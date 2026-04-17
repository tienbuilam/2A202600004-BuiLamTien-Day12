# Deployment Information

## Public URL

<https://day12-production-deb1.up.railway.app>

## Platform

Railway

## Test Commands

### Health Check

```bash
curl /health
# Expected: {"status": "ok", "version": "1.0.0", "uptime_seconds": 12.5, "total_requests": 2}
```

### API Test (with authentication)

```bash
curl -X POST /ask \
  -H "X-API-Key: [THAY BẰNG API KEY CỦA BẠN, VD: my-secret-key-123]" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

## Environment Variables Set

- `PORT`: 8000
- `REDIS_URL`: redis://default:lerlooEZxqMKAGjnjSmEKbdYKGfSIMve@redis.railway.internal:6379
- `AGENT_API_KEY`: dev-key-change-me-in-production
- `LOG_LEVEL`: INFO

## Screenshots

- [Deployment dashboard](image/dashboard.png)
- [Service running](image/running.png)
- [Test results](image/test.png)
