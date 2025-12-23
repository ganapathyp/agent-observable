# Session Bootstrap – `agent-observable` Monorepo

Use this text (or a shortened version) as the **first message** in a new AI session so it can quickly reconstruct context.

---

## Project Overview

- **Root project**: `agent-observable` (monorepo)
- **Architecture**: Micro-libraries + example client
  - `libraries/agent-observable-core/` – observability (metrics, traces, logs)
  - `libraries/agent-observable-policy/` – policy decisions & OPA
  - `libraries/agent-observable-guardrails/` – guardrails (NeMo, validation)
  - `libraries/agent-observable-prompts/` – prompt management
  - `examples/taskpilot/` – example/client app using the libraries
- **Frameworks**: MS Agent Framework + framework-agnostic adapters (see `FRAMEWORK_AGNOSTIC_DESIGN.md`)

---

## Current Decisions (as of v0.01)

- **Design**: Micro-library approach, NOT a single giant framework.
- **Repo model**: **Monorepo** – one git repo containing libraries + `taskpilot` example.
- **Rate limiting**: Handled by **cloud infrastructure** (Azure APIM / AWS API Gateway) – **no custom in-app rate limiter**.
- **Application features to implement**:
  - Tool execution timeouts
  - Retry logic with exponential backoff (incl. API 429 handling)
  - Token/cost tracking verification
  - Response caching
  - Context window management
  - API rate limit handling (response-level)
  - Exception hierarchy & error codes

---

## Key Documents (read these first)

All paths are under `docs/`:

- `REFACTORING_PLAN.md`
  - Full multi-phase refactoring + feature roadmap.
  - Now explicitly notes: micro-libraries + `agent-observable` monorepo + MS Agent Framework.

- `MUST_HAVE_FEATURES.md`
  - Prioritized feature/capability list.
  - Clarifies that **rate limiting is infra-level**; app-level features are timeouts, retries, cost tracking, caching, etc.

- `IMPLEMENTATION_TRACKER.md`
  - **Source of truth** for the **2-week Phase 0 sprint**.
  - Contains a task matrix with columns: Task / Status / Tests / Notes.
  - Phase 0 goal: Foundation (interfaces, DI, paths) + critical features (timeouts, retries).

- `ENTERPRISE_LIBRARY_ASSESSMENT.md`
  - Enterprise-readiness critique of the design.
  - Highlights versioning, stability, and adoption concerns.

- `FRAMEWORK_AGNOSTIC_DESIGN.md`
  - Defines interfaces and adapters to work with MS Agent Framework, LangGraph, or custom orchestrators.

- `UNIFIED_FRAMEWORK_PLAN.md`
  - Original “big framework” vision; now used as background, not the primary implementation path.

- `SETUP_MONOREPO.md`
  - Step-by-step instructions to create the `agent-observable` monorepo and move `taskpilot` under `examples/`.

---

## Implementation Focus (Next Steps)

We are executing **Phase 0** from `IMPLEMENTATION_TRACKER.md` as a **2-week sprint**:

1. **Week 1 – Foundation**
   - Create abstraction interfaces (`AgentExecutionContext`, `AgentInterface`, `MiddlewareInterface`, `WorkflowInterface`).
   - Introduce dependency injection for config (Metrics, DecisionLogger, OTEL).
   - Remove hard-coded paths (use config-only).

2. **Week 2 – Critical Features**
   - Implement **Tool Execution Timeouts**.
   - Implement **Retry Logic with Exponential Backoff**.

Each task must:
- Have unit tests (where applicable).
- Have integration tests (where applicable).
- Keep all existing tests passing (no regressions).

---

## How to Use This in a New Session

When starting a new chat/session:

1. **Paste this file** (or a shorter version) into the first message.
2. Tell the assistant:
   - The project root (e.g., `/path/to/agent-observable`).
   - That the main planning/tracking docs are:
     - `docs/IMPLEMENTATION_TRACKER.md`
     - `docs/REFACTORING_PLAN.md`
3. Ask it to:
   - Read those docs.
   - Summarize current status.
   - Continue with the **next pending task** from `IMPLEMENTATION_TRACKER.md`.

---

## One-Sentence Summary for the Model

> We are building `agent-observable` as a monorepo of micro-libraries (observability, policy, guardrails, prompts) with `taskpilot` as an example client; use `IMPLEMENTATION_TRACKER.md` for the 2-week Phase 0 sprint tasks and respect decisions in `MUST_HAVE_FEATURES.md` and `REFACTORING_PLAN.md`.

