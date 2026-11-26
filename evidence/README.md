# Bằng chứng kiểm thử

- `part6-full-check.txt`: script chấm nguyên gốc chạy đầy đủ trong Linux, PASS 12/12. Không sửa script chấm.
- `part4-check.txt`, `part4-monthly-budget.json`: kiểm tra auth/JWT/rate limit và ngân sách tháng Redis.
- `part5-stateless.txt`, `part5-shutdown.json`, `part5-shutdown-server.txt`: session qua 3 instance và kiểm tra signal thật.
- `eval_*.txt`, `load_*.txt`: console output của công cụ Part 7; JSON dùng để báo cáo ở `../reports/`.
- `scale_1_instances.json`, `scale_3_instances.json`: số replica thực tế trước các lượt benchmark cuối. Lượt Locust cuối dùng `--no-deps` để không bị đưa về 2 replica mặc định.
- `part7-scale-*.txt`: log Locust cuối; CSV ở thư mục production và được copy ra `../benchmark-results/` khi tạo báo cáo.
- `part7-trace-analysis.json`, `slow-trace.json`, `error-trace.json`: trace gốc và log khớp trace_id.
- `chaos-experiments.json`: cấu hình, thời gian poll, trạng thái alert thật của các thí nghiệm. Snapshot dùng UTC; báo cáo ghi ngày theo Asia/Saigon.
- `part7-alert-rule-tests.txt`: promtool test rules, exit code 0.
- `public-deployment-smoke.json`: kiểm tra độc lập public health/readiness và thiếu-key 401. Request 200 có key đã được người học kiểm tra và gửi ảnh trong hội thoại; không lưu key trong repo.

Ảnh trong `../screenshots/` được chụp từ UI thật, không dựng lại từ số liệu. Ảnh dashboard Render cần phiên đăng nhập của người học nếu chưa có file tương ứng. Các log build/pull là bằng chứng hỗ trợ, không dùng để suy ra latency/RPS. Một số file từ lượt thử ban đầu được giữ trong lịch sử; bảng báo cáo chỉ lấy các JSON/CSV và metadata được chỉ rõ.
