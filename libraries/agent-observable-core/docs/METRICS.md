# Metrics Reference

All metrics are **automatically enabled** when using `agent-observable-core`. This document provides a complete reference of all metrics.

## Metric Naming Convention

All metrics follow the pattern: `{category}.{entity}.{metric}`

Examples:
- `workflow.runs` - Workflow category, runs metric
- `agent.PlannerAgent.invocations` - Agent category, PlannerAgent entity, invocations metric
- `llm.cost.total` - LLM category, cost subcategory, total metric

## Workflow Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `workflow.runs` | Counter | Total workflow executions |
| `workflow.success` | Counter | Successful workflow executions |
| `workflow.errors` | Counter | Failed workflow executions |
| `workflow.latency_ms` | Histogram | Workflow execution latency (milliseconds) |

**Example:**
```
workflow.runs: 100
workflow.success: 95
workflow.errors: 5
workflow.latency_ms_p95: 2500.0
```

## Agent Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `agent.{name}.invocations` | Counter | Agent invocations |
| `agent.{name}.success` | Counter | Successful agent runs |
| `agent.{name}.errors` | Counter | Agent errors |
| `agent.{name}.latency_ms` | Histogram | Agent execution latency (milliseconds) |
| `agent.{name}.guardrails.blocked` | Counter | Guardrails blocks (input) |
| `agent.{name}.guardrails.output_blocked` | Counter | Guardrails blocks (output) |
| `agent.{name}.policy.violations` | Counter | Policy violations |

**Example:**
```
agent.PlannerAgent.invocations: 50
agent.PlannerAgent.success: 48
agent.PlannerAgent.errors: 2
agent.PlannerAgent.latency_ms_p95: 1200.0
agent.PlannerAgent.guardrails.blocked: 1
agent.PlannerAgent.policy.violations: 0
```

## Tool Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `tool.{name}.calls` | Counter | Tool invocations |
| `tool.{name}.success` | Counter | Successful tool calls |
| `tool.{name}.errors` | Counter | Tool errors |
| `tool.{name}.latency_ms` | Histogram | Tool execution latency (milliseconds) |

**Example:**
```
tool.create_task.calls: 30
tool.create_task.success: 29
tool.create_task.errors: 1
tool.create_task.latency_ms_p95: 150.0
```

## LLM Cost Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `llm.cost.total` | Counter | Total LLM cost (USD) |
| `llm.cost.agent.{name}` | Counter | Cost per agent (USD) |
| `llm.cost.model.{model}` | Counter | Cost per model (USD) |

**Example:**
```
llm.cost.total: 0.123456
llm.cost.agent.PlannerAgent: 0.082304
llm.cost.agent.ExecutorAgent: 0.041152
llm.cost.model.gpt-4o: 0.082304
llm.cost.model.gpt-4o-mini: 0.041152
```

## LLM Token Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `llm.tokens.input.total` | Counter | Total input tokens |
| `llm.tokens.output.total` | Counter | Total output tokens |
| `llm.tokens.total.all` | Counter | Total tokens (all) |
| `llm.tokens.input.{model}` | Counter | Input tokens per model |
| `llm.tokens.output.{model}` | Counter | Output tokens per model |
| `llm.tokens.total.{model}` | Counter | Total tokens per model |

**Example:**
```
llm.tokens.input.total: 50000
llm.tokens.output.total: 20000
llm.tokens.total.all: 70000
llm.tokens.input.gpt-4o: 30000
llm.tokens.output.gpt-4o: 15000
llm.tokens.total.gpt-4o: 45000
```

## Policy Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `policy.violations.total` | Counter | Total policy violations |

**Example:**
```
policy.violations_total: 2
```

## Retry Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `retry.attempts` | Counter | Total retry attempts |
| `retry.success_after_attempts` | Counter | Successful retries |
| `retry.exhausted` | Counter | Exhausted retries |

**Example:**
```
retry.attempts: 10
retry.success_after_attempts: 8
retry.exhausted: 2
```

## Observability Performance Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `observability.trace_export_latency_ms` | Histogram | Trace export latency |
| `observability.trace_export_queue_size` | Gauge | Trace export queue size |
| `observability.trace_export_failures` | Counter | Trace export failures |
| `observability.otel_collector_health` | Gauge | OTEL collector health (1=healthy, 0=unhealthy) |
| `observability.decision_log_flush_latency_ms` | Histogram | Decision log flush latency |

## Viewing Metrics

### Prometheus

All metrics are exported via `/metrics` endpoint in Prometheus format:

```bash
curl http://localhost:8000/metrics
```

### Grafana

Import the Golden Signals dashboard:
- File: `examples/taskpilot/observability/grafana/golden-signals-dashboard.json`
- Shows: Success rate, latency, cost per task, policy violations

### Query Examples

**Total LLM Cost:**
```promql
llm_cost_total
```

**Cost per Successful Task:**
```promql
llm_cost_total / clamp_min(workflow_success, 1)
```

**Success Rate:**
```promql
(workflow_success / workflow_runs) * 100
```

**P95 Latency:**
```promql
workflow_latency_ms_p95
```

**Policy Violation Rate:**
```promql
(policy_violations_total / workflow_runs) * 100
```

## Metric Export

Metrics are automatically exported:
1. **In-memory** - Available via `MetricsCollector.get_all_metrics()`
2. **Prometheus** - Exposed via `/metrics` endpoint
3. **Grafana** - Queryable via Prometheus data source

See [DOCKER_TOOLS.md](DOCKER_TOOLS.md) for complete setup instructions.
