# Endpoint Usage Guide

This document explains who uses each HTTP endpoint in `main.py` when running in server mode (`python main.py --server --port 8000`).

---

## Endpoint Overview

| Endpoint | Format | Primary Users | Secondary Users |
|----------|--------|---------------|-----------------|
| `/metrics` | `text/plain` (Prometheus format) | **Prometheus** (scrapes every 15s) | Developers (manual curl), Grafana (via Prometheus) |
| `/health` | `application/json` | **Kubernetes/Docker** (health probes), **Monitoring tools** | Developers (manual checks), Prometheus (health metrics) |
| `/golden-signals` | `application/json` | **Developers/Operators** (monitoring), **Dashboards** (API calls) | CI/CD pipelines, Alerting systems |

---

## 1. `/metrics` Endpoint

**Location:** `main.py:115-151`

**Format:** Prometheus text format (`text/plain`)

**Who Uses It:**

### Primary: Prometheus (Automatic Scraping)
- **Service:** Prometheus (port 9090)
- **Config:** `observability/prometheus/prometheus.yml`
- **Scrape Target:** `host.docker.internal:8000/metrics`
- **Interval:** Every 15 seconds
- **Purpose:** Collects all application metrics for storage and querying

**Example Prometheus Config:**
```yaml
scrape_configs:
  - job_name: 'taskpilot'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Secondary: Grafana (via Prometheus)
- **Service:** Grafana (port 3000)
- **Data Source:** Prometheus
- **Purpose:** Visualizes metrics from Prometheus in dashboards
- **Example Dashboard:** `observability/grafana/golden-signals-dashboard.json`

### Manual Access: Developers
```bash
# Check metrics directly
curl http://localhost:8000/metrics

# Filter specific metrics
curl http://localhost:8000/metrics | grep workflow_runs
curl http://localhost:8000/metrics | grep health_status
```

**Metrics Exposed:**
- Counters: `workflow_runs`, `workflow_success`, `llm_cost_total`, etc.
- Gauges: `health_status`, `health_check_task_store`, `health_check_guardrails`
- Histograms: `workflow_latency_ms` (with p95 as gauge)

---

## 2. `/health` Endpoint

**Location:** `main.py:153-184`

**Format:** JSON (`application/json`)

**Who Uses It:**

### Primary: Kubernetes/Docker Health Probes
- **Kubernetes:** `livenessProbe` and `readinessProbe`
- **Docker Compose:** Health checks
- **Purpose:** Determines if the service is healthy and ready to receive traffic

**Example Kubernetes Config:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Secondary: Prometheus (Health Metrics)
- The endpoint also publishes health metrics to Prometheus:
  - `health_status` (gauge): 1.0 = healthy, 0.5 = degraded, 0.0 = unhealthy
  - `health_check_task_store` (gauge): 1.0 = pass, 0.0 = fail
  - `health_check_guardrails` (gauge): 1.0 = pass, 0.0 = fail
- These metrics are scraped via `/metrics` endpoint

### Manual Access: Developers/Operators
```bash
# Check health status
curl http://localhost:8000/health | jq

# Expected response:
# {
#   "status": "healthy",
#   "checks": {
#     "task_store": {
#       "status": "pass",
#       "message": "Task store operational",
#       "details": {...}
#     },
#     "guardrails": {
#       "status": "pass",
#       "message": "Guardrails available",
#       "details": {}
#     }
#   },
#   "timestamp": 1234567890.123
# }
```

**Health Checks Performed:**
1. **Task Store:** Verifies task storage is operational
2. **Guardrails:** Verifies NeMo Guardrails is available/enabled

**Status Values:**
- `"healthy"` - All checks pass
- `"degraded"` - Some checks fail (non-critical)
- `"unhealthy"` - Critical checks fail
- `"error"` - Health check system error

---

## 3. `/golden-signals` Endpoint

**Location:** `main.py:186-220`

**Format:** JSON (`application/json`)

**Important Note:** This endpoint is a convenience API. The underlying metrics are automatically sent to Docker tools (Prometheus/Grafana), but this endpoint itself is NOT automatically scraped.

**How Golden Signals Reach Docker Tools:**

1. **Underlying Metrics** (automatically sent):
   - Raw metrics: `workflow_runs`, `workflow_success`, `workflow_latency_ms_p95`
   - `llm_cost_total`, `policy_violations_total`
   - These are exposed via `/metrics` endpoint
   - **Prometheus automatically scrapes `/metrics` every 15 seconds**
   - **All raw metrics are stored in Prometheus**

2. **Grafana Dashboard** (automatic calculation):
   - **Grafana queries Prometheus directly** (data is already there!)
   - **Calculates golden signals in real-time** from Prometheus data using PromQL
   - Example PromQL queries used by dashboard:
     - Success Rate: `(workflow_success / workflow_runs) * 100`
     - p95 Latency: `workflow_latency_ms_p95` (already exposed as gauge)
     - Cost per Task: `llm_cost_total / workflow_success`
     - Policy Violations: `(policy_violations_total / workflow_runs) * 100`
   - **No need for `/golden-signals` endpoint** - Grafana calculates from Prometheus data

3. **`/golden-signals` Endpoint** (manual/convenience):
   - Calculates signals on-demand from in-memory metrics (same calculation, different source)
   - Useful for: API calls, CI/CD pipelines, quick curl checks
   - **NOT used by Grafana** (Grafana calculates from Prometheus data instead)
   - **Redundant for Docker tools** - they already have the data in Prometheus

**Who Uses It:**

### Primary: Developers/Operators (Monitoring)
- **Purpose:** Quick overview of LLM production health metrics
- **Use Cases:**
  - Manual monitoring during development
  - CI/CD pipeline health checks
  - Alerting system integration
  - API integration (not used by Grafana)

**Example Usage:**
```bash
# Get golden signals
curl http://localhost:8000/golden-signals | jq

