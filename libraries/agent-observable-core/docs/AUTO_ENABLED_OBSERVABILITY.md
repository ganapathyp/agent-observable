# Auto-Enabled Observability

When you use `agent-observable-core`, the following observability features are **automatically enabled** with zero configuration:

## What's Automatically Tracked

### 1. Metrics ✅

**Workflow Metrics:**
- `workflow.runs` - Total workflow executions
- `workflow.success` - Successful workflows
- `workflow.errors` - Failed workflows
- `workflow.latency_ms` - Workflow latency (histogram)

**Agent Metrics:**
- `agent.{name}.invocations` - Agent invocations
- `agent.{name}.success` - Successful agent runs
- `agent.{name}.errors` - Agent errors
- `agent.{name}.latency_ms` - Agent latency (histogram)
- `agent.{name}.guardrails.blocked` - Guardrails blocks
- `agent.{name}.policy.violations` - Policy violations

**Tool Metrics:**
- `tool.{name}.calls` - Tool invocations
- `tool.{name}.success` - Successful tool calls
- `tool.{name}.errors` - Tool errors
- `tool.{name}.latency_ms` - Tool latency (histogram)

**LLM Metrics:**
- `llm.cost.total` - Total LLM cost (USD)
- `llm.cost.agent.{name}` - Cost per agent
- `llm.cost.model.{model}` - Cost per model
- `llm.tokens.input.total` - Total input tokens
- `llm.tokens.output.total` - Total output tokens
- `llm.tokens.total.all` - Total tokens
- `llm.tokens.input.{model}` - Input tokens per model
- `llm.tokens.output.{model}` - Output tokens per model
- `llm.tokens.total.{model}` - Total tokens per model

**Policy Metrics:**
- `policy.violations.total` - Total policy violations

**Retry Metrics:**
- `retry.attempts` - Retry attempts
- `retry.success_after_attempts` - Successful retries
- `retry.exhausted` - Exhausted retries

See [METRICS.md](METRICS.md) for complete reference.

### 2. Traces ✅

**Automatic Span Creation:**
- `{service}.workflow.run` - Workflow execution span
  - `{service}.agent.{name}.run` - Agent execution span
    - `{service}.tool.{name}.call` - Tool call span

**Span Attributes:**
- Request ID correlation
- Agent name, tool name
- Latency, output length
- Error codes, policy decisions

**Export:**
- Automatic export to OpenTelemetry Collector
- Viewable in Jaeger UI

See [TRACES.md](TRACES.md) for complete reference.

### 3. Policy Decisions ✅

**Automatic Logging:**
- Tool call validation decisions
- OPA policy decisions
- Guardrails decisions
- Human review decisions

**Decision Fields:**
- `decision_id` - Unique decision ID
- `timestamp` - Decision timestamp
- `decision_type` - Type of decision (tool_call, opa, guardrails, human_review)
- `result` - Decision result (allow, deny, requires_approval)
- `tool_name` - Tool name (if applicable)
- `agent_id` - Agent identifier
- `context` - Additional context

**Storage:**
- JSONL file: `decision_logs.jsonl`
- Can be shipped to Elasticsearch/Kibana

See [POLICY_DECISIONS.md](POLICY_DECISIONS.md) for complete reference.

### 4. Cost Tracking ✅

**Automatic LLM Cost Calculation:**
- Real-time cost tracking per agent
- Per-model cost breakdown
- Token usage tracking
- Supports all OpenAI models

**Cost Metrics:**
- Total cost: `llm.cost.total`
- Per-agent: `llm.cost.agent.{name}`
- Per-model: `llm.cost.model.{model}`

**Token Metrics:**
- Input tokens: `llm.tokens.input.total`, `llm.tokens.input.{model}`
- Output tokens: `llm.tokens.output.total`, `llm.tokens.output.{model}`
- Total tokens: `llm.tokens.total.all`, `llm.tokens.total.{model}`

## How It Works

### Zero Configuration

Just use the middleware:

```python
from agent_observable_core import create_observable_middleware

middleware = create_observable_middleware(
    service_name="my-service",
    enable_metrics=True,      # Auto-enabled
    enable_tracing=True,      # Auto-enabled
    enable_policy=True,       # Auto-enabled
    enable_guardrails=True,   # Auto-enabled
    enable_cost_tracking=True # Auto-enabled
)
```

### Framework Detection

The library automatically detects your framework:
- Microsoft Agent Framework
- LangGraph
- OpenAI Custom Routing

All metrics use standardized names regardless of framework.

### Automatic Instrumentation

The middleware automatically:
1. Wraps agent calls → tracks metrics, creates spans
2. Wraps tool calls → tracks metrics, creates spans
3. Extracts LLM usage → calculates cost, tracks tokens
4. Validates policies → logs decisions
5. Validates guardrails → logs blocks

**No manual instrumentation needed!**

## Viewing Data

All data is automatically exported to standard observability tools:

- **Metrics** → Prometheus → Grafana
- **Traces** → OpenTelemetry Collector → Jaeger
- **Logs** → Filebeat → Elasticsearch → Kibana
- **Policy Decisions** → `decision_logs.jsonl` → Elasticsearch → Kibana

See [DOCKER_TOOLS.md](DOCKER_TOOLS.md) for complete setup and viewing instructions.

## Next Steps

- [Metrics Reference](METRICS.md) - Complete metrics documentation
- [Traces Reference](TRACES.md) - Distributed tracing details
- [Policy Decisions](POLICY_DECISIONS.md) - Policy decision logging
- [Docker Tools Integration](DOCKER_TOOLS.md) - Viewing data in tools
