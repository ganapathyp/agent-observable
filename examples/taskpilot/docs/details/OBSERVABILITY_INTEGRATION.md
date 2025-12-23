# Observability Integration: Metrics, Traces, and Logs

## Overview

This document explains how metrics, traces, and logs are integrated into the codebase, with code snippets showing the implementation and how to view them in Docker tools (Prometheus, Grafana, Jaeger, Kibana).

---

## 1. Metrics Integration

### Code Implementation

**Location:** `src/core/middleware.py` and `src/core/observability.py`

#### Automatic Metrics Collection

Metrics are automatically collected in the middleware for every agent execution:

```python
# src/core/middleware.py
from taskpilot.core.observability import (
    RequestContext,
    get_metrics_collector,
    get_tracer,
    track_llm_metrics
)

async def audit_and_policy_middleware(context, agent_name, agent_type):
    """Middleware that automatically collects metrics."""
    metrics = get_metrics_collector()
    start_time = time.time()
    
    # 1. Increment invocation counter
    metrics.increment_counter(f"agent.{agent_name}.invocations")
    
    # 2. Track LLM token usage and cost
    if hasattr(context.result, 'agent_run_response'):
        track_llm_metrics(context.result, agent_name, metrics)
    
    # 3. Record latency histogram
    latency_ms = (time.time() - start_time) * 1000
    metrics.record_histogram(f"agent.{agent_name}.latency_ms", latency_ms)
    
    # 4. Track workflow metrics
    metrics.increment_counter("workflow.runs")
    metrics.increment_counter("workflow.success")
```

#### Cost Metrics Tracking

**Location:** `src/core/llm_cost_tracker.py`

```python
# Automatic cost tracking in middleware
from taskpilot.core.llm_cost_tracker import track_llm_metrics

# After agent execution
track_llm_metrics(context.result, agent_name, metrics)
# Records:
# - llm.cost.total
# - llm.cost.agent.{agent_name}
# - llm.cost.model.{model}
# - llm.tokens.input.total
# - llm.tokens.output.total
```

#### Golden Signals Calculation

**Location:** `src/core/observability.py`

```python
# Get Golden Signals
metrics = get_metrics_collector()
signals = metrics.get_golden_signals()

# Returns:
# {
#   "success_rate": 95.0,
#   "p95_latency_ms": 1234.56,
#   "cost_per_successful_task_usd": 0.0823,
#   "user_confirmed_correctness_percent": None,
#   "policy_violation_rate_percent": 0.5
# }
```

### Viewing Metrics in Docker Tools

#### Prometheus

**Access:** http://localhost:9090

**Query Examples:**
```promql
# Total workflow runs
workflow_runs

# Success rate
(workflow_success / workflow_runs) * 100

# Cost per successful task
llm_cost_total / workflow_success

# Agent latency (p95)
histogram_quantile(0.95, rate(agent_planneragent_latency_ms_bucket[5m]))

# Total cost
llm_cost_total
```

**Configuration:**
```yaml
# observability/prometheus/prometheus.yml
scrape_configs:
  - job_name: 'taskpilot'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

#### Grafana

**Access:** http://localhost:3000 (admin/admin)

**Import Dashboard:**
- File: `observability/grafana/golden-signals-dashboard.json`
- Shows: All 5 Golden Signals with thresholds

**Query in Explore:**
```promql
# Cost metrics
llm_cost_total
llm_cost_agent_planneragent
llm_cost_model_gpt_4o_mini

# Token metrics
llm_tokens_input_total
llm_tokens_output_total
llm_tokens_total_all
```

#### HTTP Endpoint

**Access:** http://localhost:8000/metrics (when running `python main.py --server`)

**Format:** Prometheus text format
```
# TYPE workflow_runs counter
workflow_runs 10.0

# TYPE llm_cost_total counter
llm_cost_total 0.823
```

---

## 2. Traces Integration

### Code Implementation

**Location:** `src/core/middleware.py` and `src/core/observability.py`

#### Automatic Trace Collection

Traces are automatically created for every agent execution:

```python
# src/core/middleware.py
from taskpilot.core.observability import get_tracer, RequestContext

