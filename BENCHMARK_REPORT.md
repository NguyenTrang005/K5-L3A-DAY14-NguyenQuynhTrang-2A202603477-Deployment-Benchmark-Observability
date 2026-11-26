# Benchmark & Observability Report — Day 14

**Họ tên:** Nguyễn Quỳnh Trang
**Ngày chạy:** 25–26/11/2026 (Asia/Saigon); benchmark local ngày 25, các lượt scaling/chaos cuối cùng ngày 26. Timestamp gốc nằm trong log và JSON.
**Môi trường:** Windows, Python 3.12 trong `.venv`, Docker Desktop Linux Engine 29.9.3, Docker báo 12 CPU và 16,580,878,336 byte RAM. Agent production giới hạn 0.5 CPU/256 MB mỗi container; một worker/container. Load test local và stack Docker chạy cùng máy, có hoạt động nền; số đo là minh họa trên máy này, không phải năng lực cloud hay phép đo trên phần cứng hoàn toàn cô lập.

Toàn bộ số đo lấy từ công cụ gốc của lab. Không sửa script chấm hoặc golden dataset. Agent Part 7 là bản riêng dùng mock, không load test public service Render.

## 1. SLO của agent

| SLI | SLO | Lý do |
|---|---|---|
| p95 `/ask` | ≤ 500 ms | Mục tiêu tương tác của bài, tránh chỉ nhìn trung bình |
| Error rate `/ask` | ≤ 2% | Cho phép lỗi ngẫu nhiên mock ~1%, nhưng không bỏ qua suy giảm lớn |
| Accuracy golden dataset | ≥ 80% lúc đánh giá baseline; 100% sau sửa KB, không regression | Quality gate chặn suy giảm; 23 câu chỉ đánh giá trong phạm vi dataset |

Các ngưỡng alert mẫu lỏng hơn SLO (error >5%, p95 >1 giây), có thời gian `for` để tránh spike ngắn. Không đổi alert rules cho dễ đạt.

## 2. Benchmark hiệu năng (develop)

### 2.1 Concurrency vs latency

Mỗi lượt 300 request, model nhỏ, v2 **trước sửa KB**, slow rate 0.03/error rate 0.01. Dùng `load_test.py --out`, lưu JSON ở `reports/`.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---:|---:|---:|---:|---:|---|
| 1 | 3.94 | 203.6 | 236.8 | 1714.0 | 0.33% | PASS |
| 10 | 39.87 | 195.8 | 414.6 | 1714.3 | 2.00% | PASS |
| 50 | 90.4 | 215.0 | 570.3 | 1710.9 | 1.00% | FAIL |
| 100 | 43.47 | 752.1 | 4736.8 | 5115.9 | 3.00% | FAIL |

RPS không tăng tuyến tính: từ concurrency 50 lên 100, throughput giảm và p95 tăng mạnh. Khi nhiều request đồng thời, hàng đợi và chi phí client/server/logging trên máy dùng chung có thể chi phối. Các số đo không đủ để tách riêng CPU, I/O và hoạt động nền; không kết luận đây chỉ là lỗi LLM. SLO fail được giữ nguyên thay vì chạy lại để chọn kết quả đẹp.

### 2.2 Tail latency

Mỗi lượt 300 request, concurrency 20, chỉ đổi slow rate, khởi động lại agent giữa các lượt.

| MOCK_SLOW_RATE | avg (ms) | p95 (ms) | p99 (ms) |
|---|---:|---:|---:|
| 0 | 212.7 | 445.1 | 486.8 |
| 0.03 | 232.5 | 471.8 | 1683.7 |
| 0.1 | 355.9 | 1700.5 | 1902.8 |

Với một tỷ lệ nhỏ request chậm, p99 nhạy hơn average; khi slow rate lên 10%, cả p95 cũng rơi vào nhóm chậm. Average trộn request nhanh/chậm nên có thể che trải nghiệm xấu của một nhóm người dùng. Mẫu 300 request vẫn có dao động ngẫu nhiên; không dùng 23 câu eval để kết luận về percentile latency.

## 3. Benchmark chất lượng

Chấm bằng expected keywords của dataset gốc, pass mỗi câu khi đạt ≥60% keyword. Các lượt eval giữ mock error mặc định; tool retry lỗi upstream theo cấu hình gốc.

| Chỉ số | v1 | v2 ban đầu | v2 sau sửa |
|---|---:|---:|---:|
| Accuracy | 4.35% (1/23) | 91.30% (21/23) | 100.00% (23/23) |
| Avg tokens/câu | 57.0 | 109.1 | 117.4 |
| Tổng cost USD | 0.000403 | 0.000762 | 0.000823 |
| Cost/câu đúng USD | 0.00040335 | 3.627e-05 | 3.579e-05 |
| Quality gate | FAIL | PASS | PASS |

