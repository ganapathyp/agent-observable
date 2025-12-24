# Using agent-observable-core Library

This document explains how TaskPilot integrates and uses the `agent-observable-core` library to get automatic observability (metrics, traces, logs, policy decisions) with minimal code.

---

## Quick Start

### 1. Install Library

```bash
# Library is installed as a dependency
pip install -e ../../../libraries/agent-observable-core
```

### 2. Initialize Observability

**Location:** `src/core/observable.py`

```python
from agent_observable_core.observable import setup_observability

# Initialize once at application startup
setup_observability(
    service_name="taskpilot",
    enable_metrics=True,
    enable_traces=True,
    enable_policy=True,
    enable_guardrails=True
)
```

### 3. Use Middleware

**Location:** `src/core/middleware.py`

```python
from agent_observable_core.middleware import create_observable_middleware

# Create middleware (handles all observability automatically)
middleware = create_observable_middleware(
    enable_guardrails=True,
    enable_policy=True
)

# Use in workflow
workflow.add_middleware(middleware)
```

That's it! All metrics, traces, logs, and policy decisions are now automatically collected.

---

## What You Get Automatically

### Metrics

Automatically tracked:
- **Workflow metrics**: `workflow_runs`, `workflow_success`, `workflow_errors`
- **Agent metrics**: `agent.{name}.invocations`, `agent.{name}.latency_ms`
- **Tool metrics**: `tool.{name}.executions`, `tool.{name}.errors`
- **LLM metrics**: `llm_cost_total`, `llm_tokens_total`, `llm_cost_model.{model}`
- **Policy metrics**: `policy_violations_total`

**No code needed** - Library middleware handles everything.

### Traces

Automatically created:
- **Workflow traces**: Full workflow execution spans
- **Agent traces**: Individual agent execution spans
- **Tool traces**: Tool execution spans
- **Hierarchy**: Proper parent-child relationships

**No code needed** - Library middleware creates spans automatically.

### Logs

Automatically logged:
- **Structured JSON logs**: All agent interactions
- **Request correlation**: All logs linked by `request_id`
- **Policy decisions**: All decisions logged

**No code needed** - Library middleware logs everything.

### Policy Decisions

Automatically logged:
- **Tool call decisions**: Allow/deny decisions
- **OPA decisions**: Policy evaluation results
- **Guardrails decisions**: NeMo guardrails results

**No code needed** - Library middleware logs all decisions.

---

## Project-Specific Extensions

TaskPilot extends the library middleware with project-specific logic:

**Location:** `src/core/task_hooks.py`

```python
from agent_observable_core.middleware import MiddlewareHooks

class TaskPilotHooks(MiddlewareHooks):
    """Project-specific hooks that extend library middleware."""
    
    async def on_agent_complete(self, context, agent_name, result):
        """Track task lifecycle based on agent type."""
        # Project-specific: Update task status
        if agent_name == "PlannerAgent":
            # Create task in store
            ...
        elif agent_name == "ReviewerAgent":
            # Update task status based on review
            ...
```

**Key Point**: Library handles all observability. Project code only adds business logic.

---

## Configuration

### Basic Configuration

**Location:** `src/core/observable.py`

```python
from agent_observable_core.observable import setup_observability

setup_observability(
    service_name="taskpilot",
    service_version="1.0.0",
    enable_metrics=True,
    enable_traces=True,
    enable_policy=True,
    enable_guardrails=True,
    otlp_endpoint="http://localhost:4317",  # OpenTelemetry Collector
)
```

### Advanced Configuration

See library documentation:
- **[agent-observable-core README](../../../libraries/agent-observable-core/README.md)**
- **[Auto-Enabled Observability](../../../libraries/agent-observable-core/docs/AUTO_ENABLED_OBSERVABILITY.md)**

---

## Viewing Data

### Metrics (Prometheus/Grafana)

**Access:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

**Dashboard:**
- Import: `observability/grafana/golden-signals-dashboard.json`
- Shows: All Golden Signals automatically

### Traces (Jaeger)

**Access:** http://localhost:16686

**Search:**
- Service: `taskpilot`
- View: Full trace hierarchy (workflow → agent → tool)

### Logs (Kibana)

**Access:** http://localhost:5601

**Index Pattern:** `taskpilot-logs-*`

**Filters:**
- `request_id: "req-123"` - Correlate all logs for a request
- `agent_name: "PlannerAgent"` - Filter by agent
- `level: "ERROR"` - Filter errors

### Policy Decisions (Kibana)

**Filter:** `log_type: "policy_decision"`

**View:**
- All tool call decisions
- OPA policy evaluations
- Guardrails decisions

---

## Code Examples

### Example 1: Basic Integration

```python
# main.py
from agent_observable_core.observable import setup_observability
from agent_observable_core.middleware import create_observable_middleware

# Initialize once
setup_observability(service_name="taskpilot")

# Create middleware
middleware = create_observable_middleware()

# Use in workflow
workflow.add_middleware(middleware)

# That's it! All observability is automatic.
```

### Example 2: With Project-Specific Hooks

```python
# src/core/middleware.py
from agent_observable_core.middleware import create_observable_middleware, MiddlewareHooks

class TaskPilotHooks(MiddlewareHooks):
    async def on_agent_complete(self, context, agent_name, result):
        # Project-specific: Track task lifecycle
        if agent_name == "PlannerAgent":
            task_store.create_task(...)

# Create middleware with hooks
middleware = create_observable_middleware(
    hooks=TaskPilotHooks()
)
```

### Example 3: Custom Metrics

```python
# If you need custom metrics beyond what library provides
from agent_observable_core.observable import get_metrics

metrics = get_metrics()
metrics.increment_counter("custom.business.metric", 1.0)
```

---

## What the Library Handles

✅ **Automatic Metrics Collection**
- Workflow metrics
- Agent metrics
- Tool metrics
- LLM cost/token metrics
- Policy violation metrics

✅ **Automatic Tracing**
- Workflow spans
- Agent spans
- Tool spans
- Proper hierarchy

✅ **Automatic Logging**
- Structured JSON logs
- Request correlation
- Error logging

✅ **Automatic Policy Decisions**
- Tool call validation
- OPA policy evaluation
- Guardrails decisions
- Decision logging

---

## What You Need to Code

❌ **Don't write:**
- Metrics collection code
- Trace creation code
- Log formatting code
- Policy decision logging

✅ **Do write:**
- Business logic (agents, tools, workflows)
- Project-specific hooks (if needed)
- Custom metrics (if needed beyond library)

---

## Troubleshooting

### Metrics Not Appearing

1. Check Prometheus is scraping: http://localhost:9090/targets
2. Verify `/metrics` endpoint: http://localhost:8000/metrics
3. Check time range in Grafana

### Traces Not Appearing

1. Check OTEL Collector is running: `docker ps | grep otel-collector`
2. Verify OTLP endpoint: `http://localhost:4317`
3. Check Jaeger: http://localhost:16686

### Logs Not Appearing

1. Check Filebeat is running: `docker ps | grep filebeat`
2. Verify log file exists: `ls -lh logs/taskpilot.log`
3. Check Kibana index pattern: `taskpilot-logs-*`

---

## Related Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - TaskPilot architecture
- **[OBSERVABILITY_TOOLS_WALKTHROUGH.md](OBSERVABILITY_TOOLS_WALKTHROUGH.md)** - Viewing data in tools
- **[Library Documentation](../../../libraries/agent-observable-core/README.md)** - Full library docs
