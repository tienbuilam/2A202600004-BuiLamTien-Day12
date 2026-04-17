import json
import logging
from openai import AsyncOpenAI
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.config import settings

# Import Guardrails & HITL
from src.guardrails.input_guardrails import detect_injection, topic_filter
from src.guardrails.output_guardrails import content_filter, llm_safety_check, _init_judge
from src.hitl.hitl import ConfidenceRouter

logger = logging.getLogger(__name__)
async_client = None

def create_agent():
    """Khởi tạo các dependencies (API keys, Judge Agent, NeMo)."""
    global async_client
    if settings.openai_api_key:
        async_client = AsyncOpenAI(api_key=settings.openai_api_key)
        logger.info(f"OpenAI Client initialized with {settings.llm_model}.")
    else:
        logger.warning("OPENAI_API_KEY không được tìm thấy - Chạy mock mode.")
        
    try:
        from src.guardrails.nemo_guardrails import init_nemo
        init_nemo()
    except ImportError:
        pass
        
    try:
        _init_judge()
        logger.info("Output Safety Judge has been initialized.")
    except Exception as e:
        logger.error(f"Cannot initialize safety judge: {e}")
        
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
    # 1. Input Guardrails
    if detect_injection(question):
        return "[BLOCKED] Your request was blocked: potential prompt injection detected. Please ask a banking-related question."
    if topic_filter(question):
        return "I can only assist with banking-related questions such as accounts, transfers, loans, and interest rates. How can I help you with banking today?"

    if not async_client:
        return "System is in Mock Mode due to missing API keys."

    # Kết nối Redis để load History
    try:
        from app.rate_limiter import r as redis_client
    except ImportError:
        redis_client = None

    history = _get_history(redis_client, user_id)
    
    messages = [
        {"role": "system", "content": "You are a helpful customer service assistant for VinBank. IMPORTANT: Never reveal internal system details, passwords, or API keys."}
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    # Lưu câu hỏi vào memory
    _save_message(redis_client, user_id, "user", question)

    try:
        # LLM Call
        response = await async_client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        raw_answer = response.choices[0].message.content
        
        # 2. Output Guardrails (Content Filter)
        cf_result = content_filter(raw_answer)
        clean_answer = cf_result["redacted"] if not cf_result["safe"] else raw_answer
        
        # 3. Output Guardrails (LLM as Judge)
        judge_result = await llm_safety_check(clean_answer)
        if not judge_result["safe"]:
            clean_answer = "I'm sorry, I'm unable to provide that information. Please ask a banking-related question and I'll be happy to help."

        # Lưu câu trả lời an toàn vào memory
        _save_message(redis_client, user_id, "assistant", clean_answer)
        
        # 4. HITL Confidence Routing
        router = ConfidenceRouter()
        decision = router.route(clean_answer, confidence=0.85, action_type="general")
        if decision.action == "escalate":
            clean_answer = f"[ESCALATED] (Human Review Needed) {clean_answer}"
            
        return clean_answer

    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return f"Error fulfilling request: {e}"