| Câu sai ban đầu | Keyword thiếu | Sửa KB |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm tài liệu giải thích JWT có chữ ký và thời hạn, khác API key, không đồng nhất ký với mã hóa |
| scaling-03 | cpu, memory, custom metrics | Thêm tài liệu Kubernetes HPA theo CPU/memory/custom metrics, điều kiện adapter/resource requests |

Sửa cùng nội dung trong hai bản `develop/utils/mock_llm.py` và `production/utils/mock_llm.py`; không sửa câu hỏi/đáp án. Restart v2 rồi eval: 23/23, không regression so với v2 ban đầu. v2 dùng nhiều token và cost/câu hơn, nhưng cost/câu **đúng** thấp hơn v1 rất nhiều. Latency eval được lưu trong JSON nhưng không thay thế load test.

`eval_v1_regression.json` xác nhận chạy v1 với baseline v2 trả exit code 1. Workflow `.github/workflows/quality-gate.yml` chạy eval với `--min-accuracy 1.0` và baseline bản đã sửa: exit 1 làm job thất bại. Cần đặt job thành required status check trong GitHub branch protection mới thực sự chặn merge; workflow chưa được tuyên bố đã chạy trên GitHub. CI tắt fault injection cho phép kiểm tra chất lượng ổn định, không dùng kết quả CI đó thay số benchmark.

## 4. Observability stack

### 4.1 Bằng chứng

- [Grafana khi có tải trong lượt lỗi + chậm kết hợp](screenshots/grafana-dashboard.png)
- [Trace chậm](screenshots/jaeger-slow-trace.png)
- [Trace lỗi có exception](screenshots/jaeger-error-trace.png)
- [Prometheus có ít nhất hai alert firing](screenshots/prometheus-alert-firing.png)
- Raw trace và log khớp ID: `evidence/slow-trace.json`, `evidence/error-trace.json`, `evidence/part7-trace-analysis.json`.
- Unit test alert gốc bằng `promtool`: xem `evidence/part7-alert-rule-tests.txt`.

Metrics trả lời có vấn đề gì; trace chỉ rõ bước nào; JSON log có trace_id nối chi tiết sự kiện với trace. Counter dùng rate(), gauge biểu diễn in-flight, histogram cho percentile. Route dùng template thay vì URL thực, tránh cardinality bùng nổ; không thêm user_id/question vào label.

### 4.2 Thí nghiệm sự cố

Locust 30 user, 3 replica. Mỗi thí nghiệm bắt đầu bằng recreate agent và Prometheus với volume dữ liệu mới để không kế thừa trạng thái alert từ lượt trước. Thời gian tính từ lúc bắt đầu áp dụng cấu hình, bao gồm restart/discovery/scrape/evaluation; poll mỗi 5 giây, không phải độ chính xác dưới giây. Rules và thời gian `for` giữ nguyên.

Ngoài hai lượt A/B đơn biến riêng, có lượt **A+B kết hợp** (`MOCK_ERROR_RATE=0.2`, `MOCK_SLOW_RATE=0.3`) để chụp hai alert cùng firing. Thời gian A/B trong bảng lấy từ lượt riêng, ảnh hai alert cùng firing lấy từ lượt kết hợp. C, D, E cũng chạy riêng.

| Thí nghiệm | Alert quan sát | Thời gian đầu thấy firing (s) | Panel |
|---|---|---:|---|
| A: error rate 0.2 | AgentHighErrorRate | 88.69 | Error rate, status 503 |
| B: slow rate 0.3 | AgentHighLatencyP95 | 151.88 | p95/p99 latency |
| C: model lớn | LLMCostBurnRateHigh | 156.11 | Cost burn rate, LLM latency |
| D: pause 1 instance | AgentInstanceDown | 50.25 | Instances up, targets |
| E: version v1 | Không có alert firing trong cửa sổ quan sát | 65.41 giây quan sát | Version/retrieval, cần eval để phát hiện lỗi chất lượng |

Trong E, đã chạy eval trực tiếp qua Nginx của stack: accuracy **4.35%**, quality gate **FAIL**, so với baseline v2 fixed. Xem `reports/eval_production_v1.json` và log tương ứng.

Chi tiết mỗi lần poll và cấu hình thật nằm trong `evidence/chaos-experiments.json`; các ảnh `grafana-AB.png`, `grafana-C.png`, `grafana-D.png`, `grafana-E.png` bổ sung quan sát. Model large có đơn giá mock cao gấp 16.67 lần small; cost/giờ đo được không nhất thiết tăng đúng hệ số đó vì throughput, tokens và latency cũng đổi.