async def audit_and_policy_middleware(context, agent_name, agent_type):
    """Middleware that automatically creates traces."""
    tracer = get_tracer()
    request_id = get_request_id()
    
    # Start span
    span = tracer.start_span(
        name=f"{agent_name}.execute",
        request_id=request_id,
        tags={"agent": agent_name, "agent_type": agent_type.value}
    )
    
    try:
        # Execute agent
        result = await agent.run(...)
        
        # Add result to span
        span.tags["output_length"] = len(str(result))
        span.logs.append({
            "message": f"{agent_name} completed",
            "timestamp": time.time()
        })
        
        return result
    finally:
        # End span (automatically exports to OpenTelemetry)
        tracer.end_span(span)
```

#### OpenTelemetry Export

**Location:** `src/core/otel_integration.py` and `src/core/observability.py`

```python
# src/core/observability.py (in Tracer.end_span)
def end_span(self, span: Span):
    """End a span and export to OpenTelemetry."""
    span.end_time = time.time()
    
    # Persist to file
    self._persist_span(span)
    
    # Export to OpenTelemetry
    try:
        from .otel_integration import export_span_to_otel
        export_span_to_otel(
            span_name=span.name,
            start_time=span.start_time,
            end_time=span.end_time,
            request_id=span.request_id,
            parent_span_id=span.parent_span_id,
            tags=span.tags,
            logs=span.logs
        )
    except ImportError:
        pass
```

#### OpenTelemetry Initialization

**Location:** `main.py`

```python
# main.py
from taskpilot.core.otel_integration import initialize_opentelemetry

# Initialize on startup
otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
otel_enabled = os.environ.get("OTEL_ENABLED", "true").lower() == "true"

initialize_opentelemetry(
    service_name="taskpilot",
    otlp_endpoint=otlp_endpoint,
    enabled=otel_enabled
)
```

### Viewing Traces in Docker Tools

#### Jaeger

**Access:** http://localhost:16686

**Flow:**
1. Application creates spans → OpenTelemetry SDK
2. OpenTelemetry SDK → OTLP gRPC → OpenTelemetry Collector (port 4317)
3. Collector → Jaeger (port 16686)

**Search:**
- Service: `taskpilot`
- Operation: `PlannerAgent.execute`, `ExecutorAgent.execute`, etc.
- Tags: `agent=PlannerAgent`, `request_id=abc-123`

#### File-Based Traces

**Location:** `traces.jsonl`

**View with CLI:**
```bash
python scripts/utils/view_traces.py --agents
python scripts/utils/view_traces.py --request-id abc-123
```

**Format:**
```json
{
  "span_id": "span-123",
  "name": "PlannerAgent.execute",
  "start_time": 1234567890.123,
  "end_time": 1234567890.456,
  "request_id": "req-abc-123",
  "tags": {"agent": "PlannerAgent"},
  "logs": [{"message": "Agent completed", "timestamp": 1234567890.4}]
}
```

---

## 3. Logs Integration

### Code Implementation

**Location:** `main.py` and throughout codebase

#### JSON Logging Setup

```python
# main.py
from pythonjsonlogger import jsonlogger

# Configure JSON logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / "taskpilot.log"
file_handler = logging.FileHandler(log_file)
json_formatter = jsonlogger.JsonFormatter(
    '%(timestamp)s %(level)s %(name)s %(message)s',
    timestamp=True
)
file_handler.setFormatter(json_formatter)
root_logger.addHandler(file_handler)
```

#### Structured Logging with Context

```python
# src/core/middleware.py
import logging

logger = logging.getLogger(__name__)

# Log with request ID context
request_id = get_request_id()
logger.info(
    f"[AUDIT] {agent_name} Input: {input_text}",
    extra={"request_id": request_id, "agent": agent_name}
)

# Log task creation
logger.info(
    f"[TASK] Created task: {task.id} - {title}",
    extra={
        "request_id": request_id,
        "task_id": task.id,
        "task_status": task.status.value
    }
)
```

#### Decision Logging

**Location:** `src/core/guardrails/decision_logger.py`

```python
# Structured decision logging
from taskpilot.core.guardrails.decision_logger import DecisionLogger

decision_logger = DecisionLogger()

decision = PolicyDecision.create(
    decision_type=DecisionType.TOOL_CALL,
    result=DecisionResult.ALLOW,
    reason="Policy check passed",
    context={"tool_name": "create_task"},
    tool_name="create_task",
    agent_id="PlannerAgent",
    latency_ms=15.2
)

