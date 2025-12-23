# LLM Production Guide: Metrics, Traces, and Considerations

## Overview

This guide covers LLM-specific production considerations, metrics, and traces that are implemented in TaskPilot.

---

## 1. Golden Signals for LLM Production

### The 5 Critical Metrics

| Signal | Metric | Implementation | Status |
|--------|--------|----------------|--------|
| **Success Rate** | `workflow.success / workflow.runs * 100` | ✅ Implemented | ✅ Working |
| **p95 Latency** | `workflow.latency_ms` histogram p95 | ✅ Implemented | ✅ Working |
| **Cost per Task** | `llm.cost.total / workflow.success` | ✅ Implemented | ✅ Working |
| **User Correctness** | `(user_correct / total_feedback) * 100` | ⚠️ Placeholder | ⚠️ Needs user feedback |
| **Policy Violations** | `(total_violations / workflow.runs) * 100` | ✅ Implemented | ✅ Working |

### Code Implementation

```python
# src/core/observability.py
def get_golden_signals(self) -> Dict[str, Any]:
    """Calculate Golden Signals for LLM production monitoring."""
    # 1. Success Rate
    workflow_runs = self._counters.get("workflow.runs", 0.0)
    workflow_success = self._counters.get("workflow.success", 0.0)
    success_rate = (workflow_success / workflow_runs * 100) if workflow_runs > 0 else 0.0
    
    # 2. p95 Latency
    workflow_latency_stats = self._get_histogram_stats_unlocked("workflow.latency_ms")
    p95_latency = workflow_latency_stats.get("p95", 0.0)
    
    # 3. Cost per Successful Task
    total_cost = self._counters.get("llm.cost.total", 0.0)
    cost_per_successful_task = (total_cost / workflow_success) if workflow_success > 0 else 0.0
    
    # 4. User-Confirmed Correctness
    user_correct = self._counters.get("llm.quality.user_confirmed_correct", 0.0)
    user_incorrect = self._counters.get("llm.quality.user_confirmed_incorrect", 0.0)
    total_feedback = user_correct + user_incorrect
    user_confirmed_correctness = (user_correct / total_feedback * 100) if total_feedback > 0 else None
    
    # 5. Policy Violation Rate
    total_violations = 0.0
    for key, value in self._counters.items():
        if "policy.violations" in key or ".policy.violations" in key:
            total_violations += value
    policy_violation_rate = (total_violations / workflow_runs * 100) if workflow_runs > 0 else 0.0
    
    return {
        "success_rate": round(success_rate, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "cost_per_successful_task_usd": round(cost_per_successful_task, 4),
        "user_confirmed_correctness_percent": round(user_confirmed_correctness, 2) if user_confirmed_correctness is not None else None,
        "policy_violation_rate_percent": round(policy_violation_rate, 2)
    }
```

### Viewing in Grafana

**Dashboard:** `observability/grafana/golden-signals-dashboard.json`

**Shows:**
- Success rate with thresholds (95% healthy, 90% warning)
- p95 latency with thresholds (2s healthy, 5s warning)
- Cost per task with thresholds ($0.10 healthy, $0.50 warning)
- Policy violation rate with thresholds (1% healthy, 2% warning)

---

## 2. Cost Metrics

### Token Usage Tracking

**Implementation:** `src/core/llm_cost_tracker.py`

```python
# Automatic tracking in middleware
from taskpilot.core.llm_cost_tracker import track_llm_metrics

# After agent execution
track_llm_metrics(context.result, agent_name, metrics)

# Records:
# - llm.tokens.input.{model}
# - llm.tokens.output.{model}
# - llm.tokens.total.{model}
# - llm.tokens.input.total
# - llm.tokens.output.total
# - llm.tokens.total.all
```

### Cost Calculation

**Model Pricing:** `src/core/llm_cost_tracker.py`

