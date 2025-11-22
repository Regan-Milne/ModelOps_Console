# Ollama MLOps Dashboard

A simple, production-ready MLOps dashboard for monitoring Ollama chat interactions with Prometheus metrics and Grafana visualization.

## Features

- **FastAPI Chat Service**: REST API for chatting with any Ollama model
- **Prometheus Metrics**: Request latency, token counts, error rates by model
- **Grafana Dashboards**: Real-time visualization of chat metrics
- **Model Flexibility**: Works with any Ollama model (phi3:mini default)
- **Health Checks**: Container health monitoring for reliability
- **Docker Compose**: One-command deployment

## Prerequisites

1. **Ollama** running on your host machine:
   ```bash
   ollama serve
   ```

2. **At least one model** pulled (we default to `phi3:mini`):
   ```bash
   ollama pull phi3:mini
   ```

3. **Docker & Docker Compose** installed

## Quick Start

1. **Clone and start the stack**:
   ```bash
   git clone <this-repo>
   cd LLM_Dashboard
   docker compose up --build
   ```

2. **Test the chat API**:
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Explain what this project does in one sentence."}'
   ```

3. **Access the services**:
   - **Chat API**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs
   - **Metrics**: http://localhost:8000/metrics
   - **Prometheus**: http://localhost:9090
   - **Grafana**: http://localhost:3000 (admin/admin)

## Using Different Models

### Per-request model selection:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "model": "qwen3:14b"}'
```

### Change default model:
```bash
# In docker-compose.yml
environment:
  - DEFAULT_MODEL=qwen3:14b
```

## Available Models (from your setup)
- `phi3:mini` (CPU-friendly default)
- `qwen3:14b`, `qwen3:32b` 
- `mistral-small3.2:latest`
- `dolphin-mixtral:8x7b-v2.5-q3_K_S`
- And many more...

## Monitoring & Metrics

### Key Metrics Available:
- `chat_requests_total` - Total requests by model and status
- `chat_request_latency_seconds` - Request latency distribution
- `chat_tokens_total` - Token counts by model
- `chat_errors_total` - Error counts by model and reason

### Sample Grafana Queries:
```promql
# Request rate by model
rate(chat_requests_total[1m])

# 90th percentile latency
histogram_quantile(0.9, sum(rate(chat_request_latency_seconds_bucket[5m])) by (le))

# Token throughput by model
sum by (model) (rate(chat_tokens_total[5m]))

# Error rate
rate(chat_errors_total[1m]) / rate(chat_requests_total[1m])
```

## Health Checks

All services include health endpoints:
- **Chat Service**: `/health` - Checks Ollama connectivity
- **Prometheus**: `/-/healthy` 
- **Grafana**: `/api/health`

## Configuration

### Environment Variables:
```bash
# Ollama connection
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Default model
DEFAULT_MODEL=phi3:mini

# Grafana credentials (configurable)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

## Development

### Project Structure:
```
LLM_Dashboard/
├── docker-compose.yml          # Main orchestration
├── chat-service/               # FastAPI service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       └── main.py            # Main FastAPI app
├── prometheus/
│   └── prometheus.yml         # Prometheus config
└── README.md
```

### Local Development:
```bash
# Install dependencies
cd chat-service
pip install -r requirements.txt

# Run locally (ensure Ollama is running)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Troubleshooting

### Common Issues:

1. **"Ollama unreachable"**:
   - Ensure `ollama serve` is running
   - Check Ollama is on port 11434: `curl http://localhost:11434/api/tags`

2. **Model not found**:
   - Pull the model: `ollama pull phi3:mini`
   - Check available models: `ollama list`

3. **Docker connectivity**:
   - On Windows/Mac: Uses `host.docker.internal`
   - On Linux: May need `--network="host"` or change to `localhost`

4. **Slow responses**:
   - Large models (32B+) are slower on CPU
   - Consider using smaller models like `phi3:mini` for testing

### Logs:
```bash
# View all logs
docker compose logs -f

# Specific service logs
docker compose logs -f chat-service
```

## Production Considerations

- Set strong Grafana passwords via environment variables
- Configure Prometheus retention and storage
- Add authentication for production APIs
- Monitor container resource usage
- Set up log aggregation
- Configure backup for Grafana dashboards

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test with multiple Ollama models
4. Submit a pull request

## License

MIT License - feel free to use in your own projects!