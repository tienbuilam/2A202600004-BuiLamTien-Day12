# Deployment Information

## Public URL
[VUI LÒNG ĐIỀN URL PUBLIC CỦA BẠN VÀO ĐÂY, VD: https://my-agent.up.railway.app]

## Platform
Railway

## Test Commands

### Health Check
```bash
curl [THAY BẰNG URL PUBLIC CỦA BẠN]/health
# Expected: {"status": "ok", "version": "1.0.0", "uptime_seconds": 12.5, "total_requests": 2}
```

### API Test (with authentication)
```bash
curl -X POST [THAY BẰNG URL PUBLIC CỦA BẠN]/ask \
  -H "X-API-Key: [THAY BẰNG API KEY CỦA BẠN, VD: my-secret-key-123]" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

## Environment Variables Set
- `PORT`: 8000 (Railway thường cấu hình tự động nếu để trống)
- `REDIS_URL`: [Thêm thông tin nếu chạy bằng add-on Redis]
- `AGENT_API_KEY`: [API Key bạn tự đặt trên dashboard Railway]
- `LOG_LEVEL`: INFO

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
