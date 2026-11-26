# Trạng thái hồ sơ nộp bài

Đối chiếu file thực tế; không thay thế việc người học đọc và giải thích bài.

- [x] Part 1–6: câu trả lời, code và output chấm Part 6 PASS 12/12.
- [x] Public Render: health/readiness 200, thiếu key 401 kiểm tra độc lập; có key 200 do người học kiểm tra.
- [x] Part 7: đủ 4 mức concurrency, 3 slow rate, eval v1/v2/fixed 23/23 không regression.
- [x] Scaling: 100 user/2 phút, xác nhận 1 và 3 replica, CSV gốc.
- [x] Chaos A–E và A+B kết hợp; ảnh ít nhất 2 alert firing; trace/log khớp ID.
- [x] Script chấm/golden dataset không sửa; không có file .env đang tracked.

## File còn thiếu

- [ ] `screenshots/dashboard.png`

Dashboard Render cần chụp từ phiên đăng nhập của người học. Không dùng ảnh trang đăng nhập hoặc ảnh dựng để thay bằng chứng service Live. Có thể bổ sung `screenshots/test-authorized.png` từ ảnh Swagger 200 đã gửi trong hội thoại; `test.png` hiện là kiểm tra 401 thật.

Người học cần tự đọc lại bài, giải thích số liệu/code và nộp link repo trên LMS. Không sửa ngày commit hoặc force-push.
