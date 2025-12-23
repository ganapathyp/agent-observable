# Docker Setup Guide

## Quick Start

### Prerequisites (macOS)

**⚠️ IMPORTANT:** Docker Desktop on macOS requires explicit file sharing configuration.

1. **Open Docker Desktop** → Settings (gear icon) → Resources → File Sharing
2. **Add the project directory**: `/Users/ganapathypichumani/dev/code/maia v2/demo_agentframework/taskpilot`
   - Or add parent: `/Users/ganapathypichumani/dev/code/maia v2/demo_agentframework`
3. **Click "Apply & Restart"**
4. **Wait for Docker to restart** before proceeding

### One-Command Setup

```bash
# Start all observability services
docker-compose -f docker-compose.observability.yml up -d

# Or use convenience script
./scripts/observability/start-observability.sh
```

**If you see mount errors**, Docker Desktop file sharing is not configured. See Prerequisites above.

**Services Started:**
- Prometheus (port 9090) - Metrics collection
- Grafana (port 3000) - Metrics visualization
- OpenTelemetry Collector (port 4317) - Trace collection
- Jaeger (port 16686) - Trace visualization
- Elasticsearch (port 9200) - Log storage
- Kibana (port 5601) - Log visualization
- Filebeat - Log shipping

### Access Services

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **Kibana**: http://localhost:5601
- **Elasticsearch**: http://localhost:9200

### Start Application

```bash
# Start integrated server (production mode)
python main.py --server --port 8000

# Or run workflow (script mode)
python main.py
```

**Note:** Metrics, traces, and logs are automatically collected. No additional setup needed.

---

## Configuration Files

### Prometheus

**File:** `observability/prometheus/prometheus.yml`

```yaml
scrape_configs:
  - job_name: 'taskpilot'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

**Scrapes from:** `http://host.docker.internal:8000/metrics` (when `main.py --server` is running)

### Grafana

**Dashboards:** `observability/grafana/golden-signals-dashboard.json`

**Import:** Grafana → Dashboards → Import → Upload JSON

**Data Source:** Auto-configured Prometheus at `http://prometheus:9090`

### OpenTelemetry Collector

**File:** `observability/otel/collector-config.yml`

**Receives:** OTLP gRPC on port 4317
**Exports to:** Jaeger on port 16686

### Filebeat

**File:** `observability/filebeat/filebeat.yml`

**Monitors:** `/var/log/taskpilot/*.log` (mounted volume)
**Sends to:** Elasticsearch on port 9200

---

## Volume Mounts

**Docker Compose mounts from project's `observability/` folder:**
- Prometheus config: `./observability/prometheus/prometheus.yml`
- Grafana provisioning: `./observability/grafana/provisioning/`
- OpenTelemetry config: `./observability/otel/collector-config.yml`
- Filebeat config: `./observability/filebeat/filebeat.yml`
- Logs directory: `./logs/` (mounted to `/var/log/taskpilot` in container)

**All configs are in the project repository** - no external directory setup needed!

---

## Verification

### Check Services

```bash
docker ps | grep taskpilot
```

**Should show:**
- taskpilot-prometheus
- taskpilot-grafana
- taskpilot-otel-collector
- taskpilot-jaeger
- taskpilot-elasticsearch
- taskpilot-kibana
- taskpilot-filebeat

### Check Health

```bash
# Prometheus
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health

# Jaeger
curl http://localhost:16686

# Elasticsearch
curl http://localhost:9200
```

---

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker logs taskpilot-prometheus
docker logs taskpilot-grafana

# Restart services
docker-compose -f docker-compose.observability.yml restart
```

### Prometheus Can't Scrape

**Check target status:**
- http://localhost:9090/targets
- Should show `taskpilot` as "UP"

**If DOWN:**
- Verify `main.py --server` is running
- Check port 8000 is accessible
- Verify `host.docker.internal` resolves

### No Data in Grafana

1. Wait 15 seconds (Prometheus scrape interval)
2. Verify metrics endpoint: `curl http://localhost:8000/metrics`
3. Check Prometheus has data: Query `workflow_runs` in Prometheus UI

---

*For detailed setup, see [PRODUCTION_LIKE_LOCAL_SETUP.md](PRODUCTION_LIKE_LOCAL_SETUP.md)*