```python
MODEL_PRICING = {
    "gpt-4o": {
        "input": 2.50,   # $2.50 per 1M tokens
        "output": 10.00  # $10.00 per 1M tokens
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60
    },
    # ... other models
}

def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    input_cost = (input_tokens / 1000.0) * pricing["input"]
    output_cost = (output_tokens / 1000.0) * pricing["output"]
    return round(input_cost + output_cost, 6)
```

### Cost Metrics Tracked

- `llm.cost.total` - Total cost across all LLM calls
- `llm.cost.agent.{agent_name}` - Cost per agent
- `llm.cost.model.{model}` - Cost per model

### Viewing Cost Metrics

**Prometheus:**
```promql
# Total cost
llm_cost_total

# Cost by agent
llm_cost_agent_planneragent
llm_cost_agent_executoragent

# Cost by model
llm_cost_model_gpt_4o_mini
llm_cost_model_gpt_4o
```

**Grafana:**
- Query: `llm_cost_total`
- Dashboard: Golden Signals (shows cost per task)

---

## 3. Performance Metrics

### Latency Tracking

**Implementation:** `src/core/middleware.py`

```python
# Automatic latency tracking
start_time = time.time()
result = await agent.run(...)
latency_ms = (time.time() - start_time) * 1000

# Record as histogram
metrics.record_histogram(f"agent.{agent_name}.latency_ms", latency_ms)
metrics.record_histogram("workflow.latency_ms", workflow_latency)
```

### Latency Metrics

- `agent.{agent_name}.latency_ms` - Agent latency (histogram)
- `workflow.latency_ms` - Workflow latency (histogram)

### Percentiles Available

- p50 (median)
- p95 (95th percentile)
- p99 (99th percentile)

### Viewing in Grafana

**Query:**
```promql
# p95 latency
histogram_quantile(0.95, rate(workflow_latency_ms_bucket[5m]))

# Average latency
rate(workflow_latency_ms_sum[5m]) / rate(workflow_latency_ms_count[5m])
```

---

## 4. Quality Metrics

### User-Confirmed Correctness

**Status:** ⚠️ Placeholder (requires user feedback integration)

**Implementation:**
```python
# To record user feedback
metrics.increment_counter("llm.quality.user_confirmed_correct")
metrics.increment_counter("llm.quality.user_confirmed_incorrect")

# Calculated in Golden Signals
user_confirmed_correctness = (user_correct / total_feedback * 100)
```

**Future Integration:**
- Add user feedback API endpoint
- Record feedback in metrics
- Calculate correctness rate

---

## 5. Safety Metrics

### Policy Violations

**Implementation:** `src/core/middleware.py`

```python
# Track policy violations
if input_text and "delete" in input_text.lower():
    metrics.increment_counter(f"agent.{agent_name}.policy.violations")
    metrics.increment_counter("policy.violations.total")
```

### Guardrails Blocks

**Implementation:** `src/core/middleware.py`

```python
# Track guardrails blocks
if not nemo_result.allowed:
    metrics.increment_counter(f"agent.{agent_name}.guardrails.blocked")
```

### Safety Metrics Tracked

- `agent.{agent_name}.policy.violations` - Violations per agent
- `policy.violations.total` - Total violations
- `agent.{agent_name}.guardrails.blocked` - Input blocked
- `agent.{agent_name}.guardrails.output_blocked` - Output blocked

---

## 6. Traces for LLM Operations

### Span Hierarchy

```
workflow.run
├── PlannerAgent.execute
│   ├── LLM call (implicit)
│   │   ├── Input tokens: 150
│   │   ├── Output tokens: 50
│   │   └── Cost: $0.000375
│   └── create_task (tool call)
├── ReviewerAgent.execute
│   └── LLM call (implicit)
│       ├── Input tokens: 200
│       ├── Output tokens: 30
│       └── Cost: $0.0003
└── ExecutorAgent.execute
    └── notify_external_system (tool call)
```

### Trace Tags

