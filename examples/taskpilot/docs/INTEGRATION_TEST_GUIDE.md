# Integration Test Guide

**Last Updated:** 2024-12-22

**Status:** ✅ All steps verified and tested (package installation, config loading, server startup verified)

> **Note:** This document is maintained as the authoritative reference for integration testing. All steps are verified and kept up-to-date with the current implementation.

**Python Command:** All commands use `python3` (not `python`). 

**⚠️ CRITICAL - Virtual Environment:**

**You MUST activate the virtual environment before running ANY Python commands:**
```bash
source .venv/bin/activate
```

**Common Error:** If you see `ModuleNotFoundError: No module named 'taskpilot'`, it means:
- ❌ You forgot to activate the venv
- ✅ Solution: Run `source .venv/bin/activate` first

**Installation:**
```bash
make install
# Or manually: pip install -e .
```

If `python3` is not available, create an alias or use the full path to your Python interpreter.

This guide provides step-by-step instructions for manually testing the complete TaskPilot integration, including all observability features.

---

## Quick Start (TL;DR)

**Before testing, ensure:**
1. ✅ Virtual environment is set up and activated
2. ✅ Package is installed: `python3 -c "import taskpilot"`
3. ✅ `.env` file exists with `OPENAI_API_KEY`
4. ✅ Docker services are running

**Quick setup:**
```bash
cd /Users/ganapathypichumani/dev/code/maia\ v2/demo_agentframework/taskpilot

# ⚠️ ALWAYS activate venv first!
source .venv/bin/activate

# Verify package is available
python3 -c "import taskpilot" || { 
    echo "❌ Package not installed or venv not activated"
    echo "   Run: source .venv/bin/activate && make install"
    exit 1
}
```

---

## Standard Ports (Fixed)

| Port | Service | Purpose |
|------|---------|---------|
| **8000** | Application Server | HTTP endpoints (metrics, health, golden-signals) |
| **9090** | Prometheus | Metrics collection and querying |
| **3000** | Grafana | Metrics visualization and dashboards |
| **16686** | Jaeger | Trace visualization |
| **5601** | Kibana | Log visualization (includes decision logs) |
| **4317** | OpenTelemetry Collector | OTLP gRPC endpoint |

---

## Prerequisites

### 1. Environment Setup

```bash
cd /Users/ganapathypichumani/dev/code/maia\ v2/demo_agentframework/taskpilot

# Step 1.1: Install dependencies (creates venv if needed and installs package)
# Option A: Use Makefile (recommended - handles all cases)
make install

# Option B: Manual setup (if Makefile doesn't work)
# Check if venv exists and package is already installed
if [ -d ".venv" ] && python3 -c "import taskpilot" 2>/dev/null; then
    echo "✅ Virtual environment and package already installed"
else
    echo "Setting up environment..."
    
    # Create venv if needed
    if [ ! -d ".venv" ]; then
        if command -v uv &> /dev/null; then
            echo "Using uv to create venv..."
            uv venv .venv
        else
            echo "Creating virtual environment..."
            python3 -m venv .venv
        fi
    fi
    
    source .venv/bin/activate
    
    # Install dependencies
    if [ -f ".venv/bin/pip" ]; then
        .venv/bin/pip install -r requirements.txt
        .venv/bin/pip install -e .
    elif [ -f ".venv/bin/python3" ]; then
        # Install pip if missing
        if ! .venv/bin/python3 -m pip --version &>/dev/null; then
            echo "Installing pip..."
            .venv/bin/python3 -m ensurepip --upgrade
        fi
        .venv/bin/python3 -m pip install -r requirements.txt
        .venv/bin/python3 -m pip install -e .
    elif command -v uv &> /dev/null; then
        uv pip install -r requirements.txt
        uv pip install -e .
    else
        echo "❌ Cannot install. Please install pip or uv."
        exit 1
    fi
fi

# Step 1.2: Activate virtual environment
source .venv/bin/activate
echo "✅ Virtual environment activated"

# Step 1.3: Verify package is installed
python3 -c "import taskpilot; print('✅ TaskPilot package installed')" || {
    echo "❌ TaskPilot package not installed."
    echo "   If using uv venv, run: uv pip install -e ."
    echo "   If using standard venv, run: .venv/bin/python3 -m pip install -e ."
    exit 1
}

# Step 1.4: Ensure .env file exists with API key
if [ ! -f .env ]; then
    echo "OPENAI_API_KEY=your-api-key-here" > .env
    echo "⚠️  Edit .env and add your actual API key"
    exit 1
fi

# Step 1.5: Verify API key is set
grep -q "OPENAI_API_KEY" .env && echo "✅ API key found" || echo "❌ API key missing"
```

