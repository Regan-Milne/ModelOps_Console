# ModelOps Console - Startup Procedure

## Quick Start Commands

**Windows/PowerShell:**
```powershell
# 1. Start Ollama (if not running)
ollama serve

# 2. Navigate to project directory
cd C:\ComputerStuff\MLops-Projects\LLM_Dashboard

# 3. Start the stack
docker compose up --build
```

**Services will be available at:**
- Chat Interface: http://localhost:8000
- Grafana Dashboard: http://localhost:3000 (admin/admin)
- Prometheus Metrics: http://localhost:9090
- Raw Metrics: http://localhost:8000/metrics

---

## Prerequisites Checklist

### ✅ Required Software
- [ ] **Docker Desktop** - Running and accessible
- [ ] **Ollama** - Installed and running (`ollama serve`)
- [ ] **At least one model** - Downloaded (e.g., `ollama pull phi4-mini:latest`)

### ✅ Port Availability
- [ ] Port 8000 - Chat service
- [ ] Port 3000 - Grafana
- [ ] Port 9090 - Prometheus
- [ ] Port 11434 - Ollama (default)

---

## Detailed Startup Procedure

### Step 1: Verify Prerequisites

```bash
# Check Docker
docker --version
docker compose version

# Check Ollama
curl http://localhost:11434/api/tags

# Check available models
ollama list
```

### Step 2: Start Services

```bash
# Navigate to project directory
cd /path/to/LLM_Dashboard

# Start all services
docker compose up --build

# Or start in background
docker compose up --build -d
```

### Step 3: Verify Services

```bash
# Health check endpoints
curl http://localhost:8000/health
curl http://localhost:3000/api/health
curl http://localhost:9090/-/healthy
```

### Step 4: Test End-to-End

1. **Send test message:**
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello, test message"}'
   ```

2. **Verify metrics:**
   ```bash
   curl http://localhost:8000/metrics | grep chat_
   ```

3. **Check Grafana dashboards:**
   - Open http://localhost:3000
   - Login with admin/admin
   - Navigate to the "Ollama Chat Metrics" dashboard

---

## Troubleshooting Guide

### Common Issues

#### 1. Ollama Unreachable
**Symptoms:** Chat service shows "Ollama unreachable" 
**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

#### 2. No Models Available
**Symptoms:** "No models available" in dropdown
**Solution:**
```bash
# Pull a model
ollama pull phi4-mini:latest

# Verify models
ollama list
```

#### 3. Grafana Panels Show Full Dashboard
**Symptoms:** Embedded panels show entire Grafana UI instead of individual charts
**Solution:** 
- Already fixed in latest version
- URLs now include `&kiosk` parameter for proper embedding
- If still having issues, check if dashboard exists: http://localhost:3000/d/chat-metrics/ollama-chat-metrics

#### 4. Metrics Not Showing
**Symptoms:** Grafana panels are empty or show "No data"
**Solution:**
```bash
# 1. Check if chat service is generating metrics
curl http://localhost:8000/metrics | grep chat_

# 2. Test chat endpoint to generate data
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'

# 3. Verify Prometheus can scrape metrics
curl http://localhost:9090/api/v1/query?query=chat_requests_total
```

#### 5. Port Conflicts
**Symptoms:** "Port already in use" errors
**Solution:**
```bash
# Find what's using the ports
netstat -tulpn | grep :8000
netstat -tulpn | grep :3000
netstat -tulpn | grep :9090

# Stop conflicting services or change ports in docker-compose.yml
```

---

## Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chat Service  │───▶│   Prometheus    │───▶│    Grafana      │
│   (Port 8000)  │    │   (Port 9090)   │    │   (Port 3000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│     Ollama      │
│   (Port 11434)  │
└─────────────────┘
```

### Data Flow
1. **User** ➜ Chat Interface (:8000)
2. **Chat Service** ➜ Ollama (:11434)
3. **Chat Service** ➜ Prometheus metrics (:8000/metrics)
4. **Prometheus** ➜ Scrapes metrics every 15s (:9090)
5. **Grafana** ➜ Queries Prometheus (:3000)

---

## Metrics Available

### Request Metrics
- `chat_requests_total{model, status_code}` - Total chat requests
- `chat_request_latency_seconds{model}` - Request latency histogram
- `chat_tokens_total{model}` - Total tokens generated
- `chat_errors_total{model, reason}` - Error counts

### Dashboard Panels
1. **Chat Request Rate** - Rate of requests per second
2. **Response Latency** - 95th percentile response times
3. **Token Throughput** - Tokens generated per second by model
4. **Error Rate** - Percentage of failed requests

---

## Recent Fixes Applied

### Grafana Embed URL Fix (November 2025)
**Problem:** Embedded Grafana panels were showing full dashboard UI instead of individual charts
**Root Cause:** Missing `&kiosk` parameter in iframe URLs
**Solution:** Added `&kiosk` parameter to all Grafana embed URLs in `chat.html:583,590,597,604`

**Before:**
```html
src="http://localhost:3000/d-solo/chat-metrics/ollama-chat-metrics?orgId=1&panelId=1&theme=dark&from=now-5m&to=now&refresh=5s"
```

**After:**
```html
src="http://localhost:3000/d-solo/chat-metrics/ollama-chat-metrics?orgId=1&panelId=1&theme=dark&from=now-5m&to=now&refresh=5s&kiosk"
```

### Verified Working Components
- ✅ Chat service generates Prometheus metrics
- ✅ Prometheus scrapes metrics successfully  
- ✅ Grafana dashboard exists with UID `chat-metrics`
- ✅ Solo panel URLs return HTTP 200
- ✅ End-to-end metric flow working

---

## Maintenance Tasks

### Daily
- Monitor disk space (Grafana & Prometheus data)
- Check service health endpoints

### Weekly
- Review Grafana alerts (if configured)
- Check for Ollama model updates
- Backup Grafana dashboards

### Monthly
- Update Docker images
- Review and optimize Prometheus retention policies
- Check for security updates

---

## Support Commands

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f chat-service
docker compose logs -f grafana
docker compose logs -f prometheus

# Restart specific service
docker compose restart chat-service

# Rebuild and restart
docker compose up --build

# Stop all services
docker compose down

# Reset everything (removes data!)
docker compose down -v
```