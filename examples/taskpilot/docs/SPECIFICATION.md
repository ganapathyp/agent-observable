# TaskPilot Specification

## Purpose

This specification document defines the system architecture, APIs, data models, and behavior for TaskPilot. It can be used for:
- **Design validation**
- **Spec-driven code generation**
- **API documentation**
- **Integration contracts**
- **Testing requirements**

---

## 1. System Architecture

### Components

```
TaskPilot
├── Agents
│   ├── PlannerAgent (creates tasks)
│   ├── ReviewerAgent (reviews/approves tasks)
│   └── ExecutorAgent (executes tasks)
├── Workflow
│   └── Conditional branching (approve/review/reject)
├── Tools
│   ├── create_task
│   └── notify_external_system
├── Guardrails
│   ├── NeMo Guardrails (LLM I/O validation)
│   └── Embedded OPA (tool call authorization)
└── Observability
    ├── Metrics (Prometheus)
    ├── Traces (OpenTelemetry/Jaeger)
    └── Logs (JSON/Elasticsearch)
```

### Execution Flow

```
User Input
  ↓
PlannerAgent (creates task)
  ↓
ReviewerAgent (reviews task)
  ↓
  ├─ APPROVE → ExecutorAgent (executes task)
  ├─ REVIEW → Human review (task status: REVIEW)
  └─ REJECT → Task status: REJECTED
```

---

## 2. API Specification

### HTTP Endpoints

**Base URL:** `http://localhost:8000` (when running with `--server`)

#### GET /metrics

**Description:** Prometheus metrics endpoint

**Response:** `text/plain` (Prometheus format)

**Example:**
```
# TYPE workflow_runs counter
workflow_runs 10.0

# TYPE llm_cost_total counter
llm_cost_total 0.823
```

#### GET /health

**Description:** Health check endpoint

**Response:** `application/json`

**Example:**
```json
{
  "status": "healthy",
  "checks": {
    "task_store": {"status": "healthy"},
    "guardrails": {"status": "healthy"}
  },
  "timestamp": 1234567890.123
}
```

#### GET /golden-signals

**Description:** Golden Signals for LLM production monitoring

**Response:** `application/json`

**Example:**
```json
{
  "success_rate": 95.0,
  "p95_latency_ms": 1234.56,
  "cost_per_successful_task_usd": 0.0823,
  "user_confirmed_correctness_percent": null,
  "policy_violation_rate_percent": 0.5,
  "status": {
    "success_rate": "healthy",
    "p95_latency": "healthy",
    "cost_per_task": "healthy",
    "policy_violations": "healthy"
  },
  "metadata": {
    "workflow_runs": 100,
    "workflow_success": 95,
    "total_cost_usd": 7.82,
    "total_violations": 1
  }
}
```

---

## 3. Data Models

### Task Model

```python
@dataclass
class Task:
    id: str
    title: str
    description: str
    priority: str  # "low", "medium", "high"
    status: TaskStatus  # PENDING, APPROVED, REJECTED, REVIEW, EXECUTED
    created_at: datetime
    updated_at: datetime
    reviewer_response: Optional[str] = None
```

### Metrics Model

```python
@dataclass
class MetricsCollector:
    counters: Dict[str, float]
    gauges: Dict[str, float]
    histograms: Dict[str, deque]
    
    def increment_counter(name: str, value: float = 1.0)
    def set_gauge(name: str, value: float)
    def record_histogram(name: str, value: float)
    def get_golden_signals() -> Dict[str, Any]
```

### Trace Model

```python
@dataclass
class Span:
    span_id: str
    name: str
    start_time: float
    end_time: Optional[float]
    request_id: Optional[str]
    parent_span_id: Optional[str]
    tags: Dict[str, str]
    logs: List[Dict[str, Any]]
```

### Decision Model

```python
@dataclass
class PolicyDecision:
    decision_type: DecisionType  # TOOL_CALL, INPUT_VALIDATION, OUTPUT_VALIDATION
    result: DecisionResult  # ALLOW, DENY
    reason: str
    context: Dict[str, Any]
    tool_name: Optional[str]
    agent_id: Optional[str]
    latency_ms: float
    timestamp: float
```

---

## 4. Metrics Specification

### Metric Names

**Format:** `{category}.{name}.{labels}`

#### Workflow Metrics

- `workflow.runs` (counter) - Total workflow executions
- `workflow.success` (counter) - Successful executions
- `workflow.errors` (counter) - Failed executions
- `workflow.latency_ms` (histogram) - Workflow latency

#### Agent Metrics

- `agent.{agent_name}.invocations` (counter) - Invocation count
- `agent.{agent_name}.latency_ms` (histogram) - Latency
- `agent.{agent_name}.success` (counter) - Success count
- `agent.{agent_name}.errors` (counter) - Error count

