import json
import logging
import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.config import settings

# Import mock_llm directly
from utils.mock_llm import ask

logger = logging.getLogger(__name__)

def create_agent():
    logger.info("Initializing Agent with Mock LLM.")
    return "stateless_agent", "no_runner"

def _get_history(r, user_id: str) -> list:
    if not r: return []
    try:
        raw_msgs = r.lrange(f"history:{user_id}", 0, -1)
        return [json.loads(m) for m in raw_msgs]
    except Exception:
        return []

def _save_message(r, user_id: str, role: str, content: str):
    if not r: return
    try:
        payload = json.dumps({"role": role, "content": content})
        r.rpush(f"history:{user_id}", payload)
        r.expire(f"history:{user_id}", 3600)  # 1 hour 
    except Exception:
        pass

async def ask_agent(user_id: str, question: str):
    try:
        from app.rate_limiter import r as redis_client
    except ImportError:
        redis_client = None

    history = _get_history(redis_client, user_id)
    
    # Save user question to memory
    _save_message(redis_client, user_id, "user", question)

    try:
        # Call mock LLM
        answer = await asyncio.to_thread(ask, question)

        # Save assistant answer to memory
        _save_message(redis_client, user_id, "assistant", answer)
        
        return answer

    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error fulfilling request: {e}"
