# Part 6 — Final Project: Production-ready AI Agent

Bạn tự xây một AI agent đủ chuẩn production từ **bản khung** trong thư mục này, kết hợp mọi thứ đã học ở Part 1–5.
Code bài làm đã triển khai trong `app/`, Dockerfile và Compose. Giữ nguyên script chấm. Bằng chứng chạy được lưu ở `../evidence/`; xem `../MISSION_ANSWERS.md` để biết kết quả và giới hạn kiểm chứng.

### Chạy bài làm

Từ thư mục này, cài `pip install -r requirements.txt`, tạo `.env` từ `.env.example`, đặt một `AGENT_API_KEY` riêng. Chạy `docker compose -p k5-day14-final up -d --build` để có agent và Redis. Khi chạy Python ngoài Docker, đặt `REDIS_URL` trỏ tới Redis có thể truy cập từ máy.

`GET /health` không phụ thuộc Redis. `GET /ready` trả 503 khi Redis lỗi. `POST /ask` nhận JSON `question` và header `X-API-Key`. Thiếu/sai key trả 401, quá tốc độ trả 429, hết ngân sách trả 402; Redis không truy cập được thì các thao tác có state trả 503. Key rỗng không cấp quyền truy cập.

Rate limit dùng Lua sliding window nguyên tử trong Redis. Budget là tổng toàn dịch vụ theo ngày/tháng UTC; token/cost của mock là **ước tính**, có đánh dấu trong response. Kiểm tra ngân sách trước gọi LLM và ghi nhận sau gọi nên các request đồng thời đang xử lý có thể làm vượt ngân sách một lượng nhỏ; đây chưa phải cơ chế giữ chỗ ngân sách cứng. Compose dùng Redis AOF và named volume để giữ state qua restart.

Để chấm đủ SIGTERM, dùng Python trên Linux/Ubuntu WSL với Docker hoạt động, chạy `python check_production_ready.py`. Windows chỉ kiểm tra được một phần. Uvicorn xử lý signal và chờ request trước khi lifespan đóng Redis; Docker CMD dùng `exec` để Uvicorn làm PID 1.

Railway: đặt service root là `06-lab-complete/`. Render Blueprint: đọc `render.yaml` trong thư mục này, `rootDir` tính từ gốc repo. Cả hai đều cần Redis cloud và biến `REDIS_URL` do người triển khai cung cấp; cấu hình sẵn không có nghĩa đã deploy public.

Bài chỉ được tính hoàn thành khi script chấm báo **`PASS 12/12`**:

```bash
pip install -r requirements.txt
python check_production_ready.py
```

---

## Checklist Deliverable

- [ ] Dockerfile (multi-stage, < 500 MB)
- [ ] docker-compose.yml (agent + redis)
- [ ] .dockerignore
- [ ] Health check endpoint (`GET /health`)
- [ ] Readiness endpoint (`GET /ready`)
- [ ] API Key authentication
- [ ] Rate limiting
- [ ] Cost guard
- [ ] Config từ environment variables
- [ ] Structured logging
- [ ] Graceful shutdown
- [ ] Public URL ready (Railway / Render config)

---

## Script chấm dựa vào những tiêu chí dưới đây

Script tự khởi động agent của bạn, gọi API thật, build và chạy Docker image. Để chấm được, agent phải tuân theo các quy ước sau:

| Hạng mục | Yêu cầu |
|----------|---------|
| Điểm vào | `app/main.py` có biến `app` (FastAPI), chạy được bằng `uvicorn app.main:app --workers 2` từ thư mục này |
| `GET /health` | Luôn trả **200** khi process còn chạy, kể cả khi Redis chưa kết nối được |
| `GET /ready` | **200** khi sẵn sàng; **503** khi Redis (`REDIS_URL`) không kết nối được |
| `POST /ask` | Body JSON `{"question": "..."}` (được phép có thêm `user_id`) → **200** |
| API key | Header `X-API-Key` phải trùng biến `AGENT_API_KEY`; thiếu hoặc sai → **401** |
| Rate limit | Tối đa `RATE_LIMIT_PER_MINUTE` request / 60 giây cho mỗi API key; vượt → **429** (nên có header `Retry-After`). State lưu trong **Redis**, vẫn còn sau khi restart agent |
| Cost guard | Tổng chi phí vượt `DAILY_BUDGET_USD` (hoặc `MONTHLY_BUDGET_USD`) → **402** |
| Biến môi trường | Đọc từ env: `AGENT_API_KEY`, `REDIS_URL`, `RATE_LIMIT_PER_MINUTE`, `DAILY_BUDGET_USD` / `MONTHLY_BUDGET_USD`, `PORT`, `ENVIRONMENT`. Liệt kê đủ trong `.env.example`. Script chạy với `ENVIRONMENT=staging` |
| Log | Mỗi dòng log của app là **1 JSON object hợp lệ** (log của uvicorn không tính) |
| Graceful shutdown | Nhận SIGTERM khi đang có request → request đó vẫn trả 200, process tự thoát với exit code 0. Trong Docker, `docker stop` phải xong trong < 10 giây |
| Docker image | Multi-stage, base slim, user non-root, có `HEALTHCHECK`, < 500 MB. `CMD` lắng nghe theo biến `PORT` (mặc định 8000), uvicorn là PID 1. Container khởi động được khi **không có** Redis |
| Compose | Một service build từ `Dockerfile` + một service dùng image `redis:*`; agent có `REDIS_URL` trỏ tới service Redis và `depends_on` nó |
| `.dockerignore` | Loại trừ `.env`, `__pycache__`, `venv` |
| Deploy config | `railway.toml` (builder `DOCKERFILE`, `healthcheckPath = "/health"`) **hoặc** `render.yaml` (`type: web`, `healthCheckPath: /health`, secret dùng `generateValue` / `sync: false`) |