#### LLM Token & Cost Metrics

**Token Metrics:**
- `llm.tokens.input.total` (counter) - Total input tokens across all models
- `llm.tokens.output.total` (counter) - Total output tokens across all models
- `llm.tokens.total.all` (counter) - Total tokens (input + output)
- `llm.tokens.input.{model}` (counter) - Input tokens per model (e.g., `llm.tokens.input.gpt-4o`)
- `llm.tokens.output.{model}` (counter) - Output tokens per model
- `llm.tokens.total.{model}` (counter) - Total tokens per model

**Cost Metrics:**
- `llm.cost.total` (counter) - Total cost in USD (aggregated)
- `llm.cost.agent.{agent_name}` (counter) - Cost per agent (e.g., `llm.cost.agent.PlannerAgent`)
- `llm.cost.model.{model}` (counter) - Cost per model (e.g., `llm.cost.model.gpt-4o`)

**Implementation:**
- Token usage extracted from LLM responses automatically
- Cost calculated using model-specific pricing (per 1K tokens)
- Tracked in middleware for all agent executions
- Supports multiple models with automatic pricing lookup
- See: `src/core/llm_cost_tracker.py`

#### Task Metrics

- `tasks.created` (counter) - Tasks created
- `tasks.approved` (counter) - Tasks approved
- `tasks.rejected` (counter) - Tasks rejected

#### Policy Metrics

- `agent.{agent_name}.policy.violations` (counter) - Violations per agent
- `policy.violations.total` (counter) - Total violations

---

## 5. Trace Specification

### Span Hierarchy

```
workflow.run (root span)
├── PlannerAgent.execute
│   ├── create_task (tool call span)
│   └── LLM call (implicit)
├── ReviewerAgent.execute
│   └── LLM call (implicit)
└── ExecutorAgent.execute
    └── notify_external_system (tool call span)
```

### Span Tags

**Required:**
- `agent` - Agent name
- `request_id` - Request ID for correlation

**Optional:**
- `agent_type` - Agent type
- `tool_name` - Tool name (if tool call)
- `latency_ms` - Execution latency

---

## 6. Log Specification

### Log Format

**Format:** JSON (one log per line)

**Required Fields:**
- `timestamp` - ISO 8601 timestamp
- `level` - Log level (INFO, ERROR, WARNING)
- `message` - Log message

**Optional Fields:**
- `request_id` - Request ID
- `agent` - Agent name
- `task_id` - Task ID
- `operation` - Operation name

**Example:**
```json
{
  "timestamp": "2024-12-21T10:00:00.123Z",
  "level": "INFO",
  "message": "[AUDIT] PlannerAgent Input: Create a task",
  "request_id": "req-abc-123",
  "agent": "PlannerAgent"
}
```

---

## 7. Guardrails Specification

### NeMo Guardrails

**Purpose:** LLM input/output validation

**Configuration:** `guardrails/config.yml`

**Validation Points:**
- Before agent execution (input)
- After agent execution (output)

**Actions:**
- ALLOW - Continue execution
- DENY - Block and raise error

### Embedded OPA

**Purpose:** Tool call authorization

**Policy:** `policies/tool_calls.rego`

**Validation Points:**
- Before tool execution

**Actions:**
- ALLOW - Execute tool
- DENY - Block tool call

---

## 8. Golden Signals Specification

### Signal Definitions

1. **Success Rate**
   - Formula: `(workflow.success / workflow.runs) * 100`
   - Thresholds: Healthy ≥95%, Warning ≥90%, Critical <90%

2. **p95 Latency**
   - Formula: 95th percentile of `workflow.latency_ms` histogram
   - Thresholds: Healthy <2000ms, Warning <5000ms, Critical ≥5000ms

3. **Cost per Successful Task**
   - Formula: `llm.cost.total / workflow.success`
   - Thresholds: Healthy <$0.10, Warning <$0.50, Critical ≥$0.50

4. **User-Confirmed Correctness**
   - Formula: `(user_correct / total_feedback) * 100`
   - Optional (requires user feedback)

5. **Policy Violation Rate**
   - Formula: `(total_violations / workflow.runs) * 100`
   - Thresholds: Healthy <1%, Warning <2%, Critical ≥2%

---

## 9. Integration Contracts

### Prometheus Integration

**Endpoint:** `/metrics`
**Format:** Prometheus text format
**Scrape Interval:** 15 seconds
**Path:** `/metrics`

### OpenTelemetry Integration

**Protocol:** OTLP gRPC
**Endpoint:** `http://localhost:4317`
**Service Name:** `taskpilot`
**Export:** Automatic on span end

### Elasticsearch Integration

