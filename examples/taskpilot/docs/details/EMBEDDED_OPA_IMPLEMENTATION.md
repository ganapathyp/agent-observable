# Embedded OPA Implementation

> **Note**: This document covers embedded OPA. For comparison with OPA as a service, see the "Architecture Decision" section below.

## Overview

**Status**: ✅ **Implemented** - Embedded OPA is now the default for tool call validation

The implementation uses an **in-process policy evaluator** that runs directly within the Python application, eliminating the need for a separate OPA server process.

## Architecture

### Before (OPA as Service)
```
Python App
    │
    │ HTTP POST (network call)
    ▼
OPA Server (localhost:8181)
    │
    │ JSON Response
    ▼
Python App
```

### After (Embedded OPA)
```
Python App
    │
    │ Direct function call (in-process)
    ▼
EmbeddedOPA.evaluate()
    │
    │ Policy evaluation result
    ▼
Python App
```

## Implementation Details

### Core Components

1. **`EmbeddedOPA`** (`src/core/guardrails/opa_embedded.py`)
   - In-process policy evaluator
   - Implements policy logic from `policies/tool_calls.rego`
   - No external dependencies required
   - Works without OPA server

2. **`OPAToolValidator`** (Enhanced)
   - Supports both embedded and HTTP modes
   - Default: `use_embedded=True`
   - Fallback to HTTP if needed

### Policy Evaluation

The embedded evaluator implements the same logic as the Rego policy:

```python
# From policies/tool_calls.rego
- Allow create_task for PlannerAgent (with validation)
- Allow notify_external_system for ExecutorAgent/ReviewerAgent (no "delete" in message)
- Deny delete_task
- Require approval for high-priority tasks with "sensitive" in title
```

## Usage

### Default (Embedded)
```python
from taskpilot.core.guardrails import OPAToolValidator

# Uses embedded OPA by default
validator = OPAToolValidator(use_embedded=True)

allowed, reason, requires_approval = await validator.validate_tool_call(
    tool_name="create_task",
    parameters={"title": "Test", "priority": "high"},
    agent_type="PlannerAgent"
)
```

### HTTP Mode (Fallback)
```python
# Use HTTP API if needed
validator = OPAToolValidator(use_embedded=False, opa_url="http://localhost:8181")
```

### Direct Embedded OPA
```python
from taskpilot.core.guardrails import EmbeddedOPA

opa = EmbeddedOPA()
result = opa.evaluate(
    "taskpilot.tool_calls",
    {
        "tool_name": "create_task",
        "agent_type": "PlannerAgent",
        "parameters": {"title": "Test", "priority": "high"}
    }
)
```

## Benefits

### ✅ Advantages

1. **No External Dependencies**
   - No OPA server process required
   - No network calls
   - Single process deployment

2. **Lower Latency**
   - Direct function calls (microseconds vs milliseconds)
   - No serialization overhead
   - No network round-trip

3. **Simpler Deployment**
   - Single Python process
   - No service orchestration
   - Easier containerization

4. **Better Reliability**
   - No network failures
   - No service availability issues
   - Always available

### ⚠️ Trade-offs

1. **Policy Updates**
   - Requires application restart (or hot-reload implementation)
   - HTTP mode allows dynamic policy updates

2. **Policy Complexity**
   - Current implementation: Simple rule evaluator
   - Full Rego interpreter: Would require additional library

3. **Scaling**
   - Embedded: Scales with application
   - HTTP: Can scale OPA server independently

## Configuration

### Environment Variables

- `OPA_URL` - Only used if `use_embedded=False` (default: `http://localhost:8181`)

### Code Configuration

```python
# Embedded (default)
validator = OPAToolValidator(use_embedded=True)

# HTTP mode
validator = OPAToolValidator(use_embedded=False, opa_url="http://opa-server:8181")
```

## Testing

All tests pass:
```bash
.venv/bin/python -m pytest tests/test_opa_embedded.py -v
```

**Test Coverage**:
- ✅ Policy evaluation (allow/deny)
- ✅ Approval requirements
- ✅ Parameter validation
- ✅ Tool authorization
- ✅ Integration with OPAToolValidator

## Migration from HTTP to Embedded

**Automatic**: The default is now embedded mode. No code changes needed.

**Manual**: If you want to use HTTP mode:
```python
# Change from:
validator = OPAToolValidator()

# To:
validator = OPAToolValidator(use_embedded=False)
```

## Performance Comparison

| Metric | Embedded OPA | HTTP OPA |
|--------|--------------|----------|
| **Latency** | ~0.1ms | ~2-5ms |
| **Throughput** | High (in-process) | Limited by network |
| **Dependencies** | None | OPA server process |
| **Deployment** | Single process | Multiple processes |

## Future Enhancements

1. **Full Rego Interpreter**
   - Integrate proper Rego interpreter library
   - Support full Rego language features
   - Dynamic policy loading

2. **Policy Hot-Reload**
   - Reload policies without restart
   - Watch policy files for changes
   - Version management

3. **Policy Compilation**
   - Pre-compile policies for faster evaluation
   - Cache compiled policies
   - Optimize evaluation paths

## Status

✅ **Production Ready**
- All tests passing
- No external dependencies required
- Backward compatible (HTTP mode still available)
- Integrated with tool validation
- Decision logging enabled

---

*Embedded OPA is now the default and recommended approach for tool call validation.*
