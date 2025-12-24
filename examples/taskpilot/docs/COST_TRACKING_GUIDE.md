# Cost Tracking Guide

## Overview

The `agent-observable-core` library provides comprehensive LLM cost tracking that automatically:
- Extracts token usage from LLM responses (framework-agnostic)
- Calculates costs based on model pricing
- Tracks metrics by agent, model, and total
- Exports metrics to Prometheus
- Provides cost reporting tools

## Features

✅ **Automatic Tracking**: No manual instrumentation needed  
✅ **Framework-Agnostic**: Works with MS Agent Framework, LangGraph, OpenAI, etc.  
✅ **Accurate Pricing**: Uses current OpenAI pricing (configurable)  
✅ **Multiple Views**: CLI tool, API endpoint, Prometheus metrics  
✅ **Comprehensive Metrics**: Total cost, cost by agent, cost by model, token usage  

## Quick Start

### 1. Cost Tracking is Automatic

Cost tracking happens automatically in middleware. No code changes needed!

```python
# Middleware automatically calls track_llm_metrics()
# after each agent execution
```

### 2. View Costs via CLI

```bash
# View cost report (text format)
python3 scripts/view_costs.py

# View as JSON
python3 scripts/view_costs.py --format json

# View as CSV
python3 scripts/view_costs.py --format csv

# Fetch from API (if server is running)
python3 scripts/view_costs.py --endpoint --port 8000
```

### 3. View Costs via API

```bash
# Text format (default)
curl http://localhost:8000/cost-report

# JSON format
curl http://localhost:8000/cost-report?format=json

# CSV format
curl http://localhost:8000/cost-report?format=csv
```

### 4. View Costs in Prometheus

```promql
# Total cost
llm_cost_total

# Cost by agent
llm_cost_agent_planneragent
llm_cost_agent_executoragent

# Cost by model
llm_cost_model_gpt_4o_mini
llm_cost_model_gpt_4o

# Token usage
llm_tokens_input_total
llm_tokens_output_total
llm_tokens_total_all
```

## Implementation Details

### Library Location

**Core Library**: `libraries/agent-observable-core/src/agent_observable_core/llm_cost_tracker.py`

**Key Functions**:
- `extract_token_usage(response)` - Extracts tokens from any framework response
- `calculate_cost(input_tokens, output_tokens, model)` - Calculates cost in USD
- `track_llm_metrics(response, agent_name, metrics_collector)` - Tracks all metrics

### Integration Points

**Middleware** (`examples/taskpilot/src/core/middleware.py`):
```python
from agent_observable_core.llm_cost_tracker import track_llm_metrics

# After agent execution
track_llm_metrics(context.result, agent_name, metrics, service_name="taskpilot")
```

**Library Middleware** (`libraries/agent-observable-core/src/agent_observable_core/middleware.py`):
```python
# Cost tracking is enabled by default
create_observable_middleware(
    agent_name="MyAgent",
    enable_cost_tracking=True,  # Default: True
    ...
)
```

## Metrics Tracked

### Cost Metrics

| Metric | Description | Example |
|--------|-------------|---------|
| `llm.cost.total` | Total cost across all LLM calls | `0.001234` USD |
| `llm.cost.agent.{agent_name}` | Cost per agent | `llm.cost.agent.PlannerAgent` |
| `llm.cost.model.{model}` | Cost per model | `llm.cost.model.gpt-4o-mini` |

### Token Metrics

| Metric | Description | Example |
|--------|-------------|---------|
| `llm.tokens.input.total` | Total input tokens | `15000` |
| `llm.tokens.output.total` | Total output tokens | `5000` |
| `llm.tokens.total.all` | Total tokens (all) | `20000` |
| `llm.tokens.input.{model}` | Input tokens per model | `llm.tokens.input.gpt-4o-mini` |
| `llm.tokens.output.{model}` | Output tokens per model | `llm.tokens.output.gpt-4o-mini` |
| `llm.tokens.total.{model}` | Total tokens per model | `llm.tokens.total.gpt-4o-mini` |

## Model Pricing

Current pricing (as of 2024, configurable in `llm_cost_tracker.py`):

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| `gpt-4o` | $2.50 | $10.00 |
| `gpt-4o-mini` | $0.15 | $0.60 |
| `gpt-4-turbo` | $10.00 | $30.00 |
| `gpt-4` | $30.00 | $60.00 |
| `gpt-3.5-turbo` | $0.50 | $1.50 |
| `default` | $0.15 | $0.60 |

**Source**: https://openai.com/pricing

## Cost Report Format

### Text Format

