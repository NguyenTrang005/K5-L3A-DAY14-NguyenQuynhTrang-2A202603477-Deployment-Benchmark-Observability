"""Shared UTC day/month accounting. In-flight calls may overshoot budget."""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

def budget_keys():
    now = datetime.now(timezone.utc)
    return (f"agent:cost:day:{now:%Y-%m-%d}", f"agent:cost:month:{now:%Y-%m}")

def check_budget() -> None:
    day, month = r.mget(budget_keys())
    if float(day or 0) >= settings.daily_budget_usd or float(month or 0) >= settings.monthly_budget_usd:
        raise HTTPException(status_code=402, detail="Budget exhausted")

def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000
    day, month = budget_keys()
    with r.pipeline(transaction=True) as p:
        p.incrbyfloat(day, cost)
        p.expire(day, 2 * 86400)
        p.incrbyfloat(month, cost)
        p.expire(month, 62 * 86400)
        p.execute()
    return cost