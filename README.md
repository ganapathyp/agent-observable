# Agent Observable

Enterprise micro-libraries for agent observability, policy, guardrails, and prompts.

## Monorepo Structure

This repository is a **monorepo** containing:

- `libraries/` – Reusable micro-libraries
  - `agent-observable-core/` – Observability (metrics, traces, logs)
  - `agent-observable-policy/` – Policy decisions & OPA
  - `agent-observable-guardrails/` – Guardrails (NeMo, validation)
  - `agent-observable-prompts/` – Prompt management
- `examples/` – Example implementations
  - `taskpilot/` – Example client app using the libraries

## Current Status

- **Version**: v0.01 (planning + setup baseline)
- **Design**: Micro-library approach, monorepo with `taskpilot` as example client.
- **Rate Limiting**: Handled via cloud infrastructure (Azure API Management / AWS API Gateway), not implemented in-app.
- **Execution Plan**:
  - 2-week Phase 0 sprint: foundation (interfaces, DI, paths) + critical features (timeouts, retries).
  - See `docs/IMPLEMENTATION_TRACKER.md` for task-level status.

## Key Docs

- `docs/REFACTORING_PLAN.md` – Full refactoring roadmap.
- `docs/MUST_HAVE_FEATURES.md` – Prioritized feature list.
- `docs/IMPLEMENTATION_TRACKER.md` – 2-week sprint tracker.
- `docs/SETUP_MONOREPO.md` – How this monorepo is structured.
- `docs/SESSION_BOOTSTRAP.md` – Text to bootstrap future AI sessions.

## Getting Started

1. Create and activate a virtual environment.
2. Install dependencies for the example app (`examples/taskpilot/`) once libraries are extracted.
3. Follow `docs/IMPLEMENTATION_TRACKER.md` to implement Phase 0 tasks.

