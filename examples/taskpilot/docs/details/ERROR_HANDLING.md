# Error Handling & Exception Hierarchy

**Status**: ✅ Fully Implemented

This document describes the comprehensive error handling system with structured error codes and exception hierarchy.

---

## Exception Hierarchy

All exceptions inherit from `BaseAgentException` and provide structured error handling:

```python
BaseAgentException
├── AgentException
│   ├── AgentExecutionError (AGENT_001)
│   ├── AgentTimeoutError (AGENT_002)
│   └── AgentConfigurationError (AGENT_003)
├── ToolException
│   ├── ToolExecutionError (TOOL_100)
│   ├── ToolTimeoutError (TOOL_101)
│   ├── ToolValidationError (TOOL_102)
│   └── ToolRateLimitError (TOOL_103)
├── ValidationError
│   ├── InputValidationError (VALIDATION_201)
│   └── TaskValidationError (VALIDATION_202)
├── PolicyException
│   ├── PolicyViolationError (POLICY_300)
│   └── GuardrailsBlockedError (POLICY_301)
├── LLMException
│   ├── LLMAPIError (LLM_400)
│   ├── LLMRateLimitError (LLM_401)
│   ├── LLMTimeoutError (LLM_402)
│   └── LLMTokenLimitError (LLM_403)
└── SystemException
    ├── ConfigurationError (SYSTEM_500)
    └── StorageError (SYSTEM_501)
```

**Implementation**: `src/core/exceptions.py`

---

## Error Code Format

Error codes follow the format: `{CATEGORY}{NUMBER}`

| Category | Range | Description |
|----------|-------|-------------|
| AGENT_XXX | 001-099 | Agent-related errors |
| TOOL_XXX | 100-199 | Tool execution errors |
| VALIDATION_XXX | 200-299 | Validation errors |
| POLICY_XXX | 300-399 | Policy/guardrails errors |
| LLM_XXX | 400-499 | LLM API errors |
| SYSTEM_XXX | 500-599 | System/infrastructure errors |

---

## Error Code Reference

### Agent Errors (AGENT_001 - AGENT_099)

#### AGENT_001: AgentExecutionError
- **Description**: Agent execution failed
- **User Message**: "Agent execution failed. Please try again."
- **Severity**: error
- **Details**: Includes `agent_name`, `reason`, and optional context

#### AGENT_002: AgentTimeoutError
- **Description**: Agent execution timed out
- **User Message**: "Request took too long to process. Please try again."
- **Severity**: error
- **Details**: Includes `agent_name`, `timeout_seconds`

#### AGENT_003: AgentConfigurationError
- **Description**: Agent configuration is invalid
- **User Message**: "Configuration error. Please contact support."
- **Severity**: error
- **Details**: Includes `agent_name`, `reason`

---

### Tool Errors (TOOL_100 - TOOL_199)

#### TOOL_100: ToolExecutionError
- **Description**: Tool execution failed
- **User Message**: "Tool execution failed. Please try again."
- **Severity**: error
- **Details**: Includes `tool_name`, `reason`

#### TOOL_101: ToolTimeoutError
- **Description**: Tool execution timed out
- **User Message**: "Tool execution took too long. Please try again."
- **Severity**: error
- **Details**: Includes `tool_name`, `timeout_seconds`

#### TOOL_102: ToolValidationError
- **Description**: Tool call validation failed (OPA denied)
- **User Message**: "Tool call was not allowed: {reason}"
- **Severity**: error
- **Details**: Includes `tool_name`, `reason`, `agent_name`, `request_id`

#### TOOL_103: ToolRateLimitError
- **Description**: Tool rate limit exceeded
- **User Message**: "Too many requests. Please try again later."
- **Severity**: warning
- **Details**: Includes `tool_name`, `max_calls`, `window_seconds`

---

### Validation Errors (VALIDATION_200 - VALIDATION_299)

#### VALIDATION_200: ValidationError
- **Description**: General validation error
- **User Message**: "Validation failed"
- **Severity**: error

#### VALIDATION_201: InputValidationError
- **Description**: Input validation failed
- **User Message**: "Invalid input: {reason}"
- **Severity**: error
- **Details**: Includes `field`, `reason`

#### VALIDATION_202: TaskValidationError
- **Description**: Task validation failed
- **User Message**: "Invalid task: {reason}"
- **Severity**: error
- **Details**: Includes `task_id`, `reason`

---

### Policy/Guardrails Errors (POLICY_300 - POLICY_399)

#### POLICY_300: PolicyViolationError
- **Description**: Policy violation detected (keyword filter, etc.)
- **User Message**: "Request was blocked by policy: {reason}"
- **Severity**: error
- **Details**: Includes `policy_type`, `reason`
- **Common Causes**:
  - Keyword filter detected blocked keywords (e.g., "delete", "drop")
  - OPA policy denied request
  - Custom policy rules violated

#### POLICY_301: GuardrailsBlockedError
- **Description**: NeMo Guardrails blocked the request
- **User Message**: "Request was blocked: {reason}"
- **Severity**: error
- **Details**: Includes `check_type`, `reason`
- **Common Causes**:
  - Prompt injection detected
  - Content moderation violation
  - PII detected in output

---

### LLM Errors (LLM_400 - LLM_499)

#### LLM_400: LLMAPIError
- **Description**: LLM API call failed
- **User Message**: "AI service error. Please try again."
- **Severity**: error
- **Details**: Includes `model`, `reason`

