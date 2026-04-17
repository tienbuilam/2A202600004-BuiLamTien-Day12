"""Redis sliding-window rate limiter."""
import time
import redis
from fastapi import HTTPException
from app.config import settings

# Initialize Redis client. If REDIS_URL is empty, will try localhost.
redis_url = settings.redis_url if settings.redis_url else "redis://localhost:6379/0"
try:
    r = redis.from_url(redis_url, decode_responses=True)
except Exception:
    r = None

def check_rate_limit(user_id: str):
    if not r:
        return  # Bypass if Redis not available for local dev
        
    now = time.time()
    key = f"rate:{user_id}"
    
    try:
        pipeline = r.pipeline()
        pipeline.zremrangebyscore(key, 0, now - 60)
        pipeline.zcard(key)
        pipeline.zadd(key, {str(now): now})
        pipeline.expire(key, 60)
        
        results = pipeline.execute()
        current_count = results[1]
        
        if current_count >= settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
                headers={"Retry-After": "60"},
            )
    except redis.RedisError:
        pass # Fail open on redis errors
