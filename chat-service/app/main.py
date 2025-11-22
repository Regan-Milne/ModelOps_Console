import os
import time
import logging
from typing import Optional, Dict, List

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ollama MLOps Dashboard",
    description="Chat service with Prometheus metrics for Ollama models",
    version="1.0.0"
)

# Template configuration
templates = Jinja2Templates(directory="app/templates")

# Mount static files if needed
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "phi4-mini:latest")

REQUEST_LATENCY = Histogram(
    "chat_request_latency_seconds",
    "Latency of chat endpoint",
    ["model"],
)

REQUESTS_TOTAL = Counter(
    "chat_requests_total",
    "Total chat requests",
    ["model", "status_code"],
)

TOKENS_TOTAL = Counter(
    "chat_tokens_total",
    "Total tokens in responses",
    ["model"],
)

ERRORS_TOTAL = Counter(
    "chat_errors_total",
    "Total errors talking to Ollama",
    ["model", "reason"],
)

# Session-based chat memory
class Message(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str

# In-memory session storage
sessions: Dict[str, List[Message]] = {}
MAX_MESSAGES = 20  # Keep last 20 messages per session


class ChatMetrics(BaseModel):
    tps: float
    ttft_ms: int
    process_ms: int
    generate_ms: int


class ModelOptions(BaseModel):
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    top_k: Optional[int] = 40
    num_predict: Optional[int] = 512
    repeat_penalty: Optional[float] = 1.1

class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    sessionId: Optional[str] = None
    options: Optional[ModelOptions] = None


class ChatResponse(BaseModel):
    reply: str
    model: str
    latency_sec: float
    tokens: Optional[int] = None
    metrics: Optional[ChatMetrics] = None


class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    default_model: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    ollama_reachable = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            ollama_reachable = response.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
    
    return HealthResponse(
        status="healthy" if ollama_reachable else "degraded",
        ollama_reachable=ollama_reachable,
        default_model=DEFAULT_MODEL
    )


def get_session_context(session_id: str) -> List[Message]:
    """Get conversation history for a session"""
    return sessions.get(session_id, [])

def add_to_session(session_id: str, message: Message):
    """Add message to session and maintain size limit"""
    if session_id not in sessions:
        sessions[session_id] = []
    
    sessions[session_id].append(message)
    
    # Keep only last MAX_MESSAGES
    if len(sessions[session_id]) > MAX_MESSAGES:
        sessions[session_id] = sessions[session_id][-MAX_MESSAGES:]

def build_conversation_prompt(session_id: str, current_message: str) -> str:
    """Build prompt with conversation history"""
    history = get_session_context(session_id)
    
    if not history:
        return current_message
    
    # Use only last 4 messages for context to reduce verbosity
    recent_history = history[-4:] if len(history) > 4 else history
    
    # Build simpler context-aware prompt
    prompt_parts = []
    
    for msg in recent_history:
        if msg.role == "user":
            prompt_parts.append(f"Human: {msg.content}")
        elif msg.role == "assistant":
            # Truncate long assistant responses to first 200 chars
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            prompt_parts.append(f"Assistant: {content}")
    
    prompt_parts.append(f"Human: {current_message}")
    prompt_parts.append("Assistant:")
    
    return "\n".join(prompt_parts)

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Enhanced chat endpoint with per-message metrics and session memory"""
    import json
    import uuid
    
    model = req.model or DEFAULT_MODEL
    session_id = req.sessionId or str(uuid.uuid4())
    request_start = time.perf_counter()
    first_token_at = None
    last_token_at = None
    token_count = 0
    response_content = ""
    
    # Build conversation history for chat API
    history = get_session_context(session_id)
    messages = []
    
    # Add conversation history
    for msg in history[-4:]:  # Only last 4 messages
        messages.append({
            "role": msg.role,
            "content": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        })
    
    # Add current message
    messages.append({"role": "user", "content": req.message})
    
    # Use custom options if provided, otherwise use defaults
    options = {}
    if req.options:
        options = req.options.dict()
        logger.info(f"Using custom options: {options}")
    else:
        options = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "num_predict": 512,
            "repeat_penalty": 1.1
        }
        logger.info(f"Using default options: {options}")
    
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": options
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if not response.is_success:
                    duration = time.perf_counter() - request_start
                    ERRORS_TOTAL.labels(model=model, reason=f"status_{response.status_code}").inc()
                    REQUESTS_TOTAL.labels(model=model, status_code=str(response.status_code)).inc()
                    REQUEST_LATENCY.labels(model=model).observe(duration)
                    logger.error(f"Ollama returned error {response.status_code}")
                    raise HTTPException(status_code=response.status_code, detail="Ollama error")
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            current_time = time.perf_counter()
                            
                            # Track token generation - chat API format
                            if "message" in chunk and chunk["message"] and "content" in chunk["message"]:
                                content = chunk["message"]["content"]
                                if content:
                                    if first_token_at is None:
                                        first_token_at = current_time
                                    last_token_at = current_time
                                    token_count += 1
                                    response_content += content
                            
                            # Check if done
                            if chunk.get("done", False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
                            
    except Exception as e:
        duration = time.perf_counter() - request_start
        ERRORS_TOTAL.labels(model=model, reason="connection_error").inc()
        REQUESTS_TOTAL.labels(model=model, status_code="connection_error").inc()
        REQUEST_LATENCY.labels(model=model).observe(duration)
        logger.error(f"Failed to connect to Ollama: {e}")
        raise HTTPException(status_code=503, detail=f"Ollama unreachable: {e}")

    # Calculate metrics
    total_duration = time.perf_counter() - request_start
    REQUESTS_TOTAL.labels(model=model, status_code="200").inc()
    REQUEST_LATENCY.labels(model=model).observe(total_duration)
    TOKENS_TOTAL.labels(model=model).inc(token_count)
    
    # Calculate per-message metrics
    metrics = None
    if first_token_at and last_token_at and token_count > 0:
        ttft_ms = int((first_token_at - request_start) * 1000)
        generate_ms = int((last_token_at - first_token_at) * 1000)
        process_ms = max(0, int(total_duration * 1000) - generate_ms)
        tps = token_count / (generate_ms / 1000) if generate_ms > 0 else 0
        
        metrics = ChatMetrics(
            tps=round(tps, 1),
            ttft_ms=ttft_ms,
            process_ms=process_ms,
            generate_ms=generate_ms
        )

    # Store conversation in session
    add_to_session(session_id, Message(role="user", content=req.message))
    add_to_session(session_id, Message(role="assistant", content=response_content))
    
    logger.info(f"Chat completed: model={model}, session={session_id}, tokens={token_count}, latency={total_duration:.2f}s")

    return ChatResponse(
        reply=response_content,
        model=model,
        latency_sec=total_duration,
        tokens=token_count,
        metrics=metrics
    )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """Serve the main chat interface"""
    return templates.TemplateResponse("chat.html", {"request": request})


@app.delete("/chat/session/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation history for a session"""
    if session_id in sessions:
        del sessions[session_id]
        logger.info(f"Cleared session: {session_id}")
        return {"message": f"Session {session_id} cleared"}
    return {"message": "Session not found"}

@app.get("/models")
async def get_available_models():
    """Get list of available Ollama models"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get("models", []):
                    name = model.get("name", "")
                    if name:
                        models.append({
                            "name": name,
                            "size": model.get("size", 0),
                            "modified_at": model.get("modified_at", "")
                        })
                return {"models": models}
            else:
                logger.error(f"Failed to fetch models: {response.status_code}")
                return {"models": [], "error": f"Ollama API returned {response.status_code}"}
    except Exception as e:
        logger.error(f"Failed to connect to Ollama for model list: {e}")
        return {"models": [], "error": str(e)}

@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "message": "Ollama MLOps Dashboard API",
        "endpoints": {
            "chat_ui": "GET / (Web Interface)",
            "chat": "POST /chat",
            "models": "GET /models",
            "clear_session": "DELETE /chat/session/{session_id}",
            "health": "GET /health", 
            "metrics": "GET /metrics"
        }
    }