### 2. Configure Docker Desktop File Sharing (macOS)

**⚠️ CRITICAL for macOS users:**

Docker Desktop on macOS requires explicit file sharing. Before starting services:

1. **Open Docker Desktop** → Settings (gear icon) → Resources → File Sharing
2. **Add the project directory**:
   - Path: `/Users/ganapathypichumani/dev/code/maia v2/demo_agentframework/taskpilot`
   - Or add parent: `/Users/ganapathypichumani/dev/code/maia v2/demo_agentframework`
3. **Click "Apply & Restart"**
4. **Wait for Docker to restart** (check Docker Desktop status)

**Verify:**
```bash
# Check if Docker is running
docker ps

# If you see mount errors, Docker Desktop file sharing is not configured correctly
```

### 3. Kill Stuck Processes

```bash
# Kill all processes using port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Verify port is free
lsof -ti:8000 || echo "✅ Port 8000 is free"
```

---

## Test Steps

> **⚠️ macOS Users:** Ensure Docker Desktop file sharing is configured (see Prerequisites section) before starting services.

### Step 1: Start Observability Stack

**⚠️ IMPORTANT - macOS Docker Desktop File Sharing:**

Before starting Docker services, ensure the project directory is shared with Docker Desktop:

1. **Open Docker Desktop** → Settings (gear icon) → Resources → File Sharing
2. **Add the project directory**: `/Users/ganapathypichumani/dev/code/maia v2/demo_agentframework/taskpilot`
   - Or add the parent directory: `/Users/ganapathypichumani/dev/code/maia v2/demo_agentframework`
3. **Click "Apply & Restart"** (Docker will restart)
4. **Wait for Docker to restart** before proceeding