await decision_logger.log_decision(decision)
# Writes to decision_logs.jsonl
```

### Viewing Logs in Docker Tools

#### Kibana

**Access:** http://localhost:5601

**Setup:**
1. Create index pattern: `taskpilot-logs-*`
2. View in Discover

**Log Flow:**
1. Application writes JSON logs → `logs/taskpilot.log`
2. Filebeat (Docker) reads from mounted volume
3. Filebeat → Elasticsearch
4. Kibana queries Elasticsearch

**Query Examples:**
```
# Filter by request ID
request_id: "req-abc-123"

# Filter by agent
agent: "PlannerAgent"

# Filter by level
level: "ERROR"

# Filter by task
task_id: "task-123"

# Filter by log type (decision logs)
log_type: "policy_decision"

# Filter by policy decision result
result: "deny"

# Filter by tool name
tool_name: "create_task"
```

#### File-Based Logs

**Location:** `logs/taskpilot.log`

**Format (JSON):**
```json
{
  "timestamp": "2024-12-21T10:00:00.123Z",
  "level": "INFO",
  "name": "taskpilot.core.middleware",
  "message": "[AUDIT] PlannerAgent Input: Create a task",
  "request_id": "req-abc-123",
  "agent": "PlannerAgent"
}
```

---

## 4. Request ID Correlation

### Code Implementation

**Location:** `src/core/observability.py`

```python
# Generate and set request ID
from taskpilot.core.observability import RequestContext, get_request_id

# In main.py
with RequestContext() as req_ctx:
    request_id = req_ctx.request_id
    logger.info(f"Starting workflow (request_id={request_id})")
    
    # Request ID is automatically available in all logs, traces, metrics
    # No need to pass it explicitly
```

**Automatic Correlation:**
- All logs include `request_id` in JSON format
- All traces include `request_id` in tags
- All metrics can be filtered by `request_id` (via tags)

---

## 5. Complete Integration Example

### Full Workflow with Observability

```python
# main.py
from taskpilot.core.observability import RequestContext, get_metrics_collector

async def run_workflow_once():
    # 1. Set up request context (automatic request ID)
    with RequestContext() as req_ctx:
        request_id = req_ctx.request_id
        
        # 2. Create agents (middleware automatically adds observability)
        planner = create_planner()
        planner.middleware = create_audit_and_policy_middleware(planner.name)
        
        # 3. Run workflow (metrics, traces, logs collected automatically)
        metrics = get_metrics_collector()
        metrics.increment_counter("workflow.runs")
        
        workflow_start = time.time()
        result = await workflow.run("Create a task")
        workflow_latency = (time.time() - workflow_start) * 1000
        
        # 4. Record workflow metrics
        metrics.record_histogram("workflow.latency_ms", workflow_latency)
        metrics.increment_counter("workflow.success")
        
        # 5. All observability data is now available:
        # - Metrics: In metrics.json and /metrics endpoint
        # - Traces: In traces.jsonl and Jaeger
        # - Logs: In logs/taskpilot.log and Kibana
```

---

## 6. Viewing in Docker Tools - Quick Reference

### Metrics

**Prometheus:** http://localhost:9090
- Query: `workflow_runs`, `llm_cost_total`
- Targets: http://localhost:9090/targets (check if UP)
- **Query Examples:**
  ```promql
  # Total workflow runs
  workflow_runs
  
  # Success rate
  (workflow_success / workflow_runs) * 100
  
  # Cost per successful task
  llm_cost_total / workflow_success
  
  # p95 latency
  histogram_quantile(0.95, rate(workflow_latency_ms_bucket[5m]))
  ```

**Grafana:** http://localhost:3000 (admin/admin)
- **Explore:** Explore → Prometheus → Query metrics
- **Dashboards:** Import `observability/grafana/golden-signals-dashboard.json`
- **Golden Signals Dashboard:** Shows all 5 signals with thresholds

**HTTP Endpoint:** http://localhost:8000/metrics
- Prometheus text format
- Requires: `python main.py --server --port 8000`
- **Example:**
  ```bash
  curl http://localhost:8000/metrics | grep workflow
  ```

**Health Check CLI:**
```bash
python scripts/utils/health_check.py --metrics
# Shows all metrics in human-readable format
```

### Traces

**Jaeger:** http://localhost:16686
- **Service:** `taskpilot`
- **Search by:** Operation, tags, request_id
- **View:** Span hierarchy, timing, tags (agent, model, tokens, cost)

**File-Based (CLI):**
```bash
# View agent calls
python scripts/utils/view_traces.py --agents

