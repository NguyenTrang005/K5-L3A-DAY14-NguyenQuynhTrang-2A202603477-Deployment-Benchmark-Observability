"""Production agent with shared limits, probes and JSON logging."""
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"ts": datetime.now(timezone.utc).isoformat(),
                           "lvl": record.levelname, "event": record.getMessage()}, ensure_ascii=False)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("agent")
logger.handlers = [handler]
logger.setLevel(logging.INFO)
logger.propagate = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = True
    logger.info("startup")
    yield
    # Uvicorn handles SIGTERM and drains requests before lifespan cleanup.
    app.state.ready = False
    r.close()
    logger.info("shutdown complete")

app = FastAPI(title="Production AI Agent", lifespan=lifespan)

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, pattern=r"\S")
    user_id: str | None = None

@app.middleware("http")
async def log_request(request: Request, call_next):
    started = time.monotonic()
    response = await call_next(request)
    logger.info(json.dumps({"path": request.url.path, "status": response.status_code,
                            "ms": round((time.monotonic() - started) * 1000, 2)}))
    return response

@app.exception_handler(RedisError)
async def redis_unavailable(request: Request, exc: RedisError):
    logger.warning("redis unavailable")
    return JSONResponse(status_code=503, content={"detail": "State store unavailable"})

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error("request failed")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}

@app.get("/ready")
def ready():
    ok = getattr(app.state, "ready", False) and redis_healthy()
    return JSONResponse(status_code=200 if ok else 503, content={"ready": ok})

@app.post("/ask")
def ask(body: AskRequest, key: str = Depends(verify_api_key)):
    check_rate_limit(key)
    check_budget()
    answer = llm_ask(body.question)
    # The mock has no tokenizer: these are estimates, not provider-reported usage.
    input_tokens = max(1, (len(body.question) + 3) // 4)
    output_tokens = max(1, (len(answer) + 3) // 4)
    cost = record_cost(input_tokens, output_tokens)
    return {"question": body.question, "answer": answer,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                      "cost_usd": cost, "estimated": True}}