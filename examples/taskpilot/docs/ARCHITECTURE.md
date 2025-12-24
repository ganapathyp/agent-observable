# TaskPilot Architecture

**TaskPilot** is an example implementation demonstrating how to use the `agent-observable-core` library with the Microsoft Agent Framework.

---

## Overview

TaskPilot is a multi-agent workflow system that demonstrates:
- **Agent Collaboration**: Three specialized agents work together
- **Conditional Branching**: Workflow routes based on approval status
- **Automatic Observability**: Metrics, traces, logs, and policy decisions via library
- **Tool Integration**: Functions execute as part of the workflow
- **Production Guardrails**: NeMo Guardrails + Embedded OPA for safety

---

## High-Level Architecture

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
│         │         │  agent-observable-   │                │
│         │         │  core (Library)      │                │
│         │         │  ┌─────────────────┐ │                │
│         │         │  │ Middleware       │ │                │
│         │         │  │ • Metrics         │ │                │
│         │         │  │ • Traces         │ │                │
│         │         │  │ • Policy         │ │                │
│         │         │  │ • Guardrails     │ │                │
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
│         │         │  • create_task        │                │
│         │         │  • notify_external    │                │
│         │         └──────────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## System Flow

### Complete Workflow Flow

```
User Request
    │
    ▼
┌─────────────────────┐
│ Library Middleware  │  ← Automatic observability
│ (Metrics/Traces)    │     • Request tracking
└──────────┬──────────┘     • Policy decisions
           │
           ▼
┌─────────────────────┐
│ NeMo Guardrails      │  ← Input validation
│ (Input Validation)   │     • Prompt injection detection
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
           │
           └─── REVIEW/REJECTED ────▶ Task stored
                                      (Workflow ends)
```

---

## Component Details

### 1. Agents

#### PlannerAgent (`src/agents/agent_planner.py`)
- **Purpose**: Interprets user requests and creates task proposals
- **Method**: Function calling with structured output
- **Output**: Function call with structured data (title, priority, description)

#### ReviewerAgent (`src/agents/agent_reviewer.py`)
- **Purpose**: Reviews task proposals for safety and compliance
- **Output**: "APPROVE" / "REJECTED" / "REVIEW"
- **Decision Logic**:
  - **APPROVE**: Task is safe, proceeds automatically
  - **REJECTED**: Task is unsafe, rejected by agent
  - **REVIEW**: Task requires human judgment

#### ExecutorAgent (`src/agents/agent_executor.py`)
- **Purpose**: Executes approved tasks using tools
- **Input**: Approved task from ReviewerAgent
- **Output**: Execution confirmation

### 2. Core Components

#### Configuration (`src/core/config.py`)
- **Purpose**: Centralized configuration management
- **Features**: Model ID, API keys, environment file resolution

#### Middleware (`src/core/middleware.py`)
- **Purpose**: Project-specific hooks that extend library middleware
- **Integration**: Uses `agent-observable-core` middleware for observability
- **Project Logic**: Task tracking, agent type detection

#### Workflow (`src/core/workflow.py`)
- **Purpose**: Defines the workflow structure
- **Components**:
  - `build_workflow()`: Constructs the workflow graph
  - `_is_approved()`: Condition function for conditional branching
- **Workflow Structure**:
  - Chain: Planner → Reviewer
  - Conditional Edge: Reviewer → Executor (if APPROVE)
  - Chain: Executor → create_task → notify_external_system

#### Task Store (`src/core/task_store.py`)
- **Purpose**: Persistent task storage
- **Features**: JSON-based storage, task lifecycle management

#### Structured Output (`src/core/structured_output.py`)
- **Purpose**: Parses agent responses (function calls + text)
- **Strategies**: Function calling, JSON parsing, code blocks

### 3. Tools

#### Tools (`src/tools/tools.py`)
- **Agent-compatible tools** (with `@ai_function`):
  - `create_task(title, priority)`: Creates a task (with OPA validation)
  - `notify_external_system(message)`: Notifies external system
- **Guardrails Integration**: All tools validated with embedded OPA

### 4. Library Integration

#### agent-observable-core
- **Automatic Features**:
  - Metrics collection (workflow, agent, tool, LLM cost)
  - Distributed tracing (OpenTelemetry)
  - Policy decision logging
  - Guardrails integration (NeMo, OPA)
- **Usage**: Minimal code - just initialize and use middleware

See [USING_THE_LIBRARY.md](USING_THE_LIBRARY.md) for details.

---

## Guardrails & Safety

### Three Layers of Protection

1. **NeMo Guardrails** (LLM I/O Validation)
   - Input validation: Prompt injection, content moderation
   - Output validation: PII leakage, hallucinations
   - Integrated via library middleware

2. **Embedded OPA** (Tool Call Authorization)
   - Validates tool calls before execution
   - Policy-driven authorization
   - In-process evaluation

3. **Decision Logging** (Audit Trail)
   - All policy decisions logged automatically
   - Structured JSONL format
   - Compliance and debugging

---

## Observability

All observability is handled automatically by `agent-observable-core`:

- **Metrics**: Workflow runs, agent invocations, LLM costs, policy violations
- **Traces**: Distributed tracing with parent-child relationships
- **Logs**: Structured JSON logs with request correlation
- **Policy Decisions**: All decisions logged for audit

See [USING_THE_LIBRARY.md](USING_THE_LIBRARY.md) for integration details.

---

## Related Documentation

- **[USING_THE_LIBRARY.md](USING_THE_LIBRARY.md)** - How to use agent-observable-core
- **[RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md)** - How to run TaskPilot
- **[OBSERVABILITY_TOOLS_WALKTHROUGH.md](OBSERVABILITY_TOOLS_WALKTHROUGH.md)** - Viewing data in Docker tools
- **[details/DESIGN.md](details/DESIGN.md)** - Detailed design document
