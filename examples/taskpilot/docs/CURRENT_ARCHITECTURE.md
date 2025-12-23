# Current Architecture in Use

## Overview

This document shows the **actual architecture** currently implemented and running in your system.

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TaskPilot System Architecture                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Application Layer                               │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │                                                                    │ │
│  │  ┌──────────────────────────────────────────┐                     │ │
│  │  │         main.py (Dual Mode)              │                     │ │
│  │  │                                           │                     │ │
│  │  │  Script Mode: python main.py              │                     │ │
│  │  │    - Runs workflow once                   │                     │ │
│  │  │    - Exits                                 │                     │ │
│  │  │                                           │                     │ │
│  │  │  Server Mode: python main.py --server     │                     │ │
│  │  │    - HTTP server on port 8000             │                     │ │
│  │  │    - /metrics, /health, /golden-signals   │                     │ │
│  │  │    - Workflow runs in background           │                     │ │
│  │  └──────────────────┬───────────────────────┘                     │ │
│  │                     │                                               │ │
│  │                     │ Writes/Reads                                  │ │
│  │                     │                                               │ │
│  │                     ▼                                               │ │
│  │  ┌──────────────────────────────────────────┐                     │ │
│  │  │         File-Based Storage                │                     │ │
│  │  │                                            │                     │ │
│  │  │  • metrics.json      (metrics data)       │                     │ │
│  │  │  • traces.jsonl      (trace spans)        │                     │ │
│  │  │  • decision_logs.jsonl (OPA/NeMo decisions)│                     │ │
│  │  │  • logs/taskpilot.log (JSON logs)         │                     │ │
│  │  │  • .tasks.json       (task store)         │                     │ │
│  │  └──────────────────────────────────────────┘                     │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              Observability Stack (Docker Compose)                  │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │                                                                    │ │
│  │  ┌──────────────┐                                                 │ │
│  │  │  Prometheus  │ ◄─── Scrapes ──── main.py:8000/metrics         │ │
│  │  │  Port: 9090  │                                                 │ │
│  │  │  (Metrics)   │                                                 │ │
│  │  └──────┬───────┘                                                 │ │
│  │         │                                                          │ │
│  │         ▼                                                          │ │
│  │  ┌──────────────┐                                                 │ │
│  │  │   Grafana    │ ◄─── Reads from Prometheus                      │ │
│  │  │  Port: 3000  │                                                 │ │
│  │  │ (Dashboards) │                                                 │ │
│  │  └──────────────┘                                                 │ │
│  │                                                                    │ │
│  │  ┌──────────────┐                                                 │ │
│  │  │ OpenTelemetry│ ◄─── Receives ──── main.py (OTLP gRPC)         │ │
│  │  │  Collector   │                                                 │ │
│  │  │ Ports: 4317/8│                                                 │ │
│  │  └──────┬───────┘                                                 │ │
│  │         │                                                          │ │
│  │         ▼                                                          │ │
│  │  ┌──────────────┐                                                 │ │
│  │  │    Jaeger    │ ◄─── Receives traces from OTel Collector        │ │
│  │  │  Port: 16686 │                                                 │ │
│  │  │  (Traces UI) │                                                 │ │
│  │  └──────────────┘                                                 │ │
│  │                                                                    │ │
│  │  ┌──────────────┐                                                 │ │
│  │  │  Filebeat    │ ◄─── Reads ──── logs/taskpilot.log             │ │
│  │  │  (Log Shipper)│     (mounted volume)                            │ │
│  │  └──────┬───────┘                                                 │ │
│  │         │                                                          │ │
│  │         ▼                                                          │ │
│  │  ┌──────────────┐                                                 │ │
│  │  │ Elasticsearch│ ◄─── Receives logs from Filebeat                │ │
│  │  │  Port: 9200  │                                                 │ │
│  │  │  (Log Store) │                                                 │ │
│  │  └──────┬───────┘                                                 │ │
│  │         │                                                          │ │
│  │         ▼                                                          │ │
│  │  ┌──────────────┐                                                 │ │
│  │  │    Kibana    │ ◄─── Reads from Elasticsearch                   │ │
│  │  │  Port: 5601  │                                                 │ │
│  │  │  (Logs UI)   │                                                 │ │
│  │  └──────────────┘                                                 │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Component Details

### 1. Application Components

#### `main.py` (Main Application)

**Dual-Mode Application:**

**Script Mode (Default):**
```bash
python main.py
# Runs workflow once and exits
```

**Server Mode (Production):**
```bash
python main.py --server --port 8000
# Runs HTTP server + workflow in background
```

**Features:**
- ✅ Integrated HTTP server (FastAPI)
- ✅ Metrics endpoints (`/metrics`, `/health`, `/golden-signals`)
- ✅ Workflow execution in background (server mode)
- ✅ Automatic observability (metrics, traces, logs)

**Endpoints:**
- `GET /metrics` - Prometheus metrics (text/plain)
- `GET /health` - Health checks (JSON)
- `GET /golden-signals` - Golden Signals (JSON)
- `GET /` - Service info (JSON)

