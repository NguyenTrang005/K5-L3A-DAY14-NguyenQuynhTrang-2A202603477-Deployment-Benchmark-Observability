# Ảnh bằng chứng

Các ảnh được chụp từ trang thật bằng Chrome headless, không dựng lại UI từ số liệu:

- `running.png`: public `/health` của agent Render.
- `test.png`: Swagger public `POST /ask` thiếu key, HTTP 401. Kết quả có key 200 đã được người học gửi trong hội thoại và ghi trong DEPLOYMENT.md; có thể lưu thêm ảnh gốc thành `test-authorized.png`.
- `grafana-dashboard.png`: dashboard Grafana đang có tải; các `grafana-*.png` ghi riêng các thí nghiệm.
- `jaeger-slow-trace.png`, `jaeger-error-trace.png`: trace thật, đối chiếu ID trong `evidence/part7-trace-analysis.json`.
- `prometheus-alert-firing.png`: cùng lúc AgentHighErrorRate và AgentHighLatencyP95 firing trong lượt A+B kết hợp.

**Còn cần người học lưu `dashboard.png`** từ Render dashboard/service Live. Codex không có phiên Render đã đăng nhập; ảnh trang đăng nhập không thay thế bằng chứng triển khai. Che secrets; không chụp đoạn Curl có API key trong Swagger.