Pause khác stop: container pause vẫn còn DNS nhưng không trả metrics, nên `up == 0`; stop có thể làm target biến mất khỏi discovery. Lỗi timeout do Nginx tạo không nhất thiết có trong metric của agent, cần thêm metric load balancer và kiểm tra từ bên ngoài. Trong E, hạ tầng vẫn có thể xanh dù câu trả lời sai: cần eval định kỳ/shadow traffic, đánh giá mẫu bởi người dùng và giám sát retrieval/chất lượng; không dùng latency/error rate làm đại diện accuracy.

### 4.3 Debug bằng trace

Trace chậm được chọn từ tối đa 1000 trace trong cửa sổ truy vấn, có log tương ứng (không tuyên bố là trace chậm nhất mọi thời điểm):

- trace_id: `0dee95878754785d40bfc27f54226b8e`
- Tổng thời gian: **3440.310 ms**
- Span LLM `chat mock-llm-small`: **2032.886 ms**, **59.09%** tổng thời gian.

LLM là span riêng chiếm thời gian đáng kể, nhưng phần còn lại không bằng 0; có thể có scheduling/ASGI/retrieval. Không quy toàn bộ độ chậm cho LLM khi chưa phân tích khoảng thời gian còn lại.

Log JSON cùng trace_id:

```json
{
  "ts": "2026-11-26T10:01:17.114227+00:00",
  "level": "INFO",
  "service": "observable-agent",
  "instance": "7abaaae0d0dc",
  "event": "llm_call",
  "trace_id": "0dee95878754785d40bfc27f54226b8e",
  "span_id": "de8cdae182d7657f",
  "request_id": "c0ef4eaeb175",
  "model": "mock-llm-small",
  "agent_version": "v2",
  "input_tokens": 76,
  "output_tokens": 39,
  "cost_usd": 3.5e-05,
  "llm_ms": 1640.1
}
```

Trace lỗi `97656cef6db498a90722bde501cc06cc` có event exception từ mock upstream và HTTP 503, không phải lỗi xác thực.

## 5. Benchmark scaling

Locust headless **100 users, ramp-up 10/s, 120 giây mỗi lượt**, model small/v2 đã sửa KB, error 0.01/slow 0.03. Hai lượt chạy nối tiếp, xác minh số container trong `evidence/scale_1_instances.json` và `scale_3_instances.json`. Dùng `run --no-deps` để Compose không đưa agent về mặc định 2 replica. Các lượt pilot sai replica không dùng trong bảng. Bảng dùng hàng **POST /ask**, không trộn GET /health vào percentile.

| Instance | RPS /ask | p50 (ms) | p95 (ms) | p99 (ms) | Failures / requests |
|---|---:|---:|---:|---:|---:|
| 1 | 50.94 | 240 | 1700 | 2500 | 64 / 6071 |
| 3 | 58.41 | 210 | 530 | 1700 | 67 / 6983 |

Throughput 3/1 instance = **1.15 lần**, không mặc định bằng 3. Phần trăm p95 thay đổi = **-68.82%**.

Với mock async, một process đã có thể chờ nhiều LLM đồng thời; Locust còn có thời gian nghĩ 0.5–2 giây nên số user cố định giới hạn tốc độ phát request. Scale giúp chia tải/CPU nhưng không xóa latency một lần gọi LLM. Hoạt động nền và CPU quota cũng ảnh hưởng; cần quan sát LLM p95, saturation và phân bố req/s theo instance trước khi kết luận nút thắt. Error ngẫu nhiên ~1% vẫn tồn tại sau scale, không tự biến mất bằng tăng replica.

## 6. Kết luận

1. Throughput, tail latency và error rate cần đo riêng; average tốt không bảo đảm p99 tốt, tăng concurrency có thể làm hệ thống chậm hơn.
2. Eval phát hiện regression về câu trả lời dù hạ tầng xanh; cost/câu đúng giúp đánh giá lợi ích của retrieval, nhưng 23 câu keyword-based chưa chứng minh chất lượng tổng quát.
3. Metrics, traces và logs bổ sung cho nhau; alert cần kiểm thử và thời gian `for`, không chỉ một dashboard đẹp.

Nếu đưa lên production thật: thêm metric/alert ở Nginx, synthetic public health/readiness, Redis availability, queue depth, CPU/memory, chất lượng retrieval/answer, token/cost theo model, và budget có giữ chỗ. Giới hạn cardinality, đặt sampling phù hợp và không log secret/nội dung nhạy cảm.

Thí nghiệm đã hoàn nguyên version/model/fault injection và unpause instance. Xem `SUBMISSION_STATUS.md` để biết ảnh dashboard Render nào còn cần thao tác từ phiên đăng nhập của người học.
