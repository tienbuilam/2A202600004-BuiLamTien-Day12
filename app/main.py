"""Production AI Agent."""
import os
import time
import signal
import logging
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget, record_cost
from app.agent import create_agent, ask_agent

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0

# Agent instances
_agent = None
_runner = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready, _agent, _runner
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "environment": settings.environment,
    }))
    
    _agent, _runner = create_agent()
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))
    yield
    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception as e:
        _error_count += 1
        raise

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="user1", description="Identifier for rate limit and cost")

class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    timestamp: str

@app.get("/")
def root():
    return {"app": settings.app_name, "version": settings.app_version, "environment": settings.environment}

@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    check_rate_limit(body.user_id)
    
    input_tokens = len(body.question.split()) * 2
    cost_input = (input_tokens / 1000) * 0.00015
    check_budget(body.user_id, cost_input)

    logger.info(json.dumps({
        "event": "agent_call",
        "q_len": len(body.question),
        "user_id": body.user_id,
    }))

    answer = await ask_agent(body.user_id, body.question)

    output_tokens = len(answer.split()) * 2
    cost_output = (output_tokens / 1000) * 0.0006
    record_cost(body.user_id, cost_output)

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
    }

@app.get("/ready")
def ready():
    from app.rate_limiter import r
    if not _is_ready:
        raise HTTPException(503, "Not ready - agent initialization incomplete")
    if r:
        try:
            r.ping()
        except Exception:
            raise HTTPException(503, "Not ready - Redis disconnected")
            
    return {"ready": True}

def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)

if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