```
================================================================================
LLM Cost Report
================================================================================
Generated: 2025-12-24T12:00:00

Total Cost: $0.001234 USD

Cost by Agent:
  PlannerAgent: $0.000800 (64.8%)
  ExecutorAgent: $0.000434 (35.2%)

Cost by Model:
  gpt-4o-mini: $0.001234 (100.0%)

Token Usage:
  Input Tokens: 15,000
  Output Tokens: 5,000
  Total Tokens: 20,000

Tokens by Model:
  gpt-4o-mini:
    Input: 15,000
    Output: 5,000
    Total: 20,000

Average Cost per 1K Tokens: $0.061700
================================================================================
```

### JSON Format

```json
{
  "total_cost_usd": 0.001234,
  "cost_by_agent": {
    "PlannerAgent": 0.0008,
    "ExecutorAgent": 0.000434
  },
  "cost_by_model": {
    "gpt-4o-mini": 0.001234
  },
  "tokens": {
    "input_total": 15000.0,
    "output_total": 5000.0,
    "total_all": 20000.0
  },
  "tokens_by_model": {
    "gpt-4o-mini": {
      "input": 15000.0,
      "output": 5000.0,
      "total": 20000.0
    }
  }
}
```

## Verification

### Verify Cost Tracking is Working

1. **Check metrics endpoint**:
   ```bash
   curl http://localhost:8000/metrics | grep llm_cost_total
   ```

2. **Check Prometheus**:
   - Open: http://localhost:9090
   - Query: `llm_cost_total`
   - Should show cost value (even if 0)

3. **Run a workflow**:
   ```bash
   python3 main.py "Create a test task"
   ```

4. **Check cost report**:
   ```bash
   python3 scripts/view_costs.py
   ```

### Verify Token Counting Accuracy

The library extracts token usage from LLM responses. To verify accuracy:

1. **Check response has usage info**:
   ```python
   from agent_observable_core.llm_cost_tracker import extract_token_usage
   
   usage = extract_token_usage(response)
   if usage:
       print(f"Tokens: {usage['input_tokens']} in, {usage['output_tokens']} out")
   ```

2. **Compare with OpenAI dashboard** (if using OpenAI):
   - Check OpenAI usage dashboard
   - Compare with `llm_tokens_total_all` metric

## Troubleshooting

### No Cost Metrics

**Symptom**: `llm_cost_total` is always 0

**Causes**:
1. No workflows have run yet
2. LLM responses don't include usage info
3. Cost tracking not enabled in middleware

**Fix**:
1. Run a workflow: `python3 main.py "Test task"`
2. Check response format: Verify `response.usage` or `response.agent_run_response.usage` exists
3. Verify middleware calls `track_llm_metrics()`

### Incorrect Costs

**Symptom**: Costs don't match expected values

**Causes**:
1. Model pricing outdated
2. Token extraction failing
3. Wrong model name detected

**Fix**:
1. Update `MODEL_PRICING` in `llm_cost_tracker.py`
2. Check token extraction: `extract_token_usage(response)`
3. Verify model name: Check `usage['model']`

### Cost Report Empty

**Symptom**: Cost report shows all zeros

**Causes**:
1. No workflows run
2. Metrics not being collected
3. Server not running (if using API)

**Fix**:
1. Run workflows to generate costs
2. Check metrics: `curl http://localhost:8000/metrics`
3. Start server: `python3 main.py --server --port 8000`

## Advanced Usage

### Custom Model Pricing

Update pricing in `llm_cost_tracker.py`:

```python
MODEL_PRICING = {
    "my-custom-model": {
        "input": 1.00,   # $1.00 per 1M tokens
        "output": 2.00   # $2.00 per 1M tokens
    },
    # ... existing models
}
```

### Programmatic Access

```python
from taskpilot.core.cost_viewer import create_cost_viewer

viewer = create_cost_viewer()
summary = viewer.get_cost_summary()

print(f"Total cost: ${summary['total_cost_usd']:.6f}")
print(f"Cost by agent: {summary['cost_by_agent']}")
```

### Integration Tests

```python
from agent_observable_core.llm_cost_tracker import track_llm_metrics
from agent_observable_core.observability import MetricsCollector

metrics = MetricsCollector()
# ... simulate LLM response ...
cost = track_llm_metrics(response, "TestAgent", metrics)
assert cost > 0
```

## Related Documentation

- `docs/details/LLM_PRODUCTION_GUIDE.md` - LLM production best practices
- `docs/OBSERVABILITY_TOOLS_WALKTHROUGH.md` - Viewing metrics in tools
- `libraries/agent-observable-core/src/agent_observable_core/llm_cost_tracker.py` - Implementation

## API Reference

### CostViewer

**Location**: `examples/taskpilot/src/core/cost_viewer.py`

**Methods**:
- `get_cost_summary()` - Get cost data as dict
- `get_cost_report(format="text")` - Get formatted report

### CLI Tool

**Location**: `scripts/view_costs.py`

**Usage**:
```bash
python3 scripts/view_costs.py [--format text|json|csv] [--endpoint] [--port 8000]
```

### API Endpoint

**Endpoint**: `GET /cost-report?format=text|json|csv`

**Response**: Cost report in requested format
