# Delivery Checklist — Day 12 Lab Submission

> **Student Name:** Bùi Lâm Tiến
> **Student ID:** 2A202600004
> **Date:** 17/04/2026

---

## Submission Requirements

Submit a **GitHub repository** containing:

### 1. Mission Answers (40 points)

Create a file `MISSION_ANSWERS.md` with your answers to all exercises:

```markdown
# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. **API key hardcode trong code:** Gây rủi ro bảo mật nghiêm trọng.
2. **Không có config management:** Các thông số cố định như DEBUG, MAX_TOKENS được hardcode trong code.
3. **Print thay vì proper logging:** Dùng lệnh print và để lộ cả secret (key) ra console.
4. **Không có health check endpoint:** Orchestrator không thể theo dõi liveness/readiness của ứng dụng.
5. **Port cố định & Debug Mode:** Ràng buộc localhost, port cứng 8000 và bật reload trong cấu hình `uvicorn.run()` không tối ưu cho production.

### Exercise 1.3: Comparison table
| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config  | Hardcode cứng trong code | Dùng Environment variables | Tăng cường bảo mật và giúp linh hoạt tuỳ biến cho từng môi trường (Dev/Staging/Prod). |
| Health check | Không tồn tại | Có endpoint `/health` & `/ready` | Giúp Load balancer và Container platform biết lúc nào nên chuyển traffic hoặc restart app. |
| Logging | `print()` thường | JSON structured logging | Dễ cấu trúc, parser log dễ xử lí khi lưu trữ tập trung. |
| Shutdown | Crash / Đột ngột | Graceful Shutdown | Xử lý trọn vẹn request đang dang dở, tránh mất database state hoặc đứt session của client. |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image: `python:3.11`
2. Working directory: `/app`
3. Tại sao COPY requirements.txt trước? Nhằm tối ưu hóa Layer Caching của Docker. Lớp cài đặt dependencies thường tốn thời gian, bằng cách copy requirements trước, nếu source code thay đổi mà packages không đổi thì quá trình build sẽ không cần thực hiện lại việc `pip install`.
4. CMD vs ENTRYPOINT: `CMD` cung cấp default options của image (dễ dàng thay thế qua lệnh truyền lúc `docker run`). `ENTRYPOINT` quy định process luôn chạy.  

### Exercise 2.3: Image size comparison
- Develop: 1.66 GB (Dùng python image mặc định full công cụ)
- Production: 236 MB (Dùng multi-stage build và python-slim)
- Difference: ~86% dung lượng giảm

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: https://my-agent.up.railway.app
- Screenshot: [Screenshot url from dashboard]

## Part 4: API Security

### Exercise 4.1-4.3: Test results
```bash
# Không truyền API Key -> Lỗi 401
$ curl http://localhost:8000/ask -X POST -H "Content-Type: application/json" -d '{"question": "Hello"}'
{"detail":"Invalid or missing API key. Include header: X-API-Key: <key>"}

# Truyền đúng API Key -> 200 OK
$ curl http://localhost:8000/ask -X POST -H "X-API-Key: dev-key-change-me" -H "Content-Type: application/json" -d '{"question": "Hello"}'
{
  "question": "Hello",
  "answer": "I can only assist with banking-related questions such as accounts, transfers, loans, and interest rates. How can I help you with banking today?",
  "model": "gpt-4o-mini",
  "timestamp": "2026-04-17T16:45:00+00:00"
}

