# ModelOps Console 🚀  
**A minimal local LLM inference + telemetry stack — Ollama + FastAPI + Prometheus + Grafana in one command.**

<img width="1420" height="653" alt="ModelOps Console Dashboard" src="https://github.com/user-attachments/assets/b1a0cf59-06a4-4308-9fff-27c14caad688" />

## Why This Exists

Local LLM experimentation needs **real observability**. Most tutorials show you how to run models, but skip the crucial part: *how do you know if they're working well?*

This project solves that by giving you a **production-shaped MLOps stack** that runs entirely on your laptop. No cloud lock-in, no complex setup — just the essential monitoring infrastructure that every serious ML system needs.

**Perfect for:**
- Testing model performance before cloud deployment  
- Learning MLOps fundamentals with real tools
- Rapid prototyping of inference stacks
- Baseline performance measurement for infrastructure decisions
- Educational projects requiring realistic telemetry

---

## Table of Contents
- [Features](#features)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Metrics & Monitoring](#metrics--monitoring)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Use Cases](#use-cases)
- [Contributing](#contributing)
- [License](#license)

---

## Features

✅ **Real Model Server** - FastAPI service with proper error handling  
✅ **Production Metrics** - Prometheus histograms, counters, and gauges  
✅ **Live Dashboards** - Grafana panels updating in real-time  
✅ **Multi-Model Support** - Automatically detects your Ollama models  
✅ **Token Throughput Focus** - Primary KPI prominently displayed  
✅ **One-Command Deploy** - `docker compose up` and you're running  
✅ **CPU-Only Compatible** - No GPU required for testing  
✅ **Zero Cloud Dependencies** - Everything runs locally

<img width="1420" height="653" alt="Live Metrics Dashboard" src="https://github.com/user-attachments/assets/30611cde-aac8-4b14-ac14-415e248e362b" />

---

## Quick Start

### 1. Prerequisites
```bash
# Install Ollama
ollama serve
ollama pull phi3:mini

# Ensure Docker is running
docker --version
```

### 2. Launch the Stack
```bash
git clone https://github.com/Regan-Milne/ModelOps_Console.git
cd ModelOps_Console
docker compose up --build
```

### 3. Access Services
| Service | URL | Description |
|---------|-----|-------------|
| **Chat Interface** | http://localhost:8000 | Web UI with embedded metrics |
| **API Documentation** | http://localhost:8000/docs | FastAPI auto-docs |
| **Raw Metrics** | http://localhost:8000/metrics | Prometheus format |
| **Prometheus** | http://localhost:9090 | Time-series database |
| **Grafana** | http://localhost:3000 | Dashboards (admin/admin) |

---

## Usage

### Test the API
```bash
# Basic chat request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What can you do?"}'

# Specify a different model
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "model": "llama3:instruct"}'
```

### Available Models
<img width="581" height="584" alt="Model Selection" src="https://github.com/user-attachments/assets/2437a919-54be-4ea8-86d7-ff10c7bb9474" />

The console automatically detects models from your Ollama installation:
- `phi3:mini` (lightweight, CPU-friendly)
- `llama3:instruct` (general purpose)
- `mistral:latest` (coding tasks)
- `qwen2:7b` (multilingual)

*No models are bundled — use whatever you have installed locally.*

---

## Metrics & Monitoring

<img width="1416" height="979" alt="Grafana Metrics Dashboard" src="https://github.com/user-attachments/assets/70b4b69b-619c-41d5-8dd4-5996bb137281" />

### Core Prometheus Metrics
- `chat_requests_total` - Request counts by model and status
- `chat_request_latency_seconds` - Response time histograms  
- `chat_tokens_total` - Token generation counts
- `chat_errors_total` - Error tracking by model and reason

### Dashboard Panels (Priority Order)
1. **Token Throughput by Model** (Primary KPI)
   ```promql
   sum by(model) (rate(chat_tokens_total[10s]))
   ```

2. **Chat Request Rate**
   ```promql
   rate(chat_requests_total[10s])
   ```

3. **Response Latency (95th percentile)**
   ```promql
   histogram_quantile(0.95, sum by (le) (rate(chat_request_latency_seconds_bucket[20s])))
   ```

4. **Error Rate**
   ```promql
   (sum(rate(chat_requests_total{status_code!="200"}[5m])) / sum(rate(chat_requests_total[5m]))) * 100 OR vector(0)
   ```

---

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │───▶│  FastAPI Chat   │───▶│  Ollama Model   │
│  (Port 8000)    │    │    Service      │    │  (Port 11434)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               │ /metrics endpoint
                               ▼
                    ┌─────────────────┐
                    │   Prometheus    │
                    │  (Port 9090)    │
                    └─────────────────┘
                               │
                               │ PromQL queries
                               ▼
                    ┌─────────────────┐
                    │     Grafana     │
                    │  (Port 3000)    │
                    └─────────────────┘
```

**Data Flow:**
1. User sends chat requests to FastAPI service
2. Service calls Ollama for model inference  
3. Prometheus metrics are emitted for each request
4. Prometheus scrapes and stores time-series data
5. Grafana visualizes metrics with real-time dashboards

---

## Configuration

### Environment Variables
```bash
DEFAULT_MODEL=phi3:mini
OLLAMA_BASE_URL=http://host.docker.internal:11434
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### Change Default Model
```yaml
# docker-compose.yml
environment:
  - DEFAULT_MODEL=llama3:instruct
```

---

## Troubleshooting

### Prometheus Shows No Metrics
```bash
# Check metrics endpoint
curl http://localhost:8000/metrics | grep chat_

# Ensure metrics increment
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "test"}'
curl http://localhost:8000/metrics | grep chat_requests_total
```

### Grafana Panels Show Home Page
- Use `/d-solo/` URLs with `&kiosk` parameter
- Panel IDs: 1=Request Rate, 2=Latency, 3=Token Throughput, 4=Error Rate
- Example: `http://localhost:3000/d-solo/chat-metrics/ollama-chat-metrics?orgId=1&panelId=3&theme=dark&kiosk`

### Ollama Unreachable
```bash
# Test Ollama connection
curl http://localhost:11434/api/tags

# If this fails, start Ollama
ollama serve
```

---

## Use Cases

### 🧪 **Local Testing & Development**
Test model performance and behavior before deploying to production infrastructure.

### 📊 **Performance Baseline**
Establish baseline metrics for latency, throughput, and resource usage across different models.

### 🎓 **MLOps Education**
Learn production monitoring patterns with real tools (Prometheus, Grafana) in a safe local environment.

### 🚀 **Rapid Prototyping**
Quickly spin up a complete inference stack to validate architectural decisions.

### 🔬 **Model Comparison**
Compare performance characteristics across different LLMs with consistent metrics.

### 🏗️ **Infrastructure Planning**
Understand resource requirements and scaling patterns before cloud deployment.

---

## Contributing

We welcome contributions! Open an issue or submit a PR for:

- 🔧 New Grafana panels or dashboards
- 📈 Additional Prometheus metrics  
- 🔀 Multi-model routing capabilities
- ⚡ Performance benchmarking tools
- 🎮 GPU inference support
- 📚 Documentation improvements

---

## License

MIT License — use this freely in your own projects.