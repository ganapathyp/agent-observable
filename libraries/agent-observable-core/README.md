# agent-observable-core

**Enterprise observability library for agent frameworks** - Automatically enables metrics, traces, logs, and policy decisions with zero configuration.

## Overview

`agent-observable-core` is a framework-agnostic observability library that automatically instruments your agent workflows, tools, and LLM calls. Simply drop it in, and you get:

- ✅ **Metrics** - Workflow, agent, tool, and LLM metrics (cost, tokens, latency)
- ✅ **Traces** - Distributed tracing with proper hierarchy (Jaeger)
- ✅ **Policy Decisions** - Automatic logging of policy enforcement decisions
- ✅ **Cost Tracking** - Automatic LLM cost and token usage tracking
- ✅ **Framework Detection** - Auto-detects MS Agent Framework, LangGraph, or custom routing

**No configuration required** - Works out of the box with sensible defaults.

## Quick Start

```python
from agent_observable_core import create_observable_middleware
from agent_observable_core.observability import MetricsCollector

# Create middleware (auto-enables all observability)
middleware = create_observable_middleware(
    service_name="my-agent-service",
    enable_metrics=True,
    enable_tracing=True,
    enable_policy=True,
    enable_guardrails=True,
    enable_cost_tracking=True
)

# Use in your agent framework
# The middleware automatically tracks everything!
```

## Documentation

- **[Auto-Enabled Observability](docs/AUTO_ENABLED_OBSERVABILITY.md)** - What's automatically tracked
- **[Metrics Reference](docs/METRICS.md)** - All metrics automatically enabled
- **[Traces Reference](docs/TRACES.md)** - Distributed tracing details
- **[Policy Decisions](docs/POLICY_DECISIONS.md)** - Policy decision logging
- **[Docker Tools Integration](docs/DOCKER_TOOLS.md)** - Viewing data in Prometheus, Grafana, Jaeger, Kibana

## Features

### Framework-Agnostic

Works with:
- Microsoft Agent Framework
- LangGraph
- OpenAI Custom Routing
- Any agent framework

### Automatic Instrumentation

Just use the middleware - no manual instrumentation needed:
- Workflow runs, success, errors, latency
- Agent invocations, success, errors, latency
- Tool calls, success, errors, latency
- LLM cost and token usage
- Policy violations
- Guardrails blocks

### Standardized Metrics

All metrics use consistent naming:
- `workflow.runs`, `workflow.success`, `workflow.errors`
- `agent.{name}.invocations`, `agent.{name}.success`
- `tool.{name}.calls`, `tool.{name}.success`
- `llm.cost.total`, `llm.cost.agent.{name}`, `llm.cost.model.{model}`
- `llm.tokens.input.total`, `llm.tokens.output.total`

### Distributed Tracing

Automatic OpenTelemetry integration:
- Proper parent-child span hierarchy
- Request ID correlation
- Automatic export to Jaeger

### Cost Tracking

Automatic LLM cost calculation:
- Per-agent costs
- Per-model costs
- Token usage (input, output, total)
- Supports all OpenAI models

## Installation

```bash
pip install agent-observable-core
```

## Example

See `examples/taskpilot/` for a complete working example.

## License

See project root for license information.