**Observability Integration:**
- Metrics: Automatic collection in middleware
- Traces: Automatic span creation and OpenTelemetry export
- Logs: JSON logging to `logs/taskpilot.log`

---

### 2. Observability Stack

#### Prometheus
- **Port**: 9090
- **Purpose**: Metrics collection and storage
- **Scrapes**: `host.docker.internal:8000/metrics` (when `main.py --server` is running)
- **Interval**: 15 seconds
- **Storage**: 30-day retention
- **Config**: `observability/prometheus/prometheus.yml`

**Metrics Available:**
- Workflow metrics: `workflow_runs`, `workflow_success`, `workflow_latency_ms`
- Agent metrics: `agent_*_invocations`, `agent_*_latency_ms`, `agent_*_errors`
- **Token metrics** (automatic tracking):
  - `llm_tokens_input_total` - Total input tokens across all models
  - `llm_tokens_output_total` - Total output tokens across all models
  - `llm_tokens_total_all` - Total tokens (input + output)
  - `llm_tokens_input_{model}` - Input tokens per model (e.g., `llm_tokens_input_gpt_4o`)
  - `llm_tokens_output_{model}` - Output tokens per model
  - `llm_tokens_total_{model}` - Total tokens per model
- **Cost metrics** (automatic calculation):
  - `llm_cost_total` - Total cost in USD
  - `llm_cost_agent_{agent_name}` - Cost per agent
  - `llm_cost_model_{model}` - Cost per model
- Task metrics: `tasks_created`, `tasks_approved`, `tasks_rejected`
- Policy metrics: `policy_violations_total`, `agent_{agent_name}_policy_violations`

**Token & Cost Tracking:**
- Automatically tracked in middleware for all agent executions
- Token usage extracted from LLM responses (OpenAI-style or agent framework)
- Cost calculated using model-specific pricing (per 1K tokens)
- Supports multiple models: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-4, gpt-3.5-turbo
- Implementation: `src/core/llm_cost_tracker.py`

#### Grafana
- **Port**: 3000
- **Purpose**: Metrics visualization
- **Data Source**: Prometheus
- **Login**: admin/admin
- **Dashboards**: Custom dashboards (Golden Signals, etc.)

#### OpenTelemetry Collector
- **Ports**: 4317 (gRPC), 4318 (HTTP)
- **Purpose**: Trace collection and processing
- **Receives**: OTLP traces from `main.py`
- **Exports**: To Jaeger via OTLP HTTP

#### Jaeger
- **Port**: 16686
- **Purpose**: Trace visualization
- **Receives**: Traces from OTel Collector
- **UI**: Web-based trace viewer

#### Elasticsearch
- **Port**: 9200
- **Purpose**: Log storage and indexing
- **Receives**: Logs from Filebeat
- **Index**: `taskpilot-logs-*`

#### Kibana
- **Port**: 5601
- **Purpose**: Log visualization
- **Data Source**: Elasticsearch
- **Index Pattern**: `taskpilot-logs-*`

#### Filebeat
- **Purpose**: Log shipping
- **Reads**: `./logs/taskpilot.log` (mounted as `/var/log/taskpilot/taskpilot.log` in container)
- **Sends**: To Elasticsearch
- **Format**: JSON logs

---

## 🔄 Data Flow

### Metrics Flow

```
main.py --server:8000
  │
  │ (serves /metrics endpoint)
  │ (writes to metrics.json for persistence)
  ▼
/metrics endpoint (Prometheus format)
  │
  │ (scrapes every 15s)
  ▼
Prometheus:9090
  │
  │ (queries)
  ▼
Grafana:3000
```

### Traces Flow

```
main.py
  │
  │ (OTLP gRPC)
  ▼
OpenTelemetry Collector:4317
  │
  │ (OTLP HTTP)
  ▼
Jaeger:16686
  │
  │ (also writes to file)
  ▼
traces.jsonl
```

### Logs Flow

```
main.py
  │
  │ (writes JSON logs)
  ▼
logs/taskpilot.log
  │
  │ (reads via mounted volume)
  ▼
Filebeat
  │
  │ (ships logs)
  ▼
Elasticsearch:9200
  │
  │ (queries)
  ▼
Kibana:5601
```

---

## 🗂️ File Storage

### Local Files (Project Directory)

| File | Purpose | Format |
|------|---------|--------|
| `metrics.json` | Metrics data | JSON |
| `traces.jsonl` | Trace spans | JSONL (one per line) |
| `decision_logs.jsonl` | OPA/NeMo decisions | JSONL |
| `logs/taskpilot.log` | Application logs | JSON (one per line) |
| `.tasks.json` | Task store | JSON |

### Docker Mounted Files

All configuration files are mounted from the project's `observability/` folder:

