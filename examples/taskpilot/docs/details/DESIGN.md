# TaskPilot Design Document

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [System Flow](#system-flow)
3. [Component Details](#component-details)
4. [Guardrails & Safety](#guardrails--safety)
5. [Testing Guide](#testing-guide)
6. [Example Scenarios](#example-scenarios)
7. [Task Storage and Tracking](#task-storage-and-tracking)

---

## Architecture Overview

TaskPilot is a multi-agent workflow system that demonstrates:
- **Agent Collaboration**: Three specialized agents work together
- **Conditional Branching**: Workflow routes based on approval status
- **Middleware Governance**: Audit and policy enforcement
- **Tool Integration**: Functions execute as part of the workflow
- **Production Guardrails**: NeMo Guardrails + Embedded OPA for safety

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TaskPilot System                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   main.py    │─────▶│  Workflow    │                    │
│  │ (Entry Point)│      │  Builder     │                    │
│  └──────────────┘      └──────────────┘                    │
│         │                    │                              │
│         │                    ▼                              │
│         │         ┌──────────────────────┐                │
│         │         │  Guardrails Layer      │                │
│         │         │  ┌─────────────────┐ │                │
│         │         │  │ NeMo Guardrails  │ │                │
│         │         │  │ (I/O Validation)│ │                │
│         │         │  └─────────────────┘ │                │
│         │         └──────────────────────┘                │
│         │                    │                              │
│         │                    ▼                              │
│         │         ┌──────────────────────┐                │
│         │         │   Agent Pipeline      │                │
│         │         │  ┌─────────────────┐ │                │
│         │         │  │  Middleware      │ │                │
│         │         │  │  (Audit+Policy)  │ │                │
│         │         │  └─────────────────┘ │                │
│         │         └──────────────────────┘                │
│         │                    │                              │
│         │                    ▼                              │
│         │         ┌──────────────────────┐                │
│         │         │   Three Agents        │                │
│         │         │  • Planner            │                │
│         │         │  • Reviewer           │                │
│         │         │  • Executor           │                │
│         │         └──────────────────────┘                │
│         │                    │                              │
│         │                    ▼                              │
│         │         ┌──────────────────────┐                │
│         │         │   Tools               │                │
│         │         │  ┌─────────────────┐ │                │
│         │         │  │ Embedded OPA     │ │                │
│         │         │  │ (Validation)    │ │                │
│         │         │  └─────────────────┘ │                │
│         │         │  • create_task        │                │
│         │         │  • notify_external    │                │
│         │         └──────────────────────┘                │
│         │                    │                              │
│         │                    ▼                              │
│         │         ┌──────────────────────┐                │
│         │         │  Decision Logger     │                │
│         │         │  (Audit Trail)        │                │
│         │         └──────────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## System Flow

### Complete Workflow Flow (with Guardrails)

```
User Request
    │
    ▼
┌─────────────────────┐
│ NeMo Guardrails      │  ← Input validation
│ (Input Validation)   │     • Prompt injection detection
│                     │     • Content moderation
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  PlannerAgent       │  ← Creates task proposal
│  (Function Calling) │     • Structured output
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ NeMo Guardrails     │  ← Output validation
│ (Output Validation) │     • PII leakage detection
│                     │     • Response quality
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Task Stored         │  ← Status: PENDING
│ (TaskStore)         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ ReviewerAgent       │  ← Reviews for safety
│                     │     • Returns: APPROVE/REJECTED/REVIEW
└──────────┬──────────┘
           │
           │ (conditional edge)
           ├─── APPROVE ────┐
           │                 │
           │                 ▼
           │         ┌─────────────────┐
           │         │ ExecutorAgent   │  ← Executes approved task
           │         └────────┬────────┘
           │                  │
           │                  ▼
           │         ┌─────────────────┐
           │         │ Embedded OPA    │  ← Tool call validation
           │         │ (Policy Check)  │     • Authorization
           │         └────────┬────────┘     • Parameter validation
           │                  │
           │                  ▼
           │         ┌─────────────────┐
           │         │ create_task()    │  ← Creates task record
           │         └─────────────────┘
           │                  │
           │                  ▼
           │         ┌─────────────────┐
           │         │ notify_external()│  ← Notifies external system
           │         └─────────────────┘
           │
           └─── REVIEW/REJECTED ────▶ Task stored
                                      (Workflow ends, task visible in task list)
                                      │
                                      ▼
                              ┌─────────────────┐
                              │ Decision Logger │  ← All decisions logged
                              │ (Audit Trail)   │     • Input/output validation
                              └─────────────────┘     • Tool call decisions
```

### Detailed Component Flow (with Guardrails)

```
1. User Input
   "Create a high priority task to prepare the board deck"
   │
   ▼
2. NeMo Guardrails Input Validation
   • Validates input (prompt injection, content moderation)
   • Logs decision (DecisionLogger)
   │
   ▼
3. Middleware (audit_and_policy)
   • Logs input (audit trail)
   • Checks policy (blocks "delete" keyword)
   │
   ▼
4. PlannerAgent
   • Interprets request
   • Uses function calling for structured output
   • Creates task proposal with title and priority
   • Output: Function call with structured data
   │
   ▼
5. NeMo Guardrails Output Validation
   • Validates output (PII leakage, response quality)
   • Logs decision (DecisionLogger)
   │
   ▼
6. Middleware (audit_and_policy)
   • Logs output (audit trail)
   • Stores task (status: PENDING)
   │
   ▼
7. ReviewerAgent
   • Reviews task proposal
   • Checks if safe to execute
   • Output: "APPROVE" / "REJECTED" / "REVIEW"
   • Updates task status
   │
   ▼
8. Conditional Branch (_is_approved)
   • Checks if response contains "APPROVE"
   │
   ├─ YES ──▶ 9. ExecutorAgent
   │          • Executes the approved task
   │          │
   │          ▼
   │          10. Tool Call (create_task)
   │          │
   │          ▼
   │          11. Embedded OPA Validation
   │          • Validates tool call (authorization, parameters)
   │          • Logs decision (DecisionLogger)
   │          │
   │          ▼
   │          12. create_task_workflow()
   │          • Creates task record
   │          │
   │          ▼
   │          13. notify_external_system_workflow()
   │          • Sends notification (also validated with OPA)
   │
   └─ NO ──▶ Task stored as REJECTED/REVIEW
             Workflow ends (task not executed)
             Task visible in task list with status
             All decisions logged for audit
```

---

## Component Details

### 1. Agents

#### PlannerAgent (`src/agents/agent_planner.py`)
- **Purpose**: Interprets user requests and creates task proposals
- **Method**: Function calling with structured output (OpenAI native feature)
- **Instructions**: "Interpret the request and propose a task. Use the create_task function."
- **Input**: User request (e.g., "Create a high priority task to prepare the board deck")
- **Output**: Function call with structured data (title, priority, description)
- **Features**:
  - Uses `TaskInfo.get_json_schema()` for JSON Schema
  - `strict: True` for schema enforcement
  - Guaranteed valid JSON output

#### ReviewerAgent (`src/agents/agent_reviewer.py`)
- **Purpose**: Reviews task proposals for safety and compliance
- **Instructions**: "Review the proposed task. Reply with exactly one of: APPROVE, REJECTED, or REVIEW."
- **Input**: Task proposal from PlannerAgent
- **Output**: "APPROVE" / "REJECTED" / "REVIEW"
- **Decision Logic**:
  - **APPROVE**: Task is safe, proceeds automatically (most cases)
  - **REJECTED**: Task is unsafe, rejected by agent
  - **REVIEW**: Task requires human judgment (<5% of cases)

#### ExecutorAgent (`src/agents/agent_executor.py`)
- **Purpose**: Executes approved tasks using tools
- **Instructions**: "Execute approved tasks using tools."
- **Input**: Approved task from ReviewerAgent
- **Output**: Execution confirmation

### 2. Core Components

#### Configuration (`src/core/config.py`)
- **Purpose**: Centralized configuration management
- **Features**:
  - Model ID configuration (default: `gpt-4o-mini`)
  - API key management (from .env file)
  - Environment file path resolution
  - Validation of required configuration
- **Pattern**: Factory function + global singleton (backward compatibility)

#### Middleware (`src/core/middleware.py`)
- **Purpose**: Cross-cutting concerns (audit, policy, and guardrails)
- **Functions**:
  - `create_audit_and_policy_middleware()`: Creates middleware with guardrails
  - **NeMo Guardrails**: Validates input/output (prompt injection, content moderation)
  - **Policy Enforcement**: Blocks dangerous keywords (e.g., "delete")
  - **Audit Logging**: Logs all agent interactions
  - **Task Tracking**: Tracks task lifecycle based on agent type
- **Integration Points**:
  - Input validation before agent execution
  - Output validation after agent execution
  - Task status updates based on agent responses

#### Workflow (`src/core/workflow.py`)
- **Purpose**: Defines the workflow structure
- **Components**:
  - `build_workflow()`: Constructs the workflow graph
  - `_is_approved()`: Condition function for conditional branching
  - Chains and edges connecting agents and tools
- **Workflow Structure**:
  - Chain: Planner → Reviewer
  - Conditional Edge: Reviewer → Executor (if APPROVE)
  - Chain: Executor → create_task → notify_external_system

#### Task Store (`src/core/task_store.py`)
- **Purpose**: Persistent task storage
- **Features**:
  - JSON-based storage (atomic writes)
  - Backup and recovery
  - Task lifecycle management
  - Status validation (state machine)
- **Pattern**: Factory function + global singleton

#### Structured Output (`src/core/structured_output.py`)
- **Purpose**: Parses agent responses (function calls + text)
- **Strategies** (in order):
  1. Function calling response (primary)
  2. Direct JSON parsing
  3. JSON code blocks
  4. Embedded JSON
  5. Legacy regex (fallback)

#### Validation (`src/core/validation.py`)
- **Purpose**: Input validation utilities
- **Functions**:
  - `validate_priority()`: Validates and normalizes priority
  - `validate_title()`: Validates task title (length, non-empty)
  - `validate_description()`: Validates description
  - `validate_status_transition()`: Enforces valid state transitions

### 3. Tools

#### Tools (`src/tools/tools.py`)
- **Agent-compatible tools** (with `@ai_function`):
  - `create_task(title, priority)`: Creates a task (with OPA validation)
  - `notify_external_system(message)`: Notifies external system (with OPA validation)
- **Workflow-compatible tools** (for FunctionExecutor):
  - `create_task_workflow(message)`: Wrapper for workflow use
  - `notify_external_system_workflow(message)`: Wrapper for workflow use
- **Guardrails Integration**:
  - All tools validated with embedded OPA before execution
  - Policy decisions logged for audit trail

### 4. Guardrails & Safety

#### Guardrails Module (`src/core/guardrails/`)

**Purpose**: Production-ready safety mechanisms for LLM agents

**Components**:

1. **Decision Logging** (`decision_logger.py`)
   - Centralized audit trail
   - Batched async writes (100 decisions or 5 seconds)
   - JSONL format for easy parsing
   - Singleton pattern

2. **Embedded OPA** (`opa_embedded.py`)
   - In-process policy evaluation
   - No external OPA server required
   - Loads policies from `policies/*.rego` files
   - Implements policy logic in Python

3. **Tool Validator** (`opa_tool_validator.py`)
   - Validates tool calls before execution
   - Uses embedded OPA for evaluation
   - Logs all decisions
   - Supports embedded (default) and HTTP modes

4. **NeMo Guardrails** (`nemo_rails.py`)
   - LLM input/output validation
   - Prompt injection detection
   - Content moderation
   - PII leakage prevention
   - Graceful degradation (works without NeMo Guardrails installed)

**Integration**:
- **Middleware**: NeMo Guardrails for I/O validation
- **Tools**: Embedded OPA for tool call validation
- **All Components**: Decision logging for audit trail

**Policy Files**:
- `policies/tool_calls.rego`: OPA policy for tool call validation

---

## Testing Guide

### Prerequisites

1. **Environment Setup**:
   ```bash
   cd taskpilot
   ./run.sh  # This will create venv and install dependencies
   ```

2. **API Key Configuration**:
   ```bash
   # Create .env file in taskpilot/ directory
   echo "OPENAI_API_KEY=sk-your-key-here" > .env
   ```

### Test Structure

```
tests/
├── test_guardrails.py         # Guardrails tests
├── test_opa_embedded.py       # Embedded OPA tests
├── test_middleware.py         # Middleware tests
├── test_middleware_async.py  # Async middleware tests
├── test_task_store.py        # Task store tests
├── test_workflow.py          # Workflow tests
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

# With coverage
.venv/bin/python -m pytest tests/ --cov=src --cov-report=html

# Specific test file
.venv/bin/python -m pytest tests/test_guardrails.py -v
```

---

## Example Scenarios

### Scenario 1: Normal Task Creation

**Input**: "Create a high priority task to prepare the board deck"

**Flow**:
1. NeMo Guardrails validates input ✅
2. PlannerAgent → Creates task proposal
3. NeMo Guardrails validates output ✅
4. Task stored (status: PENDING)
5. ReviewerAgent → Returns "APPROVE"
6. Task status → APPROVED
7. ExecutorAgent → Executes task
8. Embedded OPA validates tool call ✅
9. create_task() → Creates task record
10. notify_external_system() → Sends notification
11. Task status → EXECUTED

**Expected Result**: Task created and executed successfully

---

### Scenario 2: Policy Violation

**Input**: "Delete all user accounts"

**Flow**:
1. NeMo Guardrails validates input ✅
2. Middleware policy check → Contains "delete" keyword
3. **Policy violation** → ValueError raised
4. Workflow stops

**Expected Result**: Error message, no task created

---

### Scenario 3: Task Requires Human Review

**Input**: "Create a task to access sensitive data" (ambiguous case)

**Flow**:
1. NeMo Guardrails validates input ✅
2. PlannerAgent → Creates task proposal
3. Task stored (status: PENDING)
4. ReviewerAgent → Returns "REVIEW"
5. Task status → REVIEW
6. Conditional branch → False (not APPROVE)
7. Workflow ends (executor doesn't run)

**Human Action**:
```bash
# List tasks requiring review
.venv/bin/python review_tasks.py --list

# Approve or reject
.venv/bin/python review_tasks.py --approve task_id
.venv/bin/python review_tasks.py --reject task_id
```

**Expected Result**: 
- Task proposal created and stored
- Task status: REVIEW (awaiting human decision)
- Human can approve or reject via CLI

---

### Scenario 4: Tool Call Denied by OPA

**Input**: "Create a task to delete all files"

**Flow**:
1. PlannerAgent → Creates task proposal
2. ReviewerAgent → Returns "APPROVE" (if not caught)
3. ExecutorAgent → Tries to call tool
4. Embedded OPA validates tool call
5. **Policy violation** → Tool call denied
6. Error raised, tool not executed

**Expected Result**: Tool call blocked, error logged

---

## Task Storage and Tracking

### Human-in-the-Loop Review Workflow

The ReviewerAgent can return three states:
- **APPROVE**: Task is safe and proceeds automatically (most cases)
- **REJECTED**: Task is unsafe and rejected by agent (no human needed)
- **REVIEW**: Task requires human judgment (<5% of cases)

### What Happens When REVIEW is Triggered?

When the ReviewerAgent returns "REVIEW":

1. **Task is Created**: The PlannerAgent creates a task proposal, stored with status `PENDING`.

2. **Review Decision is Recorded**: The ReviewerAgent's response is captured, and the task status is updated to `REVIEW` with the reviewer's response text.

3. **Workflow Ends**: The conditional branch evaluates to `False`, so the ExecutorAgent does not run, and the workflow ends.

4. **Task Awaits Human Review**: The task remains in the task store with:
   - Status: `REVIEW`
   - Reviewer response: The full text explaining why human review is needed
   - Review timestamp: When the agent flagged it for review

5. **Human Reviews Task**: Use the review CLI to approve or reject:
   ```bash
   # Interactive review mode
   .venv/bin/python review_tasks.py
   
   # Or approve/reject directly
   .venv/bin/python review_tasks.py --approve task_20241220_123456_789012
   .venv/bin/python review_tasks.py --reject task_20241220_123456_789012
   ```

6. **After Human Decision**:
   - If approved → Status: `APPROVED` → Task can be executed
   - If rejected → Status: `REJECTED` → Workflow ends

### Task Status Lifecycle

```
User Request
    ↓
PlannerAgent → Task created → Status: PENDING
    ↓
ReviewerAgent → Decision made
    ├─ APPROVE → Status: APPROVED → ExecutorAgent → Status: EXECUTED
    ├─ REJECTED → Status: REJECTED (workflow ends)
    └─ REVIEW → Status: REVIEW (workflow ends, awaits human)
         ↓
    Human Review (via review_tasks.py)
         ├─ Approve → Status: APPROVED → ExecutorAgent → Status: EXECUTED
         └─ Reject → Status: REJECTED (workflow ends)
```

### Review Statistics

Monitor review rate to ensure it stays <5%:

```bash
.venv/bin/python review_tasks.py --stats
```

Output:
```
📊 Review Statistics
========================================
Total tasks: 100
Tasks in REVIEW: 3 (3.0%)
Target: <5% in REVIEW state
```

### Viewing Tasks

Use the `list_tasks.py` CLI tool to view tasks:

```bash
# View all tasks
.venv/bin/python list_tasks.py

# View tasks by status
.venv/bin/python list_tasks.py --status pending
.venv/bin/python list_tasks.py --status approved
.venv/bin/python list_tasks.py --status review
.venv/bin/python list_tasks.py --status rejected
.venv/bin/python list_tasks.py --status executed
```

---

## Guardrails & Safety

### Production Guardrails Architecture

TaskPilot implements **three layers of protection**:

1. **NeMo Guardrails** (LLM I/O Validation)
   - Input validation: Prompt injection, content moderation
   - Output validation: PII leakage, hallucinations
   - Integrated in middleware

2. **Embedded OPA** (Tool Call Authorization)
   - Validates tool calls before execution
   - Policy-driven authorization
   - In-process evaluation (no external server)

3. **Decision Logging** (Audit Trail)
   - All policy decisions logged
   - Structured JSONL format
   - Compliance and debugging

### Guardrails Flow

```
User Input
    │
    ▼
┌─────────────────┐
│ NeMo Guardrails │  ← Input validation
│  Input Rails   │     + Decision logging
└────────┬────────┘
         │
         ▼
    Agent Execution
         │
         ├─► Tool Call
         │   │
         │   ▼
         │ ┌─────────────────┐
         │ │ Embedded OPA    │  ← Tool validation
         │ │                 │     + Decision logging
         │ └────────┬────────┘
         │          │
         │          ▼
         │     Tool Execution
         │
         ▼
┌─────────────────┐
│ NeMo Guardrails │  ← Output validation
│  Output Rails   │     + Decision logging
└────────┬────────┘
         │
         ▼
    All Decisions
         │
         ▼
┌─────────────────┐
│ Decision Logger │  ← Batched, async writes
│                 │     to decision_logs.jsonl
└─────────────────┘
```

### Policy Enforcement

**Current Policies**:
- Block "delete" keyword in input (middleware)
- Validate tool calls (embedded OPA)
- Require approval for high-risk operations (OPA policy)

**Policy Files**:
- `policies/tool_calls.rego`: OPA policy for tool validation

**Decision Logs**:
- Location: `decision_logs.jsonl`
- Format: JSON Lines (one decision per line)
- Content: Full context of every policy decision

---

## Testing Checklist

Use this checklist to verify all components:

- [ ] Package structure is correct
- [ ] All imports work
- [ ] Configuration loads correctly
- [ ] Agents can be created
- [ ] Middleware logs and enforces policy
- [ ] NeMo Guardrails validates input/output
- [ ] Embedded OPA validates tool calls
- [ ] Decision logger writes decisions
- [ ] PlannerAgent creates task proposals
- [ ] ReviewerAgent returns APPROVE/REJECTED/REVIEW
- [ ] ExecutorAgent executes tasks
- [ ] Workflow builds successfully
- [ ] Conditional branching works
- [ ] Tools execute correctly
- [ ] Full workflow runs end-to-end
- [ ] Policy violations are caught
- [ ] REVIEW path works (workflow ends without execution)

---

## Debugging Tips

### Issue: Module not found
```bash
# Reinstall package
cd taskpilot
.venv/bin/pip install -e .
```

### Issue: Configuration not finding .env
```bash
# Check path resolution
.venv/bin/python -c "from taskpilot.core.config import get_config; print(get_config().get_env_file_path())"
```

### Issue: Workflow not executing executor
```bash
# Check conditional function
.venv/bin/python -c "from taskpilot.core.workflow import _is_approved; print(_is_approved('APPROVE'))"
```

### Issue: Middleware not logging
```bash
# Check logging level
.venv/bin/python -c "import logging; logging.basicConfig(level=logging.INFO)"
```

### Issue: Guardrails not working
```bash
# Check decision logs
tail -f decision_logs.jsonl | jq

# Test embedded OPA
.venv/bin/python -c "from taskpilot.core.guardrails import EmbeddedOPA; opa = EmbeddedOPA(); print(opa.evaluate('taskpilot.tool_calls', {'tool_name': 'create_task', 'agent_type': 'PlannerAgent', 'parameters': {'title': 'Test', 'priority': 'high'}}))"
```

---

## Related Documentation

- **[ONBOARDING.md](ONBOARDING.md)** - Developer onboarding guide
- **[GUARDRAILS_ARCHITECTURE_EXPLAINED.md](GUARDRAILS_ARCHITECTURE_EXPLAINED.md)** - Guardrails deep dive
- **[EMBEDDED_OPA_IMPLEMENTATION.md](EMBEDDED_OPA_IMPLEMENTATION.md)** - Embedded OPA details
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing guide
- **[TASK_TRACKING.md](TASK_TRACKING.md)** - Task lifecycle documentation

---

*Last updated: 2024-12-20 (includes guardrails implementation)*
