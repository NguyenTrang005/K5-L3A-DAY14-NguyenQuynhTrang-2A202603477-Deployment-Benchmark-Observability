# Deployment Information — Day 14

## Public URL

https://day14-agent-8reb.onrender.com

## Platform và source

- Render Web Service (Docker), agent Part 6 trong `06-lab-complete/`.
- Redis-compatible Render Key Value; agent dùng Internal URL qua `REDIS_URL`.
- Kết quả bên dưới được xác nhận từ ảnh người học gửi ngày 25/11/2026, múi giờ Việt Nam. Chưa ghi nhận lần kiểm tra độc lập từ công cụ trong đợt này.
- Railway không tạo được project vì tài khoản báo vượt giới hạn tài nguyên gói Free, nên chuyển sang Render.

## Kết quả kiểm tra public service

| Kiểm tra | Kết quả quan sát |
|---|---|
| `GET /health` | `{"status":"ok","environment":"production"}` |
| `GET /ready` | `{"ready":true}` — kiểm tra ping Redis của ứng dụng thành công |
| `POST /ask`, thiếu key | HTTP 401, `{"detail":"Invalid or missing API key"}` |
| `POST /ask`, key hợp lệ | HTTP 200, có `question`, `answer` và `usage` |

Response 200 do người học kiểm tra qua Swagger:

```json
{
  "question": "Hello",
  "answer": "Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.",
  "usage": {
    "input_tokens": 2,
    "output_tokens": 17,
    "cost_usd": 0.0000105,
    "estimated": true
  }
}
```

Đây là mock LLM: token/cost là ước tính, không phải bill của nhà cung cấp LLM.

## Tái kiểm tra bằng PowerShell

Hai endpoint public:

```powershell
$base = 'https://day14-agent-8reb.onrender.com'
Invoke-RestMethod "$base/health"
Invoke-RestMethod "$base/ready"
```

Không có key (chỉ in mã HTTP, mong đợi 401):

```powershell
$body = @{ question = 'Hello' } | ConvertTo-Json
try {
    (Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$base/ask" -ContentType 'application/json' -Body $body).StatusCode
} catch {
    if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { throw }
}
```

Có key: mở `$base/docs`, Authorize bằng key đặt trên Render và gửi body `{"question":"Hello"}`. Mong đợi Server response 200. Không chụp đoạn Curl của Swagger vì chứa header key.

Để test bằng PowerShell mà không nhập key vào lịch sử lệnh:

```powershell
$secret = Read-Host 'AGENT_API_KEY trên Render' -AsSecureString
$credential = New-Object System.Net.NetworkCredential('', $secret)
$headers = @{ 'X-API-Key' = $credential.Password }
try {
    $body = @{ question = 'Hello' } | ConvertTo-Json
    $response = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$base/ask" -Headers $headers -ContentType 'application/json' -Body $body
    $response.StatusCode
} finally {
    $headers.Clear()
    Remove-Variable secret, credential, headers -ErrorAction SilentlyContinue
}
```

Không ghi key hoặc URL Redis có credential vào repo.

## Environment variables

- `ENVIRONMENT=production`
- `AGENT_API_KEY`: đặt riêng trên Render, không lưu giá trị tại đây.
- `REDIS_URL`: Internal URL của Key Value, không lưu giá trị tại đây.
- `RATE_LIMIT_PER_MINUTE`, `DAILY_BUDGET_USD`, `MONTHLY_BUDGET_USD`: cấu hình trên Render; hướng dẫn lab lần lượt là 10, 1, 10. Chưa có ảnh xác minh các giá trị thực tế đã đặt.
- `PORT`: ứng dụng đọc từ môi trường của nền tảng; Dockerfile hỗ trợ biến này.

## Screenshots cần lưu vào repo

Ảnh đã gửi trong hội thoại chưa được xem là đã lưu vào filesystem của repo. Trước khi nộp cần bổ sung:

- [ ] `screenshots/dashboard.png`: Render dashboard/service Live, không lộ secrets.
- [ ] `screenshots/running.png`: public health/readiness hoạt động.
- [ ] `screenshots/test.png`: kết quả API 401 và 200, không lộ key (có thể ghép hai kết quả hoặc thêm ảnh riêng).

## Giới hạn và vận hành

Chưa benchmark cloud trong phần này. Gói Free có giới hạn vận hành; Key Value miễn phí không thay thế Redis có persistence bảo đảm cho ngân sách production thật. Khi quay lại sau thời gian không truy cập có thể cần chờ ứng dụng khởi động lại. Dừng/xóa tài nguyên sau khi được chấm theo quy định lab.