**Alternative (if you can't add the path):**
- Use absolute paths in `docker-compose.observability.yml` pointing to a directory already shared (e.g., `/Users/ganapathypichumani/dev/docker/taskpilot/`)

```bash
# Start all Docker services
docker-compose -f docker-compose.observability.yml up -d

# Wait 30 seconds for services to initialize
sleep 30

# Verify all 7 services are running
docker ps | grep taskpilot
# Expected output should show:
# - taskpilot-prometheus
# - taskpilot-grafana
# - taskpilot-otel-collector
# - taskpilot-jaeger
# - taskpilot-elasticsearch
# - taskpilot-kibana
# - taskpilot-filebeat
```

**Verification:**
```bash
# Check Prometheus
curl http://localhost:9090/-/healthy
# Expected: "Prometheus is Healthy."

# Check Grafana
curl http://localhost:3000/api/health
# Expected: {"commit":"...","database":"ok",...}

# Check Jaeger
curl -s http://localhost:16686/api/services | jq
# Expected: JSON with services array

# Check Elasticsearch
curl http://localhost:9200
# Expected: JSON with cluster info

# Check Kibana
curl -s http://localhost:5601/api/status | jq '.status.overall.level'
# Expected: "available" (means Kibana is ready)
# Alternative: Check if container is running
docker ps | grep kibana | grep -q "Up" && echo "✅ Kibana container running" || echo "❌ Kibana not running"
```

---

### Step 2: Start Application Server

```bash
# Terminal 1: Navigate to project and activate virtual environment
cd /Users/ganapathypichumani/dev/code/maia\ v2/demo_agentframework/taskpilot

# ⚠️ CRITICAL: Always activate virtual environment first!
source .venv/bin/activate

# Verify package is installed (this will fail if venv not activated)
python3 -c "import taskpilot; print('✅ TaskPilot ready')" || {
    echo "❌ TaskPilot not installed or venv not activated."
    echo "   Solution: source .venv/bin/activate"
    exit 1
}

# Start server on port 8000
python3 main.py --server --port 8000

# Expected output:
# Starting TaskPilot in server mode on port 8000
#   Metrics: http://localhost:8000/metrics
#   Health: http://localhost:8000/health
#   Golden Signals: http://localhost:8000/golden-signals
# INFO:     Started server process [XXXXX]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Verification:**
```bash
# Wait 2-3 seconds for server to start, then test:
curl http://localhost:8000/
# Expected: JSON with service info and endpoints

curl http://localhost:8000/health
# Expected: {"status": "healthy", "checks": {...}, "timestamp": ...}
```

**If server hangs:**
- Check terminal output for errors
- Verify `.env` file exists and has `OPENAI_API_KEY`
- Check for port conflicts: `lsof -ti:8000`

---

### Step 3: Generate Data (Run Workflow)

```bash
# Terminal 2: Navigate to project and activate virtual environment
cd /Users/ganapathypichumani/dev/code/maia\ v2/demo_agentframework/taskpilot

# ⚠️ CRITICAL: Always activate virtual environment first!
source .venv/bin/activate

# Verify package is installed (this will fail if venv not activated)
python3 -c "import taskpilot; print('✅ TaskPilot ready')" || {
    echo "❌ TaskPilot not installed or venv not activated."
    echo "   Solution: source .venv/bin/activate"
    exit 1
}

# Run workflow to generate metrics/traces/logs/decision_logs
python3 main.py

# Expected output:
# Starting workflow (request_id=...)
# Creating agents...
# Agents created successfully
# Setting up middleware...
# Building workflow...
# Workflow built successfully
# Running workflow... (request_id=...)
# [Various agent execution logs]
# Workflow completed successfully
# 
# FINAL RESULT
# [Workflow result output]
```

# Wait for completion (should see "FINAL RESULT" output)
# This generates:
# - Metrics (workflow runs, agent invocations, latency, cost)
# - Traces (spans for each agent execution)
# - Logs (JSON logs with request_id, agent, level)
# - Decision logs (policy decisions: allow/deny)
```

**Verification:**
```bash
# Check that files were created
ls -lh metrics.json traces.jsonl decision_logs.jsonl logs/taskpilot.log
# All files should exist and have content
```

---

### Step 4: Verify Metrics (Prometheus & Grafana)

**Available in Docker tools:**
- ✅ Prometheus (port 9090)
- ✅ Grafana (port 3000) - via Prometheus
- ✅ File (`metrics.json`) - backup/persistence

#### Check Prometheus

```bash
# 1. Wait 15 seconds (Prometheus scrape interval)
sleep 15

# 2. Check Prometheus targets (should show port 8000, not 8001)
open http://localhost:9090/targets
# Expected: taskpilot job shows "UP" (green status)

# 3. Query metrics in Prometheus UI
open http://localhost:9090
# Query: workflow_runs
# Expected: Shows number > 0 (e.g., 1.0)

# 4. Query health metrics
# Query: health_status
# Expected: 1.0 (healthy), 0.5 (degraded), or 0.0 (unhealthy)

# 5. Query individual health checks
# Query: health_check_task_store
# Query: health_check_guardrails
# Expected: 1.0 (pass) or 0.0 (fail)

# 6. Check metrics endpoint directly
curl http://localhost:8000/metrics | grep -E "workflow_runs|health_status"
# Expected: Shows metric values
```

#### Check Grafana

```bash
# 1. Open Grafana
open http://localhost:3000
# Login: admin / admin (first time may prompt to change password - click "Skip")

# 2. Check if Golden Signals dashboard is auto-provisioned
#   - Go to: Dashboards → Browse (or click "Dashboards" in left menu)
#   - Look for: "Golden Signals - LLM Production"
#   - If found, click to open it
#   - Expected: Dashboard shows all 5 golden signals

# 3. If dashboard not found, check Grafana logs for errors
docker logs taskpilot-grafana 2>&1 | grep -i "dashboard\|provisioning" | tail -5
# If you see "Dashboard title cannot be empty", the JSON format is wrong
# Fix it (see troubleshooting section), then restart Grafana:
docker restart taskpilot-grafana
# Wait 10 seconds, then refresh browser
# Go to: Dashboards → Browse
# Dashboard should now appear

# 4. If still not found, check Grafana logs
docker logs taskpilot-grafana | grep -i dashboard
# Should show dashboard provisioning messages

# 5. Manual import (if auto-provisioning doesn't work)
#   - Go to: Dashboards → Import (or click "+" → Import)
#   - Option A: Click "Upload JSON file"
#     - Select: observability/grafana/golden-signals-dashboard.json
#   - Option B: Copy/paste JSON
#     - Run: cat observability/grafana/golden-signals-dashboard.json
#     - Copy the JSON output
#     - Paste into "Import via panel json" text area
#   - Click "Load" → Review → "Import"

# 6. Explore metrics manually
#   - Go to: Explore → Select Prometheus data source
#   - Query: workflow_runs
#   - Expected: Shows metric values
#   - Query: health_status
#   - Expected: Shows health status (1.0 = healthy)

# Troubleshooting "No data" in dashboard:
#   1. Verify metrics exist: curl http://localhost:8000/metrics | grep workflow_runs
#   2. Check Prometheus has data: http://localhost:9090 → Query: workflow_runs
#   3. Ensure application server is running: python3 main.py --server --port 8000
#   4. Ensure at least one workflow has been executed
#   5. Wait 15 seconds after workflow for Prometheus to scrape
#   6. Check dashboard time range (top right) - should include recent time
```

#### Check File

```bash
cat metrics.json | jq
# Expected: JSON with:
#   - counters: {workflow.runs: 1, workflow.success: 1, ...}
#   - gauges: {health_status: 1.0, health_check_task_store: 1.0, ...}
#   - histograms: {workflow.latency_ms: {...}, ...}
```

---

### Step 5: Verify Traces (Jaeger)

**Available in Docker tools:**
- ✅ Jaeger (port 16686) - **NOW WITH SPAN HIERARCHY**
- ✅ File (`traces.jsonl`) - backup/persistence

**Expected Span Hierarchy:**
```
workflow.run (root span)
├── PlannerAgent.run
├── ReviewerAgent.run
└── ExecutorAgent.run
```

#### Check Jaeger

```bash
# 1. Open Jaeger UI
open http://localhost:16686

# 2. Select Service: taskpilot
# 3. Click "Find Traces"
# Expected: Shows traces with spans

# 4. Click on a trace to see details:
#    - Span hierarchy:
#      * workflow.run (root)
#      * PlannerAgent.execute
#      * ReviewerAgent.execute
#      * ExecutorAgent.execute
#    - Timing information (duration for each span)
#    - Tags: agent, request_id, agent_type, latency_ms

# 5. Search by request_id
#    In Jaeger UI: Search → Tags → request_id=<value>
#    Expected: Shows trace for that request
```

#### Check File

```bash
# View traces file
tail -5 traces.jsonl | jq

# Or use utility (ensure venv is activated)
source .venv/bin/activate
python3 scripts/utils/view_traces.py --agents
# Expected: Shows agent invocations with timing

python3 scripts/utils/view_traces.py --summary
# Expected: Shows summary statistics
```

---

### Step 6: Verify Logs (Kibana)

**Available in Docker tools:**
- ✅ Kibana (port 5601) - via Elasticsearch
- ✅ File (`logs/taskpilot.log`) - source file

#### Check Kibana

```bash
# 1. Open Kibana
open http://localhost:5601

# 2. First time: Create index pattern
#    Management → Stack Management → Index Patterns → Create index pattern
#    Pattern: taskpilot-logs-*
#    Time field: @timestamp
#    Click "Create index pattern"

# 3. View logs
#    Discover → Select "taskpilot-logs-*"
#    Expected: Shows JSON logs with fields:
#      - timestamp
#      - level (INFO, ERROR, etc.)
#      - message
#      - request_id (if available)
#      - agent (if available)
#      - task_id (if available)

# 4. Filter by request_id
#    Add filter: request_id: "req-abc-123"
#    Expected: Shows all logs for that request

# 5. Filter by agent
#    Add filter: agent: "PlannerAgent"
#    Expected: Shows logs from PlannerAgent

# 6. Filter by level
#    Add filter: level: "ERROR"
#    Expected: Shows only error logs
```

#### Check File

```bash
# View log file
tail -10 logs/taskpilot.log | jq

# Or follow live
tail -f logs/taskpilot.log | jq
```

---

### Step 7: Verify Decision Logs (Kibana)

**Available in Docker tools:**
- ✅ Kibana (port 5601) - **NOW AVAILABLE** (via JSON logging)
- ✅ File (`decision_logs.jsonl`) - backup/persistence

#### Check Kibana

```bash
# 1. Open Kibana (if not already open)
open http://localhost:5601

# 2. Go to Discover → Select "taskpilot-logs-*"

# 3. Filter for decision logs
#    Add filter: log_type: "policy_decision"
#    Expected: Shows policy decision entries

# 4. View decision details
#    Fields available:
#      - decision_type (guardrails_input, tool_call, etc.)
#      - result (allow, deny, require_approval)
#      - tool_name
#      - agent_id
#      - latency_ms
#      - request_id (for correlation)
#      - reason
#      - decision_id

# 5. Filter by result
#    Add filter: result: "deny"
#    Expected: Shows only denied decisions (policy violations)

# 6. Filter by tool
#    Add filter: tool_name: "create_task"
#    Expected: Shows decisions for create_task tool

# 7. Filter by decision type
#    Add filter: decision_type: "tool_call"
#    Expected: Shows only tool call decisions
```

#### Check File

```bash
# View decision logs file
tail -5 decision_logs.jsonl | jq

# Or use utility (ensure venv is activated)
source .venv/bin/activate
python3 scripts/utils/view_decision_logs.py --recent 5
# Expected: Shows policy decisions (allow/deny) with context

python3 scripts/utils/view_decision_logs.py --summary
# Expected: Shows summary statistics

python3 scripts/utils/view_decision_logs.py --denied
# Expected: Shows only denied decisions
```

---

### Step 8: Verify Golden Signals

**Available in Docker tools:**
- ✅ Grafana (port 3000) - via dashboard
- ✅ HTTP endpoint (port 8000)

#### Check HTTP Endpoint

```bash
curl http://localhost:8000/golden-signals | jq
# Expected: JSON with:
#   {
#     "success_rate": 100.0,
#     "p95_latency_ms": 1234.56,
#     "cost_per_successful_task_usd": 0.0123,
#     "user_confirmed_correctness_percent": null,
#     "policy_violation_rate_percent": 0.0,
#     "status": {
#       "success_rate": "healthy",
#       "p95_latency": "healthy",
#       "cost_per_task": "healthy",
#       "policy_violations": "healthy"
#     },
#     "metadata": {
#       "workflow_runs": 1,
#       "workflow_success": 1,
#       "total_cost_usd": 0.0123,
#       "total_violations": 0
#     }
#   }
```

#### Check Grafana Dashboard

```bash
# 1. Open Grafana
open http://localhost:3000
# Login: admin / admin (first time may prompt to change password - click "Skip")

# 2. Check if dashboard is auto-provisioned
#   - Go to: Dashboards → Browse (or click "Dashboards" in left menu)
#   - Look for: "Golden Signals - LLM Production"
#   - If found, click to open it
#   - Expected: Dashboard shows all 5 golden signals

# 3. If dashboard not found, restart Grafana to reload provisioning
docker restart taskpilot-grafana
# Wait 10 seconds for Grafana to restart
# Refresh browser (F5 or Cmd+R)
# Go to: Dashboards → Browse
# Dashboard should now appear automatically

# 4. Verify dashboard shows data
#   - Open the "Golden Signals - LLM Production" dashboard
#   - Expected panels:
#     - Success Rate (%)
#     - p95 Latency (ms)
#     - Cost per Successful Task (USD)
#     - User-Confirmed Correctness (%)
#     - Policy Violation Rate (%)
#     - Success Rate Over Time (graph)
#     - p95 Latency Over Time (graph)

# 5. If dashboard shows "No data":
#   - Check time range (top right) - set to "Last 5 minutes" or "Last 1 hour"
#   - Verify metrics exist: curl http://localhost:8000/metrics | grep workflow_runs
#   - Check Prometheus has data: http://localhost:9090 → Query: workflow_runs
#   - Ensure application server is running: python3 main.py --server --port 8000
#   - Ensure at least one workflow has been executed
#   - Wait 15 seconds after workflow for Prometheus to scrape

# 6. Manual import (only if auto-provisioning doesn't work)
#   - Go to: Dashboards → Import
#   - Upload: observability/grafana/golden-signals-dashboard.json
#   - Click "Load" → "Import"
```

---

### Step 9: Verify Health Checks (Prometheus)

**Available in Docker tools:**
- ✅ Prometheus (port 9090) - **NOW AVAILABLE**
- ✅ Grafana (port 3000) - via Prometheus
- ✅ HTTP endpoint (port 8000)

#### Check Prometheus

```bash
# 1. Open Prometheus
open http://localhost:9090

# 2. Query health metrics
# Query: health_status
# Expected: 1.0 (healthy), 0.5 (degraded), or 0.0 (unhealthy)

# 3. Query individual checks
# Query: health_check_task_store
# Query: health_check_guardrails
# Expected: 1.0 (pass) or 0.0 (fail)

# 4. Check metrics endpoint
curl http://localhost:8000/metrics | grep health
# Expected output:
# # TYPE health_status gauge
# health_status 1.0
# # TYPE health_check_task_store gauge
# health_check_task_store 1.0
# # TYPE health_check_guardrails gauge
# health_check_guardrails 1.0
```

#### Check Grafana

```bash
# 1. Open Grafana
open http://localhost:3000

# 2. Go to Explore → Prometheus
# 3. Query: health_status
# Expected: Shows health status over time

# 4. Create dashboard panel
#    - Add panel
#    - Query: health_status
#    - Visualization: Stat
#    - Expected: Shows current health status
```

#### Check HTTP Endpoint

```bash
curl http://localhost:8000/health | jq
# Expected: {
#   "status": "healthy",
#   "checks": {
#     "task_store": {
#       "status": "pass",
#       "message": "Task store operational",
#       "details": {"stats": {...}}
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

---

### Step 10: Verify Configuration

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Test that paths are configurable
export METRICS_FILE=/tmp/test_metrics.json
python3 -c "from taskpilot.core.config import get_paths; print('Metrics file:', get_paths().metrics_file)"
# Expected: /tmp/test_metrics.json

# Reset
unset METRICS_FILE
```

---

## Data Availability Summary

| Data Type | Prometheus | Grafana | Jaeger | Kibana | File | HTTP Endpoint |
|-----------|------------|---------|--------|--------|------|---------------|
| **Metrics** | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ (`/metrics`) |
| **Golden Signals** | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ (`/golden-signals`) |
| **Traces** | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| **Logs** | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **Decision Logs** | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **Health** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ (`/health`) |

---

## Quick Verification Checklist

- [ ] All 7 Docker services running (`docker ps | grep taskpilot`)
- [ ] Application server running on port 8000 (`curl http://localhost:8000/health`)
- [ ] Root endpoint returns JSON (`curl http://localhost:8000/`)
- [ ] Health endpoint returns 200 (`curl http://localhost:8000/health`)
- [ ] Prometheus shows metrics (query: `workflow_runs`)
- [ ] Prometheus shows health metrics (query: `health_status`)
- [ ] Prometheus target is UP (`http://localhost:9090/targets`)
- [ ] Grafana can query Prometheus
- [ ] Jaeger shows traces (service: `taskpilot`)
- [ ] Kibana shows logs (index: `taskpilot-logs-*`)
- [ ] Kibana shows decision logs (filter: `log_type: "policy_decision"`)
- [ ] Golden signals endpoint returns all 5 signals
- [ ] All file-based data exists (metrics.json, traces.jsonl, logs, decision_logs.jsonl)

---

## Troubleshooting

### ModuleNotFoundError: No module named 'taskpilot'

**Symptoms:** `ModuleNotFoundError: No module named 'taskpilot'`

**Most Common Cause:** Virtual environment not activated!

**Quick Fix:**
```bash
# 1. Activate virtual environment (MOST COMMON FIX)
source .venv/bin/activate

# 2. Verify it works
python3 -c "import taskpilot; print('✅ TaskPilot installed')"
```

**If that doesn't work, package may not be installed:**

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install package in editable mode
# Option A: If using uv venv
uv pip install -e .

# Option B: If using standard venv
.venv/bin/python3 -m pip install -e .

# 3. Verify installation
python3 -c "import taskpilot; print('✅ TaskPilot installed')"

# 4. If still fails, check Python path
python3 -c "import sys; print('Python:', sys.executable)"
python3 -c "import sys; print('Python path:', sys.path)"
```

### Server Hangs on Startup

**Symptoms:** `python3 main.py --server --port 8000` hangs, no output

**Solutions:**
```bash
# 1. Ensure virtual environment is activated
source .venv/bin/activate

# 2. Kill stuck processes
lsof -ti:8000 | xargs kill -9 2>/dev/null

# 3. Check for missing API key
cat .env | grep OPENAI_API_KEY
# If missing: echo "OPENAI_API_KEY=your-key" > .env

# 4. Test config loading
python3 -c "from taskpilot.core.config import get_config; get_config(); print('OK')"
# If this fails, check error message

# 5. Check for import errors
python3 -c "import fastapi, uvicorn; print('Dependencies OK')"
```

### Docker Mount Errors (macOS)

**Symptoms:** `Mounts denied: The path ... is not shared from the host and is not known to Docker`

**Cause:** Docker Desktop on macOS requires explicit file sharing configuration.

**Solutions:**
```bash
# Option 1: Add path to Docker Desktop File Sharing (Recommended)
# 1. Open Docker Desktop → Settings → Resources → File Sharing
# 2. Click "+" to add a path
# 3. Add: /Users/ganapathypichumani/dev/code/maia v2/demo_agentframework/taskpilot
#    Or add parent: /Users/ganapathypichumani/dev/code/maia v2/demo_agentframework
# 4. Click "Apply & Restart"
# 5. Wait for Docker to restart, then try again

# Option 2: Use a directory already shared with Docker
# Check what's already shared:
# Docker Desktop → Settings → Resources → File Sharing
# Common shared paths: /Users, /tmp, /var/folders

# Option 3: Copy configs to a shared location
mkdir -p /tmp/taskpilot-observability/{prometheus,otel,filebeat,grafana/provisioning,logs}
cp observability/prometheus/prometheus.yml /tmp/taskpilot-observability/prometheus/
cp observability/otel/collector-config.yml /tmp/taskpilot-observability/otel/
cp observability/filebeat/filebeat.yml /tmp/taskpilot-observability/filebeat/
cp -r observability/grafana/provisioning/* /tmp/taskpilot-observability/grafana/provisioning/
# Then update docker-compose.observability.yml to use /tmp/taskpilot-observability/ paths

# Option 4: Use Docker volumes instead of bind mounts (requires config changes)
```

**Quick Fix:**
```bash
# Add the project directory to Docker Desktop file sharing, then:
docker-compose -f docker-compose.observability.yml down
docker-compose -f docker-compose.observability.yml up -d
```

### Prometheus Target Shows DOWN (Connection Refused)

**Symptoms:** `http://localhost:9090/targets` shows taskpilot as DOWN with `connection refused` error

**Common Cause:** Prometheus config pointing to wrong port (8001 instead of 8000)

**Solutions:**
```bash
# 1. Verify server is running on port 8000
curl http://localhost:8000/health
curl http://localhost:8000/metrics | head -5

# 2. Check what port Prometheus is trying to scrape
docker exec taskpilot-prometheus cat /etc/prometheus/prometheus.yml | grep -A 3 "taskpilot"
# Should show: targets: ['host.docker.internal:8000']
# If it shows 8001, that's the problem!

# 3. Fix the Prometheus config file (in project's observability folder)
# The config file is at: observability/prometheus/prometheus.yml
# Edit it to ensure it has: targets: ['host.docker.internal:8000']
sed -i '' 's/host.docker.internal:8001/host.docker.internal:8000/g' observability/prometheus/prometheus.yml

# 4. Restart Prometheus to reload config
docker restart taskpilot-prometheus

# 5. Wait ~15 seconds, then check target status
# Go to: http://localhost:9090/targets
# Should show "UP" after next scrape interval

# 6. If still down, check Prometheus logs
docker logs taskpilot-prometheus | tail -20
```

### No Data in Kibana

**Symptoms:** Kibana shows no logs or decision logs

**Solutions:**
```bash
# 1. Check if logs are being written
tail -f logs/taskpilot.log | jq

# 2. Verify Filebeat is running
docker ps | grep filebeat

# 3. Check Filebeat logs
docker logs taskpilot-filebeat --tail 20

# 4. Verify Elasticsearch has indices
curl http://localhost:9200/_cat/indices | grep taskpilot

# 5. Create index pattern in Kibana
# Management → Index Patterns → Create
# Pattern: taskpilot-logs-*
```

### Grafana Dashboard Not Appearing (Auto-Provisioning)

**Symptoms:** Dashboard doesn't appear in Grafana after starting services

**Common Error:** Grafana logs show: `"Dashboard title cannot be empty"`

**Cause:** File-based provisioning requires dashboard JSON at root level, not wrapped in `{"dashboard": {...}}`

**Solutions:**
```bash
# 1. Verify dashboard file format is correct for provisioning
# File-based provisioning needs dashboard object at root, not wrapped
head -5 observability/grafana/provisioning/dashboards/golden-signals-dashboard.json
# Should start with: {
#   "title": "Golden Signals - LLM Production",
# NOT: {
#   "dashboard": {
#     "title": ...

# 2. If wrong format, fix it:
python3 -c "
import json
with open('observability/grafana/golden-signals-dashboard.json') as f:
    data = json.load(f)
    dashboard = data['dashboard']
with open('observability/grafana/provisioning/dashboards/golden-signals-dashboard.json', 'w') as f:
    json.dump(dashboard, f, indent=2)
print('✅ Dashboard JSON fixed')
"

# 3. Restart Grafana to reload provisioning
docker restart taskpilot-grafana

# 4. Wait 10 seconds, then refresh browser
# Go to: Dashboards → Browse
# Dashboard should appear automatically

# 5. Check Grafana logs for provisioning errors
docker logs taskpilot-grafana 2>&1 | grep -i "dashboard\|provisioning" | tail -5
# Should show: "successfully provisioned" or similar (no errors)

# 6. If still not appearing, check logs for specific error:
docker logs taskpilot-grafana 2>&1 | grep -A 2 "failed to load dashboard"
```

### Grafana Dashboard Shows "No Data"

**Symptoms:** Dashboard appears but shows "No data" for all panels

**Solutions:**
```bash
# 1. Verify metrics endpoint has data
curl http://localhost:8000/metrics | grep workflow_runs
# Should show: workflow_runs 1.0 (or higher)

# 2. Check Prometheus has scraped the data
open http://localhost:9090
# Query: workflow_runs
# Should show a value > 0

# 3. Verify Prometheus target is UP
open http://localhost:9090/targets
# taskpilot job should show "UP" (green)

# 4. Check dashboard time range
# In Grafana dashboard, check top-right time selector
# Should be set to "Last 5 minutes" or "Last 1 hour"
# If set to "Last 30 days" with no recent data, change to recent range

# 5. Verify data source is correct
# Dashboard → Settings → Variables
# Ensure "Prometheus" data source is selected

# 6. Check panel queries
# Click on a panel → Edit → Query
# Verify query matches available metrics:
#   - workflow_runs (not workflow.runs)
#   - workflow_success (not workflow.success)
#   - workflow_latency_ms_p95 (after code update)
#   - llm_cost_total (not llm.cost.total)

# 7. If still no data, generate new metrics
# Run workflow: python3 main.py
# Wait 15 seconds for Prometheus to scrape
# Refresh dashboard
```

### No Span Hierarchy in Jaeger

**Symptoms:** Traces appear in Jaeger but spans are flat (no parent-child relationships)

**Cause:** OpenTelemetry context propagation not properly established

**Solutions:**
```bash
# 1. Verify workflow span is created
# Check traces.jsonl file:
tail -5 traces.jsonl | jq '.name' | grep workflow.run
# Should show: "workflow.run"

# 2. Verify agent spans have parent_span_id
tail -5 traces.jsonl | jq 'select(.name | contains("Agent")) | {name, parent_span_id}'
# Should show parent_span_id pointing to workflow.run span

# 3. Check OpenTelemetry export is working
docker logs taskpilot-otel-collector | grep -i "span\|trace" | tail -10
# Should show spans being received

# 4. Restart services to pick up code changes
docker restart taskpilot-otel-collector taskpilot-jaeger
# Then run workflow again: python3 main.py

# 5. Verify in Jaeger
# Go to: http://localhost:16686
# Search: Service=taskpilot, Operation=workflow.run
# Click trace → Should show nested hierarchy
```

### No Traces in Jaeger

**Symptoms:** Jaeger shows no traces

**Solutions:**
```bash
# 1. Check if traces file exists
tail -5 traces.jsonl | jq

# 2. Verify OTel Collector is running
docker ps | grep otel-collector

# 3. Check OTel Collector logs
docker logs taskpilot-otel-collector --tail 20

# 4. Verify OTel is enabled
echo $OTEL_ENABLED
# Should be "true" or unset (defaults to true)

# 5. Check OTLP endpoint
echo $OTEL_EXPORTER_OTLP_ENDPOINT
# Should be "http://localhost:4317" or unset (defaults to this)
```

---

## Expected Test Results

After completing all steps, you should see:

### Metrics
- `workflow_runs` > 0
- `workflow_success` > 0
- `health_status` = 1.0
- `health_check_task_store` = 1.0
- `health_check_guardrails` = 1.0

### Traces
- At least 3 spans (workflow, planner, reviewer, executor)
- Spans linked by request_id
- Timing information for each span

### Logs
- JSON logs with request_id, agent, level
- At least 10 log entries
- Mix of INFO, DEBUG, ERROR levels

### Decision Logs
- At least 3 decision entries
- Mix of ALLOW and DENY results
- Tool names and agent IDs present

### Golden Signals
- All 5 signals present
- Status indicators (healthy/warning/critical)
- Metadata with workflow counts

---

## Cleanup

```bash
# Stop application server (Ctrl+C in Terminal 1)

# Stop Docker services
docker-compose -f docker-compose.observability.yml down

# Optional: Clean test files
rm -f /tmp/test_metrics.json
```

---

**Note:** This document is maintained as the authoritative reference for integration testing. All steps are verified and kept up-to-date with the current implementation.
