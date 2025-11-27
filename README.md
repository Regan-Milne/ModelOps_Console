🚀 ModelOps Console

A lightweight, production-style MLOps observability stack for local Ollama models.

This project demonstrates how to build a real inference service, expose structured Prometheus metrics, and visualize live model performance through Grafana — all wired together with Docker Compose.

It’s deliberately simple, transparent, and easy to extend, making it ideal for:

developers learning MLOps fundamentals

teams who want observability around local LLM experiments

founders prototyping model evaluation workflows

engineers exploring inference telemetry or model routing

📊 What This Project Shows (in Plain English)

This repo is not “just a dashboard.”
It’s a minimal, but real, MLOps pipeline:

1. A model server that actually produces metrics

FastAPI wraps a local Ollama model and logs:

request counts

latency histograms

token throughput

error rates

model names / statuses

2. Prometheus scrapes & stores the metrics

You get real, queryable time-series data.

3. Grafana visualizes everything in real-time

Dashboards show the health + behavior of your model:

token throughput by model (prioritized as primary KPI)

request rate

response latency (95th percentile)

error rate

4. Everything runs locally with one command

No GPU required.
No cloud.
Just Docker + Ollama.

This repo is intentionally small, auditable, and production-shaped.

🎥 Live Demo (GIF)

(Insert your new GIF here once you upload it:)

![demo](docs/demo.gif)


Nothing explains an MLOps system better than seeing the metrics react in real time.

🧱 Architecture Overview

Here’s the blueprint:

 ┌──────────────────────┐       ┌──────────────────┐        ┌──────────────────────┐
 │    Client / UI       │──────▶│  FastAPI Chat     │──────▶│   Ollama Model        │
 │  (ModelOps Console)  │       │  Service          │        │   (local inference)   │
 └──────────────────────┘       └──────────────────┘        └──────────────────────┘
            │                                 │
            │ emits /metrics                  │ generates tokens
            ▼                                 ▼
 ┌──────────────────────┐       ┌──────────────────────────────┐
 │     Prometheus       │◀──────│  chat-service /metrics        │
 │  (scraping engine)   │       └──────────────────────────────┘
 └──────────────────────┘
            │
            ▼
 ┌──────────────────────┐
 │       Grafana        │
 │ (dashboards + alerts)│
 └──────────────────────┘


This is the same architecture used in production ML systems — just scaled down for local experimentation.

⚡ Quick Start
1. Start Ollama
ollama serve
ollama pull phi3:mini

2. Run the entire stack
docker compose up --build

3. Explore the services
Service	URL
Chat API (FastAPI)	http://localhost:8000

API Docs	http://localhost:8000/docs

Metrics Endpoint	http://localhost:8000/metrics

Prometheus	http://localhost:9090

Grafana	http://localhost:3000
 (admin/admin)
🧪 Try a Chat Request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What can you do?"}'


Or choose a different model:

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hello", "model": "qwen3:14b"}'

📈 Metrics Tracked
Core Prometheus metrics:

chat_requests_total

chat_request_latency_seconds_bucket

chat_tokens_total

chat_errors_total

Grafana dashboard panels (in order):
# Token Throughput by Model (primary KPI)
sum by(model) (rate(chat_tokens_total[10s]))

# Chat Request Rate
rate(chat_requests_total[10s])

# Response Latency (95th percentile)
histogram_quantile(0.95, sum by (le) (rate(chat_request_latency_seconds_bucket[20s])))

# Error Rate
(
  sum(rate(chat_requests_total{status_code!="200"}[5m]))
/
  sum(rate(chat_requests_total[5m]))
) * 100
OR
vector(0)


This mirrors real-world ML observability: rate, latency, throughput, and errors.

🛠 Configuration

Environment Variables:

DEFAULT_MODEL=phi3:mini
OLLAMA_BASE_URL=http://host.docker.internal:11434
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin


To change the default model:

environment:
  - DEFAULT_MODEL=qwen3:14b

🏗 Project Structure
ModelOps_Console/
├── docker-compose.yml
├── STARTUP_PROCEDURE.md         # Complete setup and troubleshooting guide
├── PROJECT_LOG.md              # Development history and technical notes
├── chat-service/
│   ├── app/
│   │   ├── main.py             # FastAPI service with metrics
│   │   └── templates/
│   │       └── chat.html       # Web UI with embedded Grafana panels
│   ├── Dockerfile
│   └── requirements.txt
├── prometheus/
│   └── prometheus.yml
└── grafana/
    └── dashboard.json           # Pre-configured Ollama metrics dashboard

🐛 Troubleshooting
Prometheus shows no metrics

Check http://localhost:8000/metrics

Ensure chat_requests_total increments when sending messages

Verify Prometheus prometheus.yml has the correct target

Grafana panel blank or showing the home page

Use /d-solo/ embed URLs with &kiosk parameter for individual panels

Ensure panelId= matches dashboard.json (1=Chat Rate, 2=Latency, 3=Tokens, 4=Errors)

Example working URL: http://localhost:3000/d-solo/chat-metrics/ollama-chat-metrics?orgId=1&panelId=3&theme=dark&from=now-5m&to=now&refresh=5s&kiosk

Ollama not reachable
curl http://localhost:11434/api/tags


If this fails → Ollama isn’t running.

🧭 Why This Project Exists

Many MLOps tutorials focus on:

fancy models

cloud deployments

abstract concepts

But modern ML systems live or die by observability.

This project teaches the essentials:

how to serve a model

how to instrument it

how to expose metrics

how to scrape metrics

how to visualize performance

how to debug latency + throughput

It’s a small but realistic example of production-style ML telemetry that works on any laptop.

🙌 Contributing

Feel free to open issues or PRs:

new panels

additional metrics

multi-model routing

benchmarking scripts

GPU inference support

📄 License

MIT License — use it freely.