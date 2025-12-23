# TaskPilot Developer Onboarding Guide

## Welcome! 👋

This guide will help you understand TaskPilot's architecture, codebase structure, and how to contribute effectively.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Project Structure](#project-structure)
4. [Key Concepts](#key-concepts)
5. [Development Workflow](#development-workflow)
6. [Testing](#testing)
7. [Common Tasks](#common-tasks)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites
- Python 3.11+
- `uv` package manager (or `pip`)
- OpenAI API key

### Setup (5 minutes)

```bash
# 1. Navigate to project
cd taskpilot

# 2. Create virtual environment (if not exists)
python3 -m venv .venv

# 3. Install dependencies
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .

# 4. Configure API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 5. Run the application
.venv/bin/python main.py
```

### Verify Installation

```bash
# Test imports
.venv/bin/python -c "from taskpilot.core.guardrails import OPAToolValidator; print('✅ All imports work')"

# Run tests
.venv/bin/python -m pytest tests/ -v
```

---

## Architecture Overview

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TaskPilot System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Request                                                   │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Guardrails Layer (Production Safety)                    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │ │
│  │  │ NeMo         │  │ Embedded OPA │  │ Decision     │  │ │
│  │  │ Guardrails   │  │ (Tool Calls)│  │ Logger       │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Middleware Layer (Audit & Policy)                     │ │
│  │  • Input/Output validation                              │ │
│  │  • Audit logging                                        │ │
│  │  • Policy enforcement                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Agent Layer                                            │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │ Planner  │→ │ Reviewer │→ │ Executor │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └─────────────────────────────────────────────────────────┘ │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Tool Layer                                             │ │
│  │  • create_task (with OPA validation)                   │ │
│  │  • notify_external_system (with OPA validation)         │ │
│  └─────────────────────────────────────────────────────────┘ │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Storage Layer                                          │ │
│  │  • TaskStore (JSON-based, atomic writes)                │ │
│  │  • Decision logs (JSONL format)                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Complete Request Flow

```
1. User Request: "Create a high priority task to prepare board deck"
   │
   ▼
2. NeMo Guardrails Input Validation
   │   • Checks for prompt injection
   │   • Validates content
   │   • Logs decision
   │
   ▼
3. PlannerAgent
   │   • Interprets request
   │   • Uses function calling for structured output
   │   • Creates task proposal
   │
   ▼
4. NeMo Guardrails Output Validation
   │   • Validates agent output
   │   • Logs decision
   │
   ▼
5. Task Stored (status: PENDING)
   │
   ▼
6. ReviewerAgent
   │   • Reviews task proposal
   │   • Returns: APPROVE / REJECTED / REVIEW
   │
   ▼
7. Conditional Branch
   │
   ├─► APPROVE ──► ExecutorAgent
   │                  │
   │                  ▼
   │              Tool Call (create_task)
   │                  │
   │                  ▼
   │              OPA Validation (Embedded)
   │                  │
   │                  ├─► Allowed ──► Tool Executes
   │                  │
   │                  └─► Denied ──► Error Raised
   │
   └─► REVIEW/REJECTED ──► Task Stored, Workflow Ends
```

---

## Project Structure

### Directory Layout

```
taskpilot/
├── src/                          # Source code (package root)
│   ├── __init__.py              # Package metadata
│   ├── agents/                  # Agent definitions
│   │   ├── agent_planner.py    # Planner agent (function calling)
│   │   ├── agent_reviewer.py   # Reviewer agent
│   │   └── agent_executor.py   # Executor agent
│   │
│   ├── core/                    # Core functionality
│   │   ├── config.py           # Configuration management
│   │   ├── middleware.py       # Audit & policy middleware
│   │   ├── workflow.py         # Workflow builder
│   │   ├── task_store.py       # Task persistence
│   │   ├── models.py           # Pydantic models
│   │   ├── structured_output.py  # JSON parsing
│   │   ├── validation.py        # Input validation
│   │   ├── types.py            # Enums & types
│   │   ├── service.py          # Service layer
│   │   │
│   │   └── guardrails/         # Production guardrails (NEW)
│   │       ├── __init__.py     # Public API
│   │       ├── decision_log.py # Decision data structures
│   │       ├── decision_logger.py  # Centralized logging
│   │       ├── opa_embedded.py # Embedded OPA evaluator
│   │       ├── opa_tool_validator.py  # Tool call validation
│   │       └── nemo_rails.py   # NeMo Guardrails wrapper
│   │
│   └── tools/                   # Agent tools
│       └── tools.py            # Tool definitions
│
├── tests/                       # Test suite
│   ├── test_guardrails.py      # Guardrails tests
│   ├── test_opa_embedded.py    # Embedded OPA tests
│   ├── test_middleware.py      # Middleware tests
│   ├── test_task_store.py      # Task store tests
│   ├── test_workflow.py        # Workflow tests
│   └── ...
│
├── policies/                    # OPA policy files
│   └── tool_calls.rego         # Tool call validation policy
│
├── docs/                        # Documentation
│   ├── ONBOARDING.md           # This file
│   ├── DESIGN.md               # Architecture & design
│   ├── GUARDRAILS_ARCHITECTURE_EXPLAINED.md  # Guardrails deep dive
│   └── ...
│
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Package configuration
└── .env                         # Environment variables (not in git)
```

### Key Files Explained

#### Entry Point
- **`main.py`**: Application entry point, creates agents, builds workflow, runs

#### Agents (`src/agents/`)
- **`agent_planner.py`**: Creates task proposals using function calling
- **`agent_reviewer.py`**: Reviews tasks for safety (APPROVE/REJECTED/REVIEW)
- **`agent_executor.py`**: Executes approved tasks

#### Core (`src/core/`)
- **`config.py`**: Configuration management (model, API keys)
- **`middleware.py`**: Audit logging + policy enforcement + guardrails integration
- **`workflow.py`**: Workflow builder (chains, edges, conditions)
- **`task_store.py`**: Task persistence (JSON, atomic writes, backup/recovery)
- **`models.py`**: Pydantic models for validation
- **`structured_output.py`**: Parses agent responses (function calls + text)
- **`validation.py`**: Input validation utilities
- **`types.py`**: Enums (TaskStatus, TaskPriority, AgentType)
- **`service.py`**: Service layer (business logic)

#### Guardrails (`src/core/guardrails/`) - **NEW**
- **`decision_log.py`**: Decision data structures (enums, dataclasses)
- **`decision_logger.py`**: Centralized decision logging (batched, async)
- **`opa_embedded.py`**: Embedded OPA policy evaluator (in-process)
- **`opa_tool_validator.py`**: Tool call validator (uses embedded OPA)
- **`nemo_rails.py`**: NeMo Guardrails wrapper (LLM I/O validation)

#### Tools (`src/tools/`)
- **`tools.py`**: Tool definitions with OPA validation

---

## Key Concepts

### 1. Multi-Agent Workflow

**Three specialized agents** work together:
- **Planner**: Interprets requests, creates task proposals
- **Reviewer**: Reviews for safety, returns APPROVE/REJECTED/REVIEW
- **Executor**: Executes approved tasks using tools

**Workflow pattern**: Chain → Conditional Branch → Chain

### 2. Structured Output

**Function Calling** (primary method):
- PlannerAgent uses OpenAI function calling
- Guaranteed valid JSON output
- Schema enforced at LLM level

**Fallback parsing** (if function calling unavailable):
- Direct JSON parsing
- JSON code blocks
- Embedded JSON
- Legacy regex (last resort)

### 3. Guardrails (Production Safety)

**Three layers of protection**:

1. **NeMo Guardrails** (LLM I/O):
   - Validates user input (prompt injection, toxic content)
   - Validates LLM output (PII leakage, hallucinations)
   - Integrated in middleware

2. **Embedded OPA** (Tool Calls):
   - Validates tool calls before execution
   - Policy-driven authorization
   - In-process evaluation (no external server)

3. **Decision Logging**:
   - All policy decisions logged
   - Structured JSONL format
   - Audit trail for compliance

### 4. Task Lifecycle

```
PENDING → APPROVED → EXECUTED
    │         │
    │         └─► FAILED (on error)
    │
    ├─► REJECTED (by reviewer)
    │
    └─► REVIEW (requires human approval)
         │
         ├─► APPROVED (by human) → EXECUTED
         └─► REJECTED (by human)
```

### 5. Dependency Injection

**Pattern**: Factory functions + optional injection

```python
# Factory function (preferred)
task_store = create_task_store(storage_path=Path("/custom/path"))

# Global singleton (backward compatibility)
task_store = get_task_store()
```

**Why?**
- Testability: Easy to inject mocks
- Flexibility: Multiple instances with different configs
- Thread-safety: Isolated instances

### 6. Validation

**Three levels**:
1. **Pydantic models**: Type validation, field constraints
2. **Custom validators**: Business logic (priority, status transitions)
3. **Guardrails**: Production safety (content, authorization)

---

## Development Workflow

### Making Changes

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**:
   - Follow existing code patterns
   - Add type hints
   - Add docstrings
   - Update tests

3. **Run tests**:
   ```bash
   .venv/bin/python -m pytest tests/ -v
   ```

4. **Check coverage**:
   ```bash
   .venv/bin/python -m pytest tests/ --cov=src --cov-report=term-missing
   ```

5. **Fix linting**:
   ```bash
   # Check for issues
   .venv/bin/python -m py_compile src/**/*.py
   ```

6. **Update documentation**:
   - Update relevant docs in `docs/`
   - Add examples if needed

### Code Style

- **Type hints**: Use everywhere
- **Docstrings**: Google style
- **Imports**: Group by standard library, third-party, local
- **Error handling**: Specific exceptions, log with context
- **Testing**: Aim for >90% coverage on functional code

### Adding New Features

1. **New Agent**:
   - Create in `src/agents/agent_*.py`
   - Export from `src/agents/__init__.py`
   - Add to workflow in `src/core/workflow.py`

2. **New Tool**:
   - Add to `src/tools/tools.py`
   - Add OPA validation
   - Add tests in `tests/test_tools.py`

3. **New Guardrail**:
   - Add to `src/core/guardrails/`
   - Integrate in middleware or tools
   - Add decision logging
   - Add tests

4. **New Policy**:
   - Add `.rego` file to `policies/`
   - Update `opa_embedded.py` evaluator
   - Add tests

---

## Testing

### Test Structure

```
tests/
├── test_guardrails.py         # Guardrails tests
├── test_opa_embedded.py       # Embedded OPA tests
├── test_middleware.py         # Middleware tests
├── test_middleware_async.py  # Async middleware tests
├── test_task_store.py        # Task store tests
├── test_workflow.py           # Workflow tests
├── test_tools.py             # Tool tests
├── test_structured_output.py # Parsing tests
├── test_function_calling.py  # Function calling tests
├── test_config.py            # Config tests
└── test_integration.py       # End-to-end tests
```

### Running Tests

```bash
# All tests
.venv/bin/python -m pytest tests/ -v

# Specific test file
.venv/bin/python -m pytest tests/test_guardrails.py -v

# Specific test
.venv/bin/python -m pytest tests/test_guardrails.py::TestPolicyDecision -v

# With coverage
.venv/bin/python -m pytest tests/ --cov=src --cov-report=html

# View coverage
open htmlcov/index.html
```

### Writing Tests

**Example**:
```python
import pytest
from taskpilot.core.guardrails import OPAToolValidator

@pytest.mark.asyncio
async def test_tool_validation():
    validator = OPAToolValidator(use_embedded=True)
    allowed, reason, requires_approval = await validator.validate_tool_call(
        tool_name="create_task",
        parameters={"title": "Test", "priority": "high"},
        agent_type="PlannerAgent"
    )
    assert allowed is True
```

---

## Common Tasks

### Adding a New Tool

1. **Define tool** in `src/tools/tools.py`:
   ```python
   @ai_function
   def my_new_tool(param: str) -> str:
       """Tool description."""
       # Add OPA validation
       import asyncio
       validator = OPAToolValidator(use_embedded=True)
       loop = asyncio.get_event_loop()
       allowed, reason, req_approval = loop.run_until_complete(
           validator.validate_tool_call("my_new_tool", {"param": param}, "PlannerAgent")
       )
       if not allowed:
           raise ValueError(f"Tool call denied: {reason}")
       
       # Tool logic
       return f"Result: {param}"
   ```

2. **Add workflow wrapper** (if needed):
   ```python
   def my_new_tool_workflow(message: Any) -> str:
       """Workflow-compatible wrapper."""
       # Extract parameters from message
       # Call tool
       return result
   ```

3. **Add OPA policy** in `policies/tool_calls.rego`:
   ```rego
   allow if {
       input.tool_name == "my_new_tool"
       input.agent_type == "PlannerAgent"
   }
   ```

4. **Update embedded evaluator** in `src/core/guardrails/opa_embedded.py`:
   ```python
   if tool_name == "my_new_tool" and agent_type == "PlannerAgent":
       result["allow"] = True
   ```

5. **Add tests** in `tests/test_tools.py`

### Adding a New Policy Rule

1. **Update Rego policy** in `policies/tool_calls.rego`:
   ```rego
   deny[msg] if {
       input.tool_name == "dangerous_tool"
       msg := "Dangerous tool not allowed"
   }
   ```

2. **Update embedded evaluator** in `src/core/guardrails/opa_embedded.py`:
   ```python
   if tool_name == "dangerous_tool":
       result["deny"].append("Dangerous tool not allowed")
   ```

3. **Add tests** in `tests/test_opa_embedded.py`

### Debugging

**Enable debug logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check decision logs**:
```bash
tail -f decision_logs.jsonl | jq
```

**Test policy evaluation**:
```python
from taskpilot.core.guardrails import EmbeddedOPA
opa = EmbeddedOPA()
result = opa.evaluate("taskpilot.tool_calls", {
    "tool_name": "create_task",
    "agent_type": "PlannerAgent",
    "parameters": {"title": "Test", "priority": "high"}
})
print(result)
```

---

## Troubleshooting

### Import Errors

**Issue**: `ModuleNotFoundError: No module named 'taskpilot'`

**Solution**:
```bash
# Reinstall package
.venv/bin/pip install -e .
```

### OPA Validation Not Working

**Issue**: Tool calls always allowed

**Check**:
1. Is embedded OPA enabled? `OPAToolValidator(use_embedded=True)`
2. Check policy evaluator logic in `opa_embedded.py`
3. Check decision logs: `tail decision_logs.jsonl`

### NeMo Guardrails Not Working

**Issue**: No input/output validation

**Check**:
1. Is NeMo Guardrails installed? `pip install nemoguardrails`
2. Check middleware integration in `middleware.py`
3. Check decision logs for guardrails decisions

### Tests Failing

**Issue**: Tests fail with import errors

**Solution**:
```bash
# Ensure package is installed
.venv/bin/pip install -e .

# Run from project root
cd taskpilot
.venv/bin/python -m pytest tests/ -v
```

---

## Architecture Deep Dives

For detailed explanations, see:

- **`docs/details/DESIGN.md`**: Complete architecture and design
- **`docs/details/GUARDRAILS_ARCHITECTURE_EXPLAINED.md`**: Guardrails deep dive
- **`docs/details/EMBEDDED_OPA_IMPLEMENTATION.md`**: Embedded OPA details
- **`docs/details/STRUCTURED_OUTPUT.md`**: JSON parsing strategies

---

## Key Design Decisions

### Why Embedded OPA?
- **Lower latency**: No network calls (~0.1ms vs ~2-5ms)
- **Simpler deployment**: Single process
- **Better reliability**: No external service dependency

### Why NeMo Guardrails?
- **Industry standard**: NVIDIA's production-ready solution
- **Comprehensive**: Handles prompt injection, content moderation, PII
- **Graceful degradation**: Works even if not installed

### Why Decision Logging?
- **Audit trail**: Compliance requirement
- **Debugging**: Trace why decisions were made
- **Analytics**: Understand policy effectiveness

### Why Function Calling?
- **Guaranteed structure**: LLM must return valid JSON
- **Schema enforcement**: Validated at LLM level
- **No parsing needed**: Direct extraction

---

## Next Steps

1. **Read**: `docs/details/DESIGN.md` for complete architecture
2. **Explore**: Run the application and observe the flow
3. **Experiment**: Modify policies, add tools, test scenarios
4. **Contribute**: Fix bugs, add features, improve docs

---

## Getting Help

- **Documentation**: Check `docs/` directory (see [README.md](README.md) for index)
- **Code examples**: See `tests/` for usage patterns
- **Architecture**: See [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md) and [details/GUARDRAILS_ARCHITECTURE_EXPLAINED.md](details/GUARDRAILS_ARCHITECTURE_EXPLAINED.md)

---

*Welcome to TaskPilot! Happy coding! 🚀*