**Format:** JSON logs
**Path:** `logs/taskpilot.log`
**Shipper:** Filebeat
**Index Pattern:** `taskpilot-logs-*`

---

## 10. Error Handling Specification

### Exception Hierarchy

All exceptions inherit from `BaseAgentException` and include:
- **error_code**: Structured error code (e.g., "AGENT_001")
- **user_message**: User-friendly error message
- **details**: Additional context for debugging
- **to_dict()**: Serialization for logging

**Implementation**: `src/core/exceptions.py`

### Error Code Categories

Error codes follow format: `{CATEGORY}{NUMBER}`

#### Agent Errors (AGENT_001 - AGENT_099)
- **AGENT_001**: `AgentExecutionError` - Agent execution failed
- **AGENT_002**: `AgentTimeoutError` - Agent execution timed out
- **AGENT_003**: `AgentConfigurationError` - Agent configuration invalid

#### Tool Errors (TOOL_100 - TOOL_199)
- **TOOL_100**: `ToolExecutionError` - Tool execution failed
- **TOOL_101**: `ToolTimeoutError` - Tool execution timed out
- **TOOL_102**: `ToolValidationError` - Tool call validation failed (OPA)
- **TOOL_103**: `ToolRateLimitError` - Tool rate limit exceeded

#### Validation Errors (VALIDATION_200 - VALIDATION_299)
- **VALIDATION_200**: `ValidationError` - General validation error
- **VALIDATION_201**: `InputValidationError` - Input validation failed
- **VALIDATION_202**: `TaskValidationError` - Task validation failed

#### Policy/Guardrails Errors (POLICY_300 - POLICY_399)
- **POLICY_300**: `PolicyViolationError` - Policy violation detected (keyword filter, etc.)
- **POLICY_301**: `GuardrailsBlockedError` - NeMo Guardrails blocked request

#### LLM Errors (LLM_400 - LLM_499)
- **LLM_400**: `LLMAPIError` - LLM API call failed
- **LLM_401**: `LLMRateLimitError` - LLM API rate limit exceeded
- **LLM_402**: `LLMTimeoutError` - LLM API call timed out
- **LLM_403**: `LLMTokenLimitError` - Token limit exceeded

#### System Errors (SYSTEM_500 - SYSTEM_599)
- **SYSTEM_500**: `ConfigurationError` - System configuration error
- **SYSTEM_501**: `StorageError` - Storage operation failed

### Error Handling Behavior

1. **Agent Errors**
   - Recorded: `agent.{agent_name}.errors` counter
   - Logged: ERROR level with error_code and stack trace
   - Traced: Span marked as error with error_code tag
   - User-facing: User-friendly message returned

2. **Policy Violations**
   - Recorded: `agent.{agent_name}.policy.violations` counter
   - Logged: WARNING level with POLICY_300 error code
   - Action: Execution blocked, PolicyViolationError raised
   - User-facing: "Request was blocked by policy" message

3. **Guardrails Blocks**
   - Recorded: `agent.{agent_name}.guardrails.blocked` counter
   - Logged: ERROR level with POLICY_301 error code
   - Action: Execution blocked, GuardrailsBlockedError raised

4. **Error Code Registry**
   - All error codes registered in `ERROR_CODE_REGISTRY`
   - Provides metadata: category, description, user_message, severity
   - Accessible via `get_error_code_info(error_code)`

### Error Tracking

- **Metrics**: Error counters tracked per agent and globally
- **Logs**: JSON logs include error_code, message, details
- **Traces**: Spans include error_code as tag when errors occur
- **Observability**: Errors visible in Prometheus, Jaeger, Kibana

---

## 11. Testing Specification

### Unit Tests

**Coverage Target:** 90%+

**Test Files:**
- `tests/test_*.py` - Unit tests
- `tests/test_integration.py` - Integration tests

**Test Categories:**
- Metrics collection
- Trace creation
- Log formatting
- Cost calculation
- Golden Signals

### Integration Tests

**Test Endpoints:**
- `/metrics` - Prometheus format
- `/health` - Health checks
- `/golden-signals` - Golden Signals

**Test Observability:**
- Metrics appear in Prometheus
- Traces appear in Jaeger
- Logs appear in Kibana

---

## 12. Deployment Specification

### Container Specification

**Base Image:** `python:3.11-slim`

**Command:**
```bash
python main.py --server --port 8000
```

**Ports:**
- 8000 - HTTP server (metrics, health, golden-signals)

**Environment Variables:**
- `PORT` - Server port (default: 8000)
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry endpoint
- `OTEL_ENABLED` - Enable/disable OpenTelemetry

**Health Check:**
- Endpoint: `/health`
- Interval: 30s
- Timeout: 5s

---

*This specification can be used for code generation, API documentation, and integration contracts.*