# Vượt quá Rate Limit (quá 20 req/phút) -> Lỗi 429
$ for i in {1..25}; do curl http://localhost:8000/ask -X POST -H "X-API-Key: dev-key-change-me" -H "Content-Type: application/json" -d '{"question": "Hello"}'; done
{"detail":"Rate limit exceeded: 20 req/min"}
```

### Exercise 4.4: Cost guard implementation

Triển khai Redis để track cost theo từng user và từng tháng.

- Sử dụng key trên Redis theo format `budget:{user_id}:{YYYY-MM}`.
- Mỗi khi có request, sẽ tính toán cost dự đoán. Sau đó get biến current_cost hiện tại, nếu `current_cost + estimated_cost > LIMIT (5$)` thì block request và trả về lỗi vượt budget.
- Nếu nằm trong mức an toàn, dùng `r.incrbyfloat` để cộng dồn cost và set expiration (ví dụ 32 ngày) để tự động xoá dữ liệu sang tháng mới mà không bị leak memory của Redis.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

- **Exercise 5.1 (Health Checks):** Đã phân chia `/health` (Liveness) để check process đang chạy và `/ready` (Readiness) để check các dependencies bên thứ 3 (Ping Redis / Database connections) xem instance đó đã đủ khoẻ để server load balancer chuyển traffic vào chưa rớt.
- **Exercise 5.2 (Graceful Shutdown):** Tích hợp bắt tín hiệu `SIGTERM` trong logic. Khi nhận tín hiệu, ứng dụng sẽ ngừng nhận request mới từ Load Balancer, chờ xử lý nốt các process đang dang dở, đóng database sạch sẽ và exit một cách toàn vẹn.
- **Exercise 5.3 & 5.5 (Stateless Design):** Đã xoá bỏ dictionary local server memory lưu trữ state conversation để tránh trường hợp scaling nhiều replicas gây lệch dữ liệu theo từng instances. State được lưu trên Redis (`r.lrange(f"history:{user_id}", 0, -1)`) giúp mọi instance đều có cái nhìn duy nhất về lịch sử chat của user.

### Test Results

```bash
# Exercise 5.1: Health validation
$ curl http://localhost:8000/health
{"status":"ok","version":"1.0.0","uptime_seconds":12.5,"total_requests":2}

# Exercise 5.1: Ready (with Redis connection alive)
$ curl http://localhost:8000/ready
{"ready":true}
```

---

### 2. Full Source Code - Lab 06 Complete (60 points)

Your final production-ready agent with all files:

```
your-repo/
├── app/
│   ├── main.py              # Main application
│   ├── config.py            # Configuration
│   ├── auth.py              # Authentication
│   ├── rate_limiter.py      # Rate limiting
│   └── cost_guard.py        # Cost protection
├── utils/
│   └── mock_llm.py          # Mock LLM (provided)
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full stack
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
├── .dockerignore            # Docker ignore
├── railway.toml             # Railway config (or render.yaml)
└── README.md                # Setup instructions
```

**Requirements:**

- All code runs without errors
- Multi-stage Dockerfile (image < 500 MB)
- API key authentication
- Rate limiting (10 req/min)
- Cost guard ($10/month)
- Health + readiness checks
- Graceful shutdown
- Stateless design (Redis)
- No hardcoded secrets

---

### 3. Service Domain Link

Create a file `DEPLOYMENT.md` with your deployed service information:

```markdown
# Deployment Information

## Public URL
https://your-agent.railway.app

## Platform
Railway / Render / Cloud Run

## Test Commands

### Health Check
```bash
curl https://your-agent.railway.app/health
# Expected: {"status": "ok"}
```

### API Test (with authentication)

```bash
curl -X POST https://your-agent.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
```

## Environment Variables Set

- PORT
- REDIS_URL
- AGENT_API_KEY
- LOG_LEVEL

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)

```

##  Pre-Submission Checklist

- [ ] Repository is public (or instructor has access)
- [ ] `MISSION_ANSWERS.md` completed with all exercises
- [ ] `DEPLOYMENT.md` has working public URL
- [ ] All source code in `app/` directory
- [ ] `README.md` has clear setup instructions
- [ ] No `.env` file committed (only `.env.example`)
- [ ] No hardcoded secrets in code
- [ ] Public URL is accessible and working
- [ ] Screenshots included in `screenshots/` folder
- [ ] Repository has clear commit history

---

##  Self-Test

Before submitting, verify your deployment:

```bash
# 1. Health check
curl https://your-app.railway.app/health

# 2. Authentication required
curl https://your-app.railway.app/ask
# Should return 401

# 3. With API key works
curl -H "X-API-Key: YOUR_KEY" https://your-app.railway.app/ask \
  -X POST -d '{"user_id":"test","question":"Hello"}'
# Should return 200

# 4. Rate limiting
for i in {1..15}; do 
  curl -H "X-API-Key: YOUR_KEY" https://your-app.railway.app/ask \
    -X POST -d '{"user_id":"test","question":"test"}'; 
done
# Should eventually return 429
```

---

## Submission

**Submit your GitHub repository URL:**

```
https://github.com/your-username/day12-agent-deployment
```

**Deadline:** 17/4/2026

---

## Quick Tips

1. Test your public URL from a different device
2. Make sure repository is public or instructor has access
3. Include screenshots of working deployment
4. Write clear commit messages
5. Test all commands in DEPLOYMENT.md work
6. No secrets in code or commit history

---

## Need Help?

- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review [CODE_LAB.md](CODE_LAB.md)
- Ask in office hours
- Post in discussion forum

---

**Good luck!**