# View by request ID
python scripts/utils/view_traces.py --request-id abc-123

# View summary
python scripts/utils/view_traces.py --summary
```

**File:** `traces.jsonl` (JSONL format, one span per line)

### Logs

**Kibana:** http://localhost:5601
- **Index Pattern:** `taskpilot-logs-*` (create on first use)
- **Query Examples:**
  ```
  request_id: "req-abc-123"
  agent: "PlannerAgent"
  level: "ERROR"
  task_id: "task-123"
  ```
- **Discover:** View structured JSON logs with filters

**File:** `logs/taskpilot.log`
- JSON format (one log per line)
- **View:**
  ```bash
  tail -f logs/taskpilot.log | jq
  ```

### Golden Signals

**HTTP Endpoint:** http://localhost:8000/golden-signals
```bash
curl http://localhost:8000/golden-signals | jq
```

**Response includes:**
- Success rate with status (healthy/warning/critical)
- p95 latency with status
- Cost per successful task with status
- Policy violation rate with status
- Metadata (workflow_runs, total_cost, etc.)

**Grafana Dashboard:**
- Import: `observability/grafana/golden-signals-dashboard.json`
- Shows all 5 signals with status indicators

### Health Checks

**HTTP Endpoint:** http://localhost:8000/health
```bash
curl http://localhost:8000/health | jq
```

**Response includes:**
- Overall status (healthy/degraded/unhealthy)
- Individual check statuses (task_store, guardrails)
- Timestamp

**Prometheus Metrics:**
- `health_status` (gauge): 1.0 = healthy, 0.5 = degraded, 0.0 = unhealthy
- `health_check_task_store` (gauge): 1.0 = pass, 0.0 = fail
- `health_check_guardrails` (gauge): 1.0 = pass, 0.0 = fail

**Query in Prometheus:**
```promql
# Overall health
health_status

# Individual checks
health_check_task_store
health_check_guardrails
```

---

## 7. Key Metrics Tracked

### Workflow Metrics
- `workflow.runs` - Total executions
- `workflow.success` - Successful executions
- `workflow.errors` - Failed executions
- `workflow.latency_ms` - Latency histogram

### Agent Metrics
- `agent.{agent_name}.invocations` - Invocation count
- `agent.{agent_name}.latency_ms` - Latency histogram
- `agent.{agent_name}.success` - Success count
- `agent.{agent_name}.errors` - Error count

### Cost Metrics
- `llm.cost.total` - Total cost (USD)
- `llm.cost.agent.{agent_name}` - Cost per agent
- `llm.cost.model.{model}` - Cost per model
- `llm.tokens.input.total` - Total input tokens
- `llm.tokens.output.total` - Total output tokens

### Task Metrics
- `tasks.created` - Tasks created
- `tasks.approved` - Tasks approved
- `tasks.rejected` - Tasks rejected

### Policy Metrics
- `agent.{agent_name}.policy.violations` - Violations per agent
- `policy.violations.total` - Total violations

---

## 8. Key Traces Tracked

### Span Hierarchy
```
workflow.run
├── PlannerAgent.execute
│   ├── create_task (tool call)
│   └── LLM call
├── ReviewerAgent.execute
│   └── LLM call
└── ExecutorAgent.execute
    └── notify_external_system (tool call)
