# Docker Tools Integration

This guide shows how to view all observability data (metrics, traces, policy decisions, logs) in Docker-based observability tools.

## Quick Start

1. **Start Docker services:**
   ```bash
   cd examples/taskpilot
   docker-compose -f docker-compose.observability.yml up -d
   ```

2. **Start your application:**
   ```bash
   python main.py --server --port 8000
   ```

3. **Run a workflow:**
   ```bash
   python main.py "Create a test task"
   ```

4. **View data in tools:**
   - **Prometheus:** http://localhost:9090
   - **Grafana:** http://localhost:3000 (admin/admin)
   - **Jaeger:** http://localhost:16686
   - **Kibana:** http://localhost:5601

## Metrics → Prometheus & Grafana

### Prometheus

**URL:** http://localhost:9090

**What to Check:**
1. **Targets:** Status → Targets → Verify `taskpilot` is **UP**
2. **Metrics:** Graph → Query:
   - `llm_cost_total`
   - `workflow_runs`
   - `policy_violations_total`
   - `workflow_success`

**Query Examples:**
```promql
# Total LLM cost
llm_cost_total

# Cost per successful task
llm_cost_total / clamp_min(workflow_success, 1)

# Success rate
(workflow_success / workflow_runs) * 100

# P95 latency
workflow_latency_ms_p95

# Policy violation rate
(policy_violations_total / workflow_runs) * 100
```

### Grafana

**URL:** http://localhost:3000  
**Login:** admin / admin

**Setup:**
1. **Data Source:** Configuration → Data Sources → Add Prometheus
   - URL: `http://prometheus:9090`
   - Save & Test

2. **Import Dashboard:**
   - Dashboards → Import
   - Upload: `examples/taskpilot/observability/grafana/golden-signals-dashboard.json`
   - Select Prometheus data source
   - Import

**Dashboard Shows:**
- ✅ Success Rate (with thresholds)
- ✅ P95 Latency (with thresholds)
- ✅ Cost per Successful Task (with thresholds)
- ✅ Policy Violation Rate (with thresholds)
- ✅ Time series graphs

## Traces → Jaeger

**URL:** http://localhost:16686

**What to Check:**
1. **Service:** Select your service (e.g., `taskpilot`) from dropdown
2. **Find Traces:** Click "Find Traces"
3. **View Trace:** Click on a trace to see hierarchy

**Expected Hierarchy:**
```
taskpilot.workflow.run
  ├─ taskpilot.agent.PlannerAgent.run
  │   └─ taskpilot.tool.create_task.call
  ├─ taskpilot.agent.ExecutorAgent.run
  │   └─ taskpilot.tool.update_task.call
  └─ taskpilot.agent.ReviewerAgent.run
      └─ taskpilot.tool.review_task.call
```

**Trace Details:**
- **Timeline** - When each span executed
- **Duration** - How long each span took
- **Tags** - Request ID, agent name, tool name, latency
- **Logs** - Span logs (if any)
- **Hierarchy** - Parent-child relationships

**Query Examples:**
- **Service:** `taskpilot`
- **Tags:** `error=true` (find traces with errors)
- **Tags:** `request.id=abc123` (find trace by request ID)

## Policy Decisions → Kibana

**URL:** http://localhost:5601

**Setup:**
1. **Create Index Pattern:**
   - Management → Index Patterns → Create
   - Pattern: `decision-logs-*`
   - Time field: `timestamp`
   - Create

2. **Discover:**
   - Discover → Select `decision-logs-*` index
   - Search and filter decisions

**View Decisions:**
- **All Decisions:** Discover → `decision-logs-*`
- **Filter by Type:** `decision_type:tool_call`
- **Filter by Result:** `result:deny`
- **Filter by Agent:** `agent_id:PlannerAgent`

**Decision Fields:**
- `decision_id` - Unique decision ID
- `timestamp` - Decision timestamp
- `decision_type` - Type (tool_call, opa, guardrails, human_review)
- `result` - Result (allow, deny, requires_approval)
- `tool_name` - Tool name (if applicable)
- `agent_id` - Agent identifier
- `context` - Additional context

## Logs → Elasticsearch & Kibana

**URL:** http://localhost:5601

**Setup:**
1. **Create Index Pattern:**
   - Management → Index Patterns → Create
   - Pattern: `taskpilot-*` (or your service name)
   - Time field: `@timestamp`
   - Create

2. **Discover:**
   - Discover → Select your index pattern
   - Search and filter logs

**Log Fields:**
- `@timestamp` - Log timestamp
- `level` - Log level (INFO, ERROR, WARNING)
- `message` - Log message
- `request.id` - Request ID (for correlation)
- `agent_name` - Agent name
- `tool_name` - Tool name

**Query Examples:**
- **Find errors:** `level:ERROR`
- **Find by request ID:** `request.id:abc123`
- **Find agent logs:** `agent_name:PlannerAgent`

## Docker Compose Services

The `docker-compose.observability.yml` includes:

- **Prometheus** - Metrics storage (port 9090)
- **Grafana** - Metrics visualization (port 3000)
- **Jaeger** - Distributed tracing (port 16686)
- **Elasticsearch** - Log storage (port 9200)
- **Kibana** - Log visualization (port 5601)
- **OpenTelemetry Collector** - Trace collection (port 4317)
- **Filebeat** - Log shipping

## Configuration

### Application Configuration

Ensure your application exports metrics:

```python
# In your FastAPI app
@app.get("/metrics")
def metrics():
    from agent_observable_core.observability import get_metrics
    metrics = get_metrics()
    return Response(metrics.to_prometheus(), media_type="text/plain")
```

### Prometheus Configuration

Prometheus scrapes your application:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'taskpilot'
    static_configs:
      - targets: ['host.docker.internal:8000']
```

### OpenTelemetry Configuration

Traces are exported to OpenTelemetry Collector:

```python
# In your application
from agent_observable_core.otel_integration import OpenTelemetryIntegration

otel = OpenTelemetryIntegration(
    service_name="taskpilot",
    otlp_endpoint="http://localhost:4317"
)
```

## Troubleshooting

### Metrics Not Showing

1. **Check Prometheus target:**
   - http://localhost:9090/status/targets
   - Verify target is **UP**

2. **Check metrics endpoint:**
   ```bash
   curl http://localhost:8000/metrics
   ```

3. **Check Prometheus logs:**
   ```bash
   docker-compose -f docker-compose.observability.yml logs prometheus
   ```

### Traces Not Showing

1. **Check Jaeger service:**
   - http://localhost:16686
   - Verify service appears in dropdown

2. **Check OpenTelemetry Collector:**
   ```bash
   docker-compose -f docker-compose.observability.yml logs otel-collector
   ```

3. **Verify OTLP endpoint:**
   - Default: `http://localhost:4317`
   - Check application logs for connection errors

### Policy Decisions Not Showing

1. **Check decision log file:**
   ```bash
   ls -lh decision_logs.jsonl
   tail -1 decision_logs.jsonl | jq
   ```

2. **Check Elasticsearch:**
   ```bash
   curl http://localhost:9200/_cat/indices?v | grep decision
   ```

3. **Check Filebeat:**
   ```bash
   docker-compose -f docker-compose.observability.yml logs filebeat
   ```

## Next Steps

- [Metrics Reference](METRICS.md) - Complete metrics documentation
- [Traces Reference](TRACES.md) - Distributed tracing details
- [Policy Decisions](POLICY_DECISIONS.md) - Policy decision logging
- [Auto-Enabled Observability](AUTO_ENABLED_OBSERVABILITY.md) - Overview