# Expected response:
# {
#   "success_rate": 95.5,
#   "p95_latency_ms": 1234.5,
#   "cost_per_successful_task_usd": 0.08,
#   "policy_violation_rate_percent": 0.5,
#   "user_confirmed_correctness_percent": null,
#   "status": {
#     "success_rate": "healthy",
#     "p95_latency": "healthy",
#     "cost_per_task": "healthy",
#     "policy_violations": "healthy"
#   }
# }
```

### Secondary: Dashboards/Visualization Tools
- **Grafana:** Can query this endpoint via HTTP data source
- **Custom Dashboards:** API integration for real-time monitoring
- **Alerting Systems:** Can poll this endpoint for threshold violations

**Status Indicators:**
Each signal includes a status (`healthy`, `warning`, `critical`):
- **Success Rate:** `healthy` ≥95%, `warning` ≥90%, `critical` <90%
- **p95 Latency:** `healthy` <2000ms, `warning` <5000ms, `critical` ≥5000ms
- **Cost per Task:** `healthy` <$0.10, `warning` <$0.50, `critical` ≥$0.50
- **Policy Violations:** `healthy` <1%, `warning` <2%, `critical` ≥2%

**Golden Signals Calculated:**
1. **Reliability:** Success Rate (workflow_success / workflow_runs)
2. **Performance:** p95 Latency (from histogram)
3. **Cost:** Cost per Successful Task (llm_cost_total / workflow_success)
4. **Quality:** User-Confirmed Correctness (if available)
5. **Safety:** Policy Violation Rate (policy_violations_total / workflow_runs)

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    main.py --server:8000                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐          │
│  │ /metrics │  │ /health  │  │ /golden-signals  │          │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘          │
│       │             │                  │                     │
└───────┼─────────────┼──────────────────┼─────────────────────┘
        │             │                  │
        │             │                  │
   ┌────▼─────┐  ┌───▼────┐      ┌──────▼──────┐
   │Prometheus│  │K8s/Dock│      │Developers/  │
   │(scrapes) │  │(probes)│      │Dashboards   │
   └────┬─────┘  └────────┘      └─────────────┘
        │
   ┌────▼─────┐
   │ Grafana  │
   │(queries) │
   └──────────┘
```

---

## When Are Endpoints Available?

**All endpoints are only available when running in server mode:**
```bash
python main.py --server --port 8000
```

**In script mode (`python main.py`), endpoints are NOT available** - the application runs once and exits.

---

## Testing Endpoints

### Test `/metrics`
```bash
# Check if endpoint responds
curl http://localhost:8000/metrics | head -10

# Verify Prometheus can scrape
# Go to: http://localhost:9090/targets
# Should show taskpilot as "UP"
```

### Test `/health`
```bash
# Check health status
curl http://localhost:8000/health | jq

# Check HTTP status code
curl -o /dev/null -s -w "%{http_code}\n" http://localhost:8000/health
# Expected: 200
```

### Test `/golden-signals`
```bash
# Get golden signals
curl http://localhost:8000/golden-signals | jq

# Check specific signal
curl http://localhost:8000/golden-signals | jq '.success_rate'
```

---

## Summary

| Endpoint | Primary Consumer | Access Pattern | Purpose |
|----------|------------------|----------------|---------|
| `/metrics` | **Prometheus** | Automatic scraping (15s) | Metrics collection |
| `/health` | **Kubernetes/Docker** | Health probes (5-10s) | Service health |
| `/golden-signals` | **Developers/Operators** | Manual/API calls | Production monitoring (convenience API) |

## Important Clarification: Golden Signals in Docker Tools

**Question:** Is `/golden-signals` endpoint data automatically sent to Docker tools?

**Answer:** The endpoint itself is NOT automatically scraped, BUT:

✅ **The underlying metrics ARE automatically sent:**
- Raw metrics (`workflow_runs`, `workflow_success`, etc.) are exposed via `/metrics`
- Prometheus automatically scrapes `/metrics` every 15 seconds
- Grafana queries Prometheus and calculates golden signals using PromQL

✅ **Grafana Dashboard automatically shows golden signals:**
- Dashboard queries Prometheus directly (not the `/golden-signals` endpoint)
- Uses PromQL queries like: `(workflow_success / workflow_runs) * 100`
- Updates automatically every 30 seconds (dashboard refresh interval)

❌ **`/golden-signals` endpoint is NOT used by Grafana:**
- It's a convenience API for manual checks, CI/CD, or custom integrations
- Grafana calculates signals itself from Prometheus data

**Data Flow:**
```
Application Metrics (workflow_runs, workflow_success, etc.)
  ↓
/metrics endpoint (Prometheus text format)
  ↓
Prometheus (scrapes every 15s, stores raw metrics)
  ↓
Grafana Dashboard (queries Prometheus with PromQL, calculates golden signals)
  └─ Example: (workflow_success / workflow_runs) * 100
  └─ Refreshes every 30s
```

**Key Point:** 
- ✅ **All underlying metrics are already in Prometheus** (scraped from `/metrics`)
- ✅ **Grafana calculates golden signals from Prometheus data** (using PromQL)
- ✅ **No need for `/golden-signals` endpoint** - Grafana has everything it needs

**The `/golden-signals` endpoint:**
- Calculates signals from in-memory metrics (same calculation, different source)
- Useful for: curl checks, API integrations, CI/CD pipelines
- **Redundant for Docker tools** - they already calculate from Prometheus data
- NOT used by: Prometheus, Grafana (they use `/metrics` + PromQL)

All endpoints are accessible via HTTP for manual testing, but their primary purpose is integration with observability and orchestration tools.