```

### Span Tags
- `agent` - Agent name
- `agent_type` - Agent type (PLANNER, REVIEWER, EXECUTOR)
- `request_id` - Request ID for correlation
- `latency_ms` - Execution latency
- `tool_name` - Tool name (if tool call)

---

## 9. Key Logs Tracked

### Audit Logs
- `[AUDIT] {agent} Input: {text}` - Agent input
- `[AUDIT] {agent} Output: {text}` - Agent output

### Task Logs
- `[TASK] Created task: {id}` - Task creation
- `[TASK] Task {id} approved` - Task approval
- `[TASK] Task {id} rejected` - Task rejection

### Error Logs
- Structured error logs with stack traces
- Includes request_id for correlation

### Decision Logs
- Policy decisions (OPA, NeMo Guardrails)
- Tool call authorizations
- Structured JSONL format
- **Available in Kibana** (via JSON logging to Filebeat)

---

## 10. Data Storage and Persistence

### File Locations

All data files are configurable via environment variables (see [CONFIGURATION.md](CONFIGURATION.md)). Default locations:

- **Metrics:** `metrics.json` (project root)
- **Traces:** `traces.jsonl` (project root, JSONL format)
- **Decision Logs:** `decision_logs.jsonl` (project root, JSONL format)
- **Logs:** `logs/taskpilot.log` (JSON format, one log per line)
- **Tasks:** `.tasks.json` (project root)

### Viewing Stored Data

**Metrics:**
```bash
cat metrics.json | jq
```

**Traces:**
```bash
python scripts/utils/view_traces.py --agents
python scripts/utils/view_traces.py --request-id abc-123
python scripts/utils/view_traces.py --summary
```

**Decision Logs:**
```bash
python scripts/utils/view_decision_logs.py --recent
python scripts/utils/view_decision_logs.py --summary
python scripts/utils/view_decision_logs.py --denied
```

**Logs:**
```bash
tail -f logs/taskpilot.log | jq
```

### Persistence Strategy

- **Metrics:** Persisted to `metrics.json` for cross-process sharing (JSON format)
- **Traces:** Persisted to `traces.jsonl` (append-only, JSONL format, one span per line)
- **Decision Logs:** Persisted to `decision_logs.jsonl` (append-only, JSONL format, one decision per line)
- **Logs:** Written to `logs/taskpilot.log` (JSON format, one log per line, rotated by log system)

**Production:** Use absolute paths via environment variables:
```bash
export METRICS_FILE=/var/lib/taskpilot/metrics.json
export TRACES_FILE=/var/lib/taskpilot/traces.jsonl
export DECISION_LOGS_FILE=/var/lib/taskpilot/decision_logs.jsonl
export LOGS_DIR=/var/log/taskpilot
```

### File Formats

**JSONL Format (Traces, Decision Logs):**
- One JSON object per line
- Append-only (no overwrites)
- Easy to stream and parse
- Example:
  ```json
  {"span_id": "span-123", "name": "PlannerAgent.execute", "start_time": 1234567890.123}
  {"span_id": "span-124", "name": "ExecutorAgent.execute", "start_time": 1234567890.456}
  ```

**JSON Format (Metrics, Tasks):**
- Single JSON object
- Read/write entire file
- Used for cross-process sharing
- Example:
  ```json
  {
    "counters": {"workflow.runs": 10},
    "gauges": {"tasks.active": 2},
    "histograms": {}
  }
  ```

---

## 10. Docker Setup

### Start Observability Stack

```bash
docker-compose -f docker-compose.observability.yml up -d
```

**Services:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Jaeger: http://localhost:16686
- OpenTelemetry Collector: localhost:4317
- Elasticsearch: http://localhost:9200
- Kibana: http://localhost:5601
- Filebeat: (runs in background)

### Configuration Files

- `observability/prometheus/prometheus.yml` - Prometheus config
- `observability/grafana/provisioning/` - Grafana dashboards
- `observability/otel/collector-config.yml` - OTel collector config
- `observability/filebeat/filebeat.yml` - Filebeat config

---

## 11. Testing Observability

### Test Metrics

```python
# tests/test_golden_signals.py
from taskpilot.core.observability import MetricsCollector

def test_golden_signals():
    metrics = MetricsCollector(metrics_file=None)  # In-memory for tests
    metrics.increment_counter("workflow.runs", value=100)
    metrics.increment_counter("workflow.success", value=95)
    
    signals = metrics.get_golden_signals()
    assert signals["success_rate"] == 95.0
```

### Test Traces

```python
# tests/test_otel_integration.py
from taskpilot.core.otel_integration import initialize_opentelemetry

def test_trace_export():
    initialize_opentelemetry(enabled=True)
    # Test span export
```

---

*All observability features are automatically integrated. No manual instrumentation needed in application code.*
