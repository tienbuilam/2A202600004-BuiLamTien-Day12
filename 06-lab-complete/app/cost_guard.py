"""Redis-backed Cost Guard for token budgeting."""
from datetime import datetime
import redis
from fastapi import HTTPException
from app.config import settings

redis_url = settings.redis_url if settings.redis_url else "redis://localhost:6379/0"
try:
    r = redis.from_url(redis_url, decode_responses=True)
except Exception:
    r = None

def check_budget(user_id: str, estimated_cost: float = 0.0) -> bool:
    if not r:
        return True
        
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    try:
        current = float(r.get(key) or 0)
        if current + estimated_cost > settings.daily_budget_usd:
            raise HTTPException(
                status_code=402,
                detail="Monthly budget exceeded."
            )
        
        if estimated_cost > 0:
            r.incrbyfloat(key, estimated_cost)
            r.expire(key, 32 * 24 * 3600)  # 32 days
            
        return True
    except redis.RedisError:
        return True  # Fail open
        
def record_cost(user_id: str, cost: float):
    if not r or cost <= 0:
        return
        
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    try:
        r.incrbyfloat(key, cost)
        r.expire(key, 32 * 24 * 3600)
    except redis.RedisError:
        pass