---

## Bản khung

```
06-lab-complete/
├── app/
│   ├── main.py           # TODO: /health, /ready, nối auth + rate limit + cost guard vào /ask, log JSON, shutdown
│   ├── config.py         # TODO: đọc cấu hình từ biến môi trường
│   ├── auth.py           # TODO: verify_api_key → 401
│   ├── rate_limiter.py   # TODO: check_rate_limit → 429 (Redis)
│   ├── cost_guard.py     # TODO: check_budget → 402, record_cost (Redis)
│   └── redis_client.py   # TODO: kết nối Redis + redis_healthy() cho /ready
├── utils/mock_llm.py     # Mock LLM — có sẵn, không cần sửa
├── Dockerfile            # TODO: viết lại thành multi-stage production
├── docker-compose.yml    # TODO: thêm redis
├── .dockerignore         # TODO
├── .env.example          # TODO: liệt kê đủ biến
├── railway.toml          # TODO (hoặc render.yaml)
├── render.yaml           # TODO (hoặc railway.toml)
├── requirements.txt      # Có sẵn
├── check_production_ready.py   # Script chấm — không sửa
└── benchmark-observability/    # Part 7 — làm sau khi xong Part 6
```

**Gợi ý thứ tự làm:** `/health` → `config.py` → log JSON → `auth.py` → `redis_client.py` + `/ready` → `rate_limiter.py` → `cost_guard.py` → graceful shutdown → `Dockerfile` + `.dockerignore` → `docker-compose.yml` → `railway.toml` / `render.yaml`. Hướng dẫn từng bước: [CODE_LAB.md — Part 6](../CODE_LAB.md#part-6-final-project-60-phút).

---

## Chạy local

```bash
pip install -r requirements.txt
cp .env.example .env

# Chạy nhanh không cần Docker (cần Redis riêng nếu muốn test rate limit thật)
AGENT_API_KEY=dev-key uvicorn app.main:app --reload

# Chạy cả agent + redis
docker compose up --build

curl http://localhost:8000/health
curl -X POST http://localhost:8000/ask \
     -H "X-API-Key: dev-key" -H "Content-Type: application/json" \
     -d '{"question": "What is deployment?"}'
```

---

## Chấm bài

```bash
python check_production_ready.py                 # chấm đầy đủ — cần Docker đang chạy
python check_production_ready.py --skip-docker   # chế độ nhanh khi đang làm (bỏ build image)
python check_production_ready.py --static-only   # chỉ đọc file, không chạy agent
python check_production_ready.py --public-url https://your-app.railway.app   # thêm kiểm tra URL đã deploy
```

- Kết quả in theo từng tiêu chí: ✅ đạt · ❌ chưa đạt · ⚠️ chưa kiểm tra được.
- **Chỉ PASS khi cả 12 tiêu chí ✅.** Mục ⚠️ (vd máy chưa bật Docker) cũng tính là chưa đạt, nên khi nộp bài phải chạy chế độ đầy đủ.
- Lần đầu chạy, script build Docker image nên mất vài phút. Bài test stateless cần Redis: script dùng `REDIS_URL` nếu có, không thì tự bật container `redis:7-alpine` tạm thời.

---

## Deploy

**Railway**

```bash
npm i -g @railway/cli
railway login
railway init
railway variables set AGENT_API_KEY=your-secret-key
railway up
railway domain        # nhận public URL
```

**Render:** push repo lên GitHub → Render Dashboard → New → Blueprint → chọn repo (Render đọc `render.yaml`) → điền secret → Deploy.

Sau khi deploy: `python check_production_ready.py --public-url <URL>` và ghi URL vào `DEPLOYMENT.md` (xem [DAY14_DELIVERY_CHECKLIST.md](../DAY14_DELIVERY_CHECKLIST.md)).

---

## Part 7 — Benchmark & Observability

Agent đã chạy được, bước tiếp theo là đo xem nó **nhanh** và **đúng** tới đâu, rồi **giám sát** khi chạy thật:

```bash
cd benchmark-observability
```

| Thư mục | Nội dung |
|---------|----------|
| `develop/` | Agent có `/metrics`, load test (p50/p95/p99, SLO), eval trên golden dataset + quality gate |
| `production/` | Docker Compose: agent x2 + Nginx + Prometheus + Grafana + Jaeger + Locust, 4 alert rules |

Hướng dẫn đầy đủ: [benchmark-observability/README.md](benchmark-observability/README.md). Nộp kèm `BENCHMARK_REPORT.md` theo [mẫu](benchmark-observability/BENCHMARK_REPORT_TEMPLATE.md).
