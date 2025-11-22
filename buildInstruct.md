V1 – What we’re actually building

Assumptions for V1:

User has Ollama running on the host (localhost:11434)

User has at least one model pulled (we’ll default to phi3:mini)

User has Docker + docker-compose

We provide a tiny stack:

chat-service (FastAPI)

/chat → forwards to Ollama

/metrics → Prometheus metrics

prometheus → scrapes chat-service

grafana → visualizes the metrics

Out-of-the-box:

We default to phi3:mini (nice for CPU).

User can override the model name with an env var or per-request.

If they already have Qwen/DeepSeek/etc, they can pick those instead — dashboard still works.

Project layout

Something like:

ollama-mlops-dashboard/
  docker-compose.yml
  chat-service/
    Dockerfile
    requirements.txt
    app/
      __init__.py
      main.py
  prometheus/
    prometheus.yml

1) docker-compose.yml

This assumes Ollama is running on your host (Windows + Docker Desktop), and we use host.docker.internal to reach it from inside the container:

version: "3.9"

services:
  chat-service:
    build: ./chat-service
    container_name: chat-service
    ports:
      - "8000:8000"
    environment:
      # Host Ollama instance
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      # Default V1 model (your tiny CPU-friendly model)
      - DEFAULT_MODEL=phi3:mini
    extra_hosts:
      - "host.docker.internal:host-gateway"

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  grafana-data:

2) chat-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

3) chat-service/requirements.txt
fastapi
uvicorn[standard]
httpx
prometheus_client

4) chat-service/app/main.py

This is a simple chat endpoint plus a Prometheus /metrics endpoint.
We record basic metrics: requests, latency, token count, errors.

import os
import time

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "phi3:mini")

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


class ChatRequest(BaseModel):
    message: str
    model: str | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str
    latency_sec: float


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    model = req.model or DEFAULT_MODEL
    start = time.perf_counter()
    url = f"{OLLAMA_BASE_URL}/api/chat"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": req.message}],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json=payload)
    except Exception as e:
        duration = time.perf_counter() - start
        ERRORS_TOTAL.labels(model=model, reason="connection_error").inc()
        REQUESTS_TOTAL.labels(model=model, status_code="connection_error").inc()
        REQUEST_LATENCY.labels(model=model).observe(duration)
        raise HTTPException(status_code=503, detail=f"Ollama unreachable: {e}")

    duration = time.perf_counter() - start
    status = r.status_code
    REQUESTS_TOTAL.labels(model=model, status_code=str(status)).inc()
    REQUEST_LATENCY.labels(model=model).observe(duration)

    if not r.is_success:
        ERRORS_TOTAL.labels(model=model, reason=f"status_{status}").inc()
        raise HTTPException(status_code=status, detail=r.text)

    data = r.json()
    # Ollama chat response shape: { "message": { "role": "...", "content": "..." }, ... }
    content = (data.get("message") or {}).get("content", "")
    # Simple token estimate: whitespace split
    token_estimate = len(content.split())
    TOKENS_TOTAL.labels(model=model).inc(token_estimate)

    return ChatResponse(
        reply=content,
        model=model,
        latency_sec=duration,
    )


@app.get("/metrics")
def metrics():
    # Expose Prometheus metrics
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


How model choice works in V1:

Default model: DEFAULT_MODEL env var (set to phi3:mini in docker-compose.yml).

Per-request override:

Include "model": "qwen3:14b" in the JSON body if they want something else.

Dashboard doesn’t care which one they use; it just labels metrics by model name.

5) prometheus/prometheus.yml

Minimal config that scrapes only our chat-service:

global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "chat-service"
    static_configs:
      - targets: ["chat-service:8000"]


Prometheus will automatically scrape http://chat-service:8000/metrics.

Running V1

Once phi3:mini finishes downloading and Ollama is running:

Start Ollama (if not already running):

ollama serve


From the project root:

docker compose up --build


Test the chat API:

curl -X POST http://localhost:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"Explain what this project does in one sentence.\"}"


(On WSL/Linux, same command without the PowerShell escaping.)

Check metrics:

Open: http://localhost:8000/metrics

Bring up Prometheus & Grafana:

Prometheus: http://localhost:9090

Grafana: http://localhost:3000 (user/pass: admin / admin)

In Grafana:

Add a Prometheus data source with URL: http://prometheus:9090

Create a simple dashboard with panels like:

rate(chat_requests_total[1m])

histogram_quantile(0.9, sum(rate(chat_request_latency_seconds_bucket[5m])) by (le))

sum by (model) (rate(chat_tokens_total[5m]))

That’s a clean, simple V1:

tiny model default,

any other Ollama model optional,

and a nice metrics pipeline ready for you to build dashboards on.

If you want, next step we can design one specific Grafana dashboard layout (panel queries + titles) so you can set it up in a couple of minutes and call V1 “done.”