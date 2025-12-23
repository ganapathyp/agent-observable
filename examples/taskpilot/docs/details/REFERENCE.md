# TaskPilot Reference Implementation

**Complete reference implementation demonstrating Microsoft Agent Framework capabilities**

---

## Table of Contents

1. [Microsoft Agent Framework Capabilities](#microsoft-agent-framework-capabilities)
2. [Production Guardrails](#production-guardrails)
3. [Workflow & Routing](#workflow--routing)
4. [Role-Based Agents](#role-based-agents)
5. [Cost Optimization](#cost-optimization)
6. [Monitoring & Observability](#monitoring--observability)
7. [Quick Reference](#quick-reference)

---

## Microsoft Agent Framework Capabilities

### 1. Multi-Agent Collaboration

**Three specialized role-based agents**:

| Agent | Role | Responsibility | Output |
|-------|------|----------------|--------|
| **PlannerAgent** | Planner | Interprets user requests, creates task proposals | Structured task proposal (function calling) |
| **ReviewerAgent** | Reviewer | Reviews proposals for safety/compliance | APPROVE / REJECTED / REVIEW |
| **ExecutorAgent** | Executor | Executes approved tasks using tools | Execution confirmation |

**Implementation**: `src/agents/agent_*.py`

### 2. Structured Output (Function Calling)

**Primary Method**: OpenAI Function Calling
- Schema enforced at LLM level
- Guaranteed valid JSON output
- No parsing needed

```python
# PlannerAgent uses function calling
planner = create_planner()
# Automatically uses TaskInfo.get_json_schema()
# strict: True ensures schema compliance
```

**Fallback Strategies** (if function calling unavailable):
1. Direct JSON parsing
2. JSON code blocks
3. Embedded JSON
4. Legacy regex (last resort)

**Implementation**: `src/core/structured_output.py`, `src/agents/agent_planner.py`

### 3. Middleware & Cross-Cutting Concerns

**Middleware Pattern**: Wraps all agent executions

```python
# Middleware provides:
- Audit logging (all inputs/outputs)
- Policy enforcement (keyword blocking)
- Guardrails integration (NeMo + OPA)
- Task tracking (lifecycle management)
```

**Implementation**: `src/core/middleware.py`

### 4. Workflow Orchestration

**Workflow Builder**: Constructs agent execution graph

```python
# Workflow structure:
Planner → Reviewer → (conditional) → Executor → Tools
```

**Features**:
- **Chains**: Sequential execution (Planner → Reviewer)
- **Conditional Edges**: Branch based on conditions (Reviewer → Executor if APPROVE)
- **Function Executors**: Wrap tools for workflow use

**Implementation**: `src/core/workflow.py`

### 5. Tool Integration

**Agent-Compatible Tools** (with `@ai_function`):
- `create_task(title, priority)`: Creates task with OPA validation
- `notify_external_system(message)`: Notifies external system with OPA validation

**Workflow-Compatible Tools** (wrapped for FunctionExecutor):
- `create_task_workflow(message)`: Wrapper for workflow use
- `notify_external_system_workflow(message)`: Wrapper for workflow use

**Implementation**: `src/tools/tools.py`

---

## Production Guardrails

### 1. NeMo Guardrails (LLM I/O Validation)

**Purpose**: Protect against prompt injection, toxic content, PII leakage

**Integration**:
- **Input Validation**: Before agent execution (middleware)
- **Output Validation**: After agent execution (middleware)

**Features**:
- Prompt injection detection
- Content moderation
- PII leakage prevention
- Graceful degradation (works without NeMo installed)

**Implementation**: `src/core/guardrails/nemo_rails.py`

### 2. Embedded OPA (Tool Call Authorization)

**Purpose**: Policy-driven tool call validation

**Features**:
- In-process evaluation (no external server)
- Policy files: `policies/tool_calls.rego`
- Decision logging for audit trail
- Fast evaluation (~0.1ms)

**Policy Rules**:
- Block `delete_task` tool
- Require approval for sensitive high-priority tasks
- Validate parameters (title length, priority values)
- Agent-type-based authorization

**Implementation**: 
- `src/core/guardrails/opa_embedded.py` (evaluator)
- `src/core/guardrails/opa_tool_validator.py` (validator)
- `policies/tool_calls.rego` (policy)

### 3. Decision Logging

**Purpose**: Centralized audit trail for all policy decisions

**Features**:
- Batched async writes (100 decisions or 5 seconds)
- JSONL format (`decision_logs.jsonl`)
- Structured logging (decision type, result, context)
- Singleton pattern (shared across components)

**Decision Types**:
- `GUARDRAILS_INPUT`: NeMo input validation
- `GUARDRAILS_OUTPUT`: NeMo output validation
- `TOOL_CALL`: OPA tool call validation

**Implementation**: 
- `src/core/guardrails/decision_logger.py`
- `src/core/guardrails/decision_log.py`

---

## Workflow & Routing

### Workflow Structure

```
User Request
    │
    ▼
PlannerAgent (creates proposal)
    │
    ▼
ReviewerAgent (reviews)
    │
    ├─ APPROVE ──▶ ExecutorAgent
    │                  │
    │                  ▼
    │              Tool Calls (OPA validated)
    │                  │
    │                  ▼
    │              create_task → notify_external
    │
    └─ REVIEW/REJECTED ──▶ End (task stored)
```

### Conditional Routing

**Microsoft Agent Framework** uses **conditional edges** (not routing tables):

```python
# Conditional edge: Reviewer → Executor (only if APPROVE)
builder.add_edge(
    reviewer,
    executor,
    condition=_is_approved  # Function that returns bool
)
```

**Routing Logic**:
- `_is_approved()`: Checks if response contains "APPROVE"
- Returns `True` → Executor runs
- Returns `False` → Workflow ends, task stored

**Note**: Microsoft Agent Framework doesn't use routing tables. Instead, it uses:
- **Chains**: Sequential execution
- **Conditional Edges**: Branch based on conditions
- **Function Executors**: Wrap functions for workflow use

**Implementation**: `src/core/workflow.py`

---

## Role-Based Agents

### Agent Roles & Responsibilities

| Role | Agent | Instructions | Output Format |
|------|-------|--------------|---------------|
| **Planner** | PlannerAgent | "Interpret the request and propose a task. Use the create_task function." | Function call (structured) |
| **Reviewer** | ReviewerAgent | "Review the proposed task. Reply with exactly one of: APPROVE, REJECTED, or REVIEW." | Text ("APPROVE" / "REJECTED" / "REVIEW") |
| **Executor** | ExecutorAgent | "Execute approved tasks using tools." | Text (execution confirmation) |

### Agent Type Detection

**Automatic Detection**: Middleware detects agent type from name

```python
# Agent types:
- PlannerAgent → AgentType.PLANNER
- ReviewerAgent → AgentType.REVIEWER
- ExecutorAgent → AgentType.EXECUTOR
```

**Usage**: Task tracking, policy enforcement, audit logging

**Implementation**: `src/core/middleware.py`, `src/core/types.py`

---

## Cost Optimization

### Current Implementation

| Strategy | Status | Implementation |
|----------|--------|----------------|
| **Model Selection** | ✅ Implemented | Configurable (default: `gpt-4o-mini`) |
| **Token Counting** | ✅ Implemented | Automatic tracking per agent/model |
| **Cost Tracking** | ✅ Implemented | Automatic cost calculation and metrics |
| **Caching** | ❌ Not implemented | No response caching |
| **Prompt Optimization** | ✅ Manual | Concise instructions |
| **Function Calling** | ✅ Implemented | Reduces retries (structured output) |

### Token & Cost Tracking

**Automatic Tracking**: Token usage and costs tracked automatically in middleware for all agent executions.

**Token Metrics Tracked**:
- Input tokens per model: `llm.tokens.input.{model}`
- Output tokens per model: `llm.tokens.output.{model}`
- Total tokens per model: `llm.tokens.total.{model}`
- Aggregated totals: `llm.tokens.input.total`, `llm.tokens.output.total`, `llm.tokens.total.all`

**Cost Metrics Tracked**:
- Total cost: `llm.cost.total` (USD)
- Cost per agent: `llm.cost.agent.{agent_name}`
- Cost per model: `llm.cost.model.{model}`

**Supported Models** (with pricing):
- `gpt-4o`: $2.50/1M input, $10.00/1M output
- `gpt-4o-mini`: $0.15/1M input, $0.60/1M output
- `gpt-4-turbo`: $10.00/1M input, $30.00/1M output
- `gpt-4`: $30.00/1M input, $60.00/1M output
- `gpt-3.5-turbo`: $0.50/1M input, $1.50/1M output
- Default fallback: Uses `gpt-4o-mini` pricing

**Implementation**: `src/core/llm_cost_tracker.py`
- Extracts token usage from LLM responses (OpenAI-style or agent framework)
- Calculates cost using model-specific pricing
- Tracks metrics via MetricsCollector
- Called automatically in middleware after each agent execution

### Recommendations

**High Priority** (Completed ✅):
1. ✅ **Token Usage Tracking**: Implemented - tracks input/output tokens per agent
2. ✅ **Cost Monitoring**: Implemented - calculates costs per request/workflow
3. ✅ **Model Selection**: Implemented - configurable model selection

**Medium Priority**:
4. **Response Caching**: Cache similar requests (use `functools.lru_cache` or Redis)
5. **Context Window Management**: Truncate long contexts
6. **Batch Processing**: Batch similar requests

**Reference**: See [CAPABILITIES_MATRIX.md](CAPABILITIES_MATRIX.md) for detailed analysis

---

## Monitoring & Observability

### Current Implementation

| Feature | Status | Implementation |
|---------|--------|----------------|
| **Audit Logging** | ✅ Implemented | Middleware logs all I/O |
| **Decision Logging** | ✅ Implemented | Guardrails log all decisions |
| **Structured Logs** | ⚠️ Partial | Python logging (not JSON) |
| **Metrics** | ❌ Not implemented | No Prometheus/metrics |
| **Tracing** | ❌ Not implemented | No request correlation IDs |
| **Health Checks** | ❌ Not implemented | No health endpoints |

### Decision Logs

**Location**: `decision_logs.jsonl`

**Format**: JSON Lines (one decision per line)

**Example**:
```json
{
  "timestamp": "2024-12-20T12:00:00Z",
  "decision_type": "TOOL_CALL",
  "result": "ALLOW",
  "context": {
    "tool_name": "create_task",
    "agent_type": "PlannerAgent",
    "parameters": {"title": "Test", "priority": "high"}
  },
  "policy_result": {
    "allow": true,
    "deny": [],
    "require_approval": false
  }
}
```

**Usage**:
```bash
# View decision logs
tail -f decision_logs.jsonl | jq

# Filter by decision type
cat decision_logs.jsonl | jq 'select(.decision_type == "TOOL_CALL")'
```

### Audit Logs

**Location**: Python logging (stdout/stderr)

**Content**: All agent inputs/outputs, policy violations, errors

**Enhancement Opportunities**:
- JSON structured logging
- Request correlation IDs
- Log aggregation (ELK, Splunk)
- Metrics export (Prometheus)

**Implementation**: `src/core/middleware.py`

---

## Quick Reference

### File Structure

```
taskpilot/
├── src/
│   ├── agents/              # Role-based agents
│   │   ├── agent_planner.py
│   │   ├── agent_reviewer.py
│   │   └── agent_executor.py
│   ├── core/
│   │   ├── middleware.py     # Audit, policy, guardrails
│   │   ├── workflow.py       # Workflow builder
│   │   ├── structured_output.py  # JSON parsing
│   │   └── guardrails/       # Production guardrails
│   │       ├── nemo_rails.py
│   │       ├── opa_embedded.py
│   │       ├── opa_tool_validator.py
│   │       └── decision_logger.py
│   └── tools/
│       └── tools.py          # Agent tools
├── policies/
│   └── tool_calls.rego      # OPA policy
└── docs/
    ├── REFERENCE.md          # This file
    ├── ONBOARDING.md         # Developer guide
    ├── DESIGN.md             # Architecture
    └── TESTING_GUIDE.md      # Testing
```

### Key Commands

```bash
# Setup
./run.sh

# Run workflow
.venv/bin/python main.py

# View tasks
.venv/bin/python list_tasks.py

# Review tasks
.venv/bin/python review_tasks.py

# Run tests
.venv/bin/python -m pytest tests/ -v

# View decision logs
tail -f decision_logs.jsonl | jq
```

### Key Concepts

1. **Multi-Agent Workflow**: Three agents collaborate (Planner → Reviewer → Executor)
2. **Conditional Routing**: Workflow branches based on conditions (not routing tables)
3. **Structured Output**: Function calling ensures valid JSON
4. **Guardrails**: NeMo (I/O) + OPA (tools) + Decision logging
5. **Middleware**: Cross-cutting concerns (audit, policy, guardrails)

---

## Related Documentation

- **[ONBOARDING.md](ONBOARDING.md)** - Complete developer onboarding guide
- **[DESIGN.md](DESIGN.md)** - Detailed architecture and design
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing guide
- **[GUARDRAILS_ARCHITECTURE_EXPLAINED.md](GUARDRAILS_ARCHITECTURE_EXPLAINED.md)** - Guardrails deep dive

---

*This reference implementation demonstrates all major Microsoft Agent Framework capabilities with production-grade guardrails.*