#### LLM_401: LLMRateLimitError
- **Description**: LLM API rate limit exceeded
- **User Message**: "Too many requests. Please try again later."
- **Severity**: warning
- **Details**: Includes `model`, `retry_after`

#### LLM_402: LLMTimeoutError
- **Description**: LLM API call timed out
- **User Message**: "Request took too long. Please try again."
- **Severity**: error
- **Details**: Includes `model`, `timeout_seconds`

#### LLM_403: LLMTokenLimitError
- **Description**: LLM token limit exceeded
- **User Message**: "Request too large. Please reduce input size."
- **Severity**: error
- **Details**: Includes `model`, `max_tokens`, `requested_tokens`

---

### System Errors (SYSTEM_500 - SYSTEM_599)

#### SYSTEM_500: ConfigurationError
- **Description**: System configuration error
- **User Message**: "System configuration error. Please contact support."
- **Severity**: error
- **Details**: Includes `config_key`, `reason`

#### SYSTEM_501: StorageError
- **Description**: Storage operation failed
- **User Message**: "Storage error. Please try again."
- **Severity**: error
- **Details**: Includes `operation`, `reason`

---

## Exception Properties

All exceptions include:

```python
exception.error_code      # Structured error code (e.g., "POLICY_300")
exception.message         # Technical error message
exception.user_message    # User-friendly message
exception.details         # Additional context (dict)
exception.to_dict()       # Serialize to dict for logging
```

---

## Error Code Registry

All error codes are registered in `ERROR_CODE_REGISTRY` for programmatic access:

```python
from taskpilot.core.exceptions import get_error_code_info, get_user_message

# Get error code metadata
info = get_error_code_info("POLICY_300")
# Returns: {"category": "Policy", "description": "...", "user_message": "...", "severity": "error"}

# Get user-friendly message
message = get_user_message("POLICY_300")
# Returns: "Request was blocked by policy"
```

---

## Error Handling Behavior

### 1. Exception Raising

Exceptions are raised with structured information:

```python
from taskpilot.core.exceptions import PolicyViolationError

raise PolicyViolationError(
    policy_type="keyword_filter",
    reason="'delete' keyword not allowed",
    details={"request_id": "req-123", "agent": "PlannerAgent"}
)
```

### 2. Error Tracking

When exceptions occur:

- **Metrics**: Error counters incremented (`agent.{agent_name}.errors`, etc.)
- **Logs**: ERROR/WARNING level with error_code, message, details
- **Traces**: Span marked as error with error_code tag
- **Observability**: Errors visible in Prometheus, Jaeger, Kibana

### 3. User-Facing Messages

User-friendly messages are automatically provided:

```python
try:
    # ... operation ...
except PolicyViolationError as e:
    # e.user_message: "Request was blocked by policy: 'delete' keyword not allowed"
    # e.error_code: "POLICY_300"
    # e.details: {"policy_type": "keyword_filter", "reason": "...", ...}
```

---

## Usage Examples

### Catching Specific Errors

```python
from taskpilot.core.exceptions import (
    PolicyViolationError,
    ToolValidationError,
    LLMAPIError
)

try:
    result = await agent.run(input)
except PolicyViolationError as e:
    logger.warning(f"[{e.error_code}] Policy violation: {e.message}")
    # Handle policy violation
except ToolValidationError as e:
    logger.error(f"[{e.error_code}] Tool validation failed: {e.message}")
    # Handle tool validation error
except LLMAPIError as e:
    logger.error(f"[{e.error_code}] LLM API error: {e.message}")
    # Handle LLM error
```

### Error Serialization

```python
from taskpilot.core.exceptions import AgentExecutionError

error = AgentExecutionError(
    agent_name="PlannerAgent",
    reason="Connection timeout",
    details={"request_id": "req-123"}
)

# Serialize for logging
error_dict = error.to_dict()
# {
#     "error_code": "AGENT_001",
#     "message": "Agent PlannerAgent execution failed: Connection timeout",
#     "user_message": "Agent execution failed. Please try again.",
#     "details": {"agent_name": "PlannerAgent", "reason": "Connection timeout", "request_id": "req-123"}
# }
```

---

## Integration with Observability

### Metrics

Error codes are tracked in metrics:

- `agent.{agent_name}.errors` - Total errors per agent
- `policy.violations.total` - Total policy violations
- `agent.{agent_name}.policy.violations` - Policy violations per agent

### Logs

Error codes appear in JSON logs:

```json
{
  "timestamp": "2024-12-22T10:00:00Z",
  "level": "ERROR",
  "message": "[POLICY_300] Policy violation (keyword_filter): 'delete' keyword not allowed",
  "error_code": "POLICY_300",
  "agent": "PlannerAgent",
  "request_id": "req-abc-123"
}
```

### Traces

Error codes appear as span tags:

- `error=true` - Span marked as error
- `error_code=POLICY_300` - Error code tag
- `error_message=...` - Error message tag

---

## Best Practices

1. **Use Specific Exceptions**: Use the most specific exception type (e.g., `PolicyViolationError` not `BaseAgentException`)
2. **Include Context**: Always provide `details` dict with relevant context (request_id, agent_name, etc.)
3. **User Messages**: User messages are automatically provided, but can be customized
4. **Error Registry**: Use `get_error_code_info()` to get error metadata programmatically
5. **Logging**: Always log with error_code for better observability

---

**Implementation**: `src/core/exceptions.py`  
**Tests**: `tests/test_middleware.py`, `tests/test_integration.py`