| Path | Purpose | Used By |
|------|---------|---------|
| `./logs/` | Logs directory | Filebeat (mounted as `/var/log/taskpilot`) |
| `./observability/prometheus/prometheus.yml` | Prometheus config | Prometheus |
| `./observability/otel/collector-config.yml` | OTel config | OTel Collector |
| `./observability/filebeat/filebeat.yml` | Filebeat config | Filebeat |
| `./observability/grafana/provisioning/` | Grafana provisioning | Grafana |

---

## 🌐 Network Architecture

### Ports in Use

| Port | Service | Purpose |
|------|---------|---------|
| **8000** | main.py --server | Integrated metrics + workflows |
| **9090** | Prometheus | Metrics UI |
| **3000** | Grafana | Dashboards |
| **4317** | OTel Collector | OTLP gRPC |
| **4318** | OTel Collector | OTLP HTTP |
| **16686** | Jaeger | Trace UI |
| **9200** | Elasticsearch | Log storage API |
| **5601** | Kibana | Log UI |

### Network Connections

```
Host Machine
  │
  ├─── main.py --server:8000
  │    │
  │    ├─── /metrics ────► Prometheus:9090 (scrapes every 15s)
  │    │
  │    └─── OTLP gRPC ────► OTel Collector:4317
  │
  ├─── main.py (script mode, writes files)
  │    └─── Writes: metrics.json, traces.jsonl, logs/taskpilot.log
  │
  ├─── OTel Collector:4318 ────► Jaeger:16686 (OTLP HTTP)
  │
  └─── Filebeat ────► Elasticsearch:9200 (HTTP)
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTel Collector endpoint | `http://localhost:4317` |
| `OTEL_ENABLED` | Enable OpenTelemetry | `true` |
| `PORT` | Main server port (when --server) | `8000` |
| `OPENAI_API_KEY` | OpenAI API key | Required |

### Docker Compose Services

```yaml
services:
  prometheus:    # Metrics collection
  grafana:      # Metrics visualization
  otel-collector: # Trace collection
  jaeger:       # Trace visualization
  elasticsearch: # Log storage
  kibana:       # Log visualization
  filebeat:     # Log shipping
```

---

## 📈 Current Status

### ✅ Working

- ✅ Metrics collection (Prometheus scraping main.py --server)
- ✅ Metrics visualization (Grafana)
- ✅ Trace collection (OpenTelemetry)
- ✅ Trace visualization (Jaeger)
- ✅ Log collection (Filebeat)
- ✅ Log storage (Elasticsearch)
- ✅ Log visualization (Kibana)
- ✅ Golden Signals endpoint

### ⚠️ Limitations

- ✅ **Metrics integrated** into main app (port 8000 with --server flag)
- ⚠️ **File-based persistence** (not database)
- ⚠️ **Single instance** (no clustering)
- ⚠️ **Local development** setup (not production-ready)

---

## 🚀 How to Run

### Start Observability Stack

```bash
docker-compose -f docker-compose.observability.yml up -d
```

### Start Application

**Option 1: Server Mode (Production)**
```bash
# Single process with integrated metrics
python main.py --server --port 8000
```

**Option 2: Script Mode (Development)**
```bash
# Run workflow once (backward compatible)
python main.py

# Or use separate metrics server (optional)
python main.py --server --port 8000  # Terminal 1
python main.py            # Terminal 2
```

### Access Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **Kibana**: http://localhost:5601
- **Metrics API**: http://localhost:8000/metrics (server mode)
- **Health**: http://localhost:8000/health (server mode)
- **Golden Signals**: http://localhost:8000/golden-signals (server mode)
- **Integrated Metrics Server**: http://localhost:8000/metrics (when running with --server)

---

## 🔍 Key Characteristics

### Architecture Style
- **Microservices**: Separate metrics server
- **File-based**: Local file persistence
- **Docker Compose**: All observability tools in containers
- **Hybrid**: Application runs on host, observability in Docker

### Data Persistence
- **Metrics**: `metrics.json` (file) + Prometheus (time-series DB)
- **Traces**: `traces.jsonl` (file) + Jaeger (in-memory)
- **Logs**: `logs/taskpilot.log` (file) + Elasticsearch (search DB)
- **Decisions**: `decision_logs.jsonl` (file)
- **Tasks**: `.tasks.json` (file)

### Scalability
- **Current**: Single instance
- **Limitation**: File-based storage (not shared)
- **Production**: Would need database/object storage

---

## 📝 Summary

**Current Architecture:**
- ✅ **Application**: Python script (`main.py`) + separate metrics server
- ✅ **Observability**: Full stack (Prometheus, Grafana, Jaeger, ELK)
- ✅ **Storage**: File-based (local development)
- ✅ **Network**: Host + Docker containers
- ⚠️ **Production Gap**: Metrics server not integrated into main app

**Key Insight:**
The system uses a **hybrid architecture**:
- Application runs on host (Python)
- Observability runs in Docker
- Communication via file I/O and network (OTLP, HTTP)

**Production Ready:**
- ✅ Metrics server integrated into main app
- ✅ Dual mode: Script mode (dev) + Server mode (prod)
- ✅ Backward compatible with existing setup
- ✅ Single container deployment ready