**LLM-specific tags:**
- `agent` - Agent name
- `model` - LLM model used
- `input_tokens` - Input tokens (if available)
- `output_tokens` - Output tokens (if available)
- `cost_usd` - Cost in USD (if available)
- `latency_ms` - Execution latency

### Viewing in Jaeger

**Access:** http://localhost:16686

**Search by:**
- Service: `taskpilot`
- Operation: `PlannerAgent.execute`
- Tags: `agent=PlannerAgent`, `model=gpt-4o-mini`

**Trace View Shows:**
- Span hierarchy
- Timing information
- Token usage (in tags)
- Cost (in tags)

---

## 7. Logs for LLM Operations

### Structured Logging

**Format:** JSON

**LLM-specific fields:**
```json
{
  "timestamp": "2024-12-21T10:00:00.123Z",
  "level": "INFO",
  "message": "[AUDIT] PlannerAgent Input: Create a task",
  "request_id": "req-abc-123",
  "agent": "PlannerAgent",
  "input_length": 25,
  "model": "gpt-4o-mini"
}
```

### Log Categories

1. **Audit Logs**
   - Agent input/output
   - Tool calls
   - Task operations

2. **Error Logs**
   - LLM API errors
   - Token limit errors
   - Cost threshold alerts

3. **Decision Logs**
   - Policy decisions
   - Guardrails blocks
   - Tool authorizations

### Viewing in Kibana

**Access:** http://localhost:5601

**Query Examples:**
```
# Filter by agent
agent: "PlannerAgent"

# Filter by model
model: "gpt-4o-mini"

# Filter by cost threshold
cost_usd: >0.10

# Filter by request ID
request_id: "req-abc-123"
```

---

## 8. Alert Thresholds

### Golden Signals Alerts

**Prometheus Rules:** `observability/prometheus/golden-signals-alerts.yml`

```yaml
groups:
  - name: golden_signals
    rules:
      - alert: HighCostPerTask
        expr: llm_cost_total / workflow_success > 0.50
        annotations:
          summary: "Cost per task exceeds $0.50"
      
      - alert: LowSuccessRate
        expr: (workflow_success / workflow_runs) * 100 < 90
        annotations:
          summary: "Success rate below 90%"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(workflow_latency_ms_bucket[5m])) > 5000
        annotations:
          summary: "p95 latency exceeds 5 seconds"
      
      - alert: HighPolicyViolations
        expr: (policy_violations_total / workflow_runs) * 100 > 2
        annotations:
          summary: "Policy violation rate exceeds 2%"
```

---

## 9. Best Practices

### Metrics to Monitor Daily

1. **Cost per Task** - Budget management
2. **Success Rate** - System reliability
3. **p95 Latency** - User experience
4. **Token Usage** - Cost optimization
5. **Policy Violations** - Safety compliance

### Metrics to Monitor Weekly

1. **Cost Trends** - Budget planning
2. **Latency Trends** - Performance degradation
3. **Error Patterns** - System health
4. **Model Usage** - Cost optimization

### Metrics to Monitor Monthly

1. **Total Cost** - Budget review
2. **Cost Efficiency** - ROI analysis
3. **Quality Trends** - User satisfaction
4. **Safety Trends** - Compliance review

---

## 10. Implementation Checklist

### ✅ Implemented

- [x] Token usage tracking
- [x] Cost calculation
- [x] Cost metrics (total, per agent, per model)
- [x] Latency tracking (histograms)
- [x] Success rate calculation
- [x] Policy violation tracking
- [x] Golden Signals calculation
- [x] OpenTelemetry integration
- [x] JSON logging
- [x] Request ID correlation

### ⚠️ Partial

- [ ] User-confirmed correctness (placeholder ready, needs feedback API)
- [ ] Cost alerts (Prometheus rules defined, needs alertmanager)

### ❌ Not Implemented

- [ ] Cost budgets (daily/monthly limits)
- [ ] Token limit alerts
- [ ] Model performance comparison
- [ ] A/B testing metrics

---

*All implemented metrics and traces are production-ready and automatically collected.*
