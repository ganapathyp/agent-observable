# Agent Observable

Enterprise micro-libraries for agent observability, policy, guardrails, and prompts.

## Monorepo Structure

This repository is a **monorepo** containing:

- `libraries/` – Reusable micro-libraries
  - `agent-observable-core/` – Observability (metrics, traces, logs)
  - `agent-observable-policy/` – Policy decisions & OPA
  - `agent-observable-guardrails/` – Guardrails (NeMo, validation)
  - `agent-observable-prompt/` – Prompt management
- `examples/` – Example implementations
  - `taskpilot/` – Example client app using the libraries

## Current Status

- **Version**: v0.01 (planning + setup baseline)
- **Design**: Micro-library approach, monorepo with `taskpilot` as example client.
- **Rate Limiting**: Handled via cloud infrastructure (Azure API Management / AWS API Gateway), not implemented in-app.
- **Execution Plan**:
  - 2-week Phase 0 sprint: foundation (interfaces, DI, paths) + critical features (timeouts, retries).
  - See `docs/IMPLEMENTATION_TRACKER.md` for task-level status.

## Documentation

### Library Documentation

**agent-observable-core:**
- **[README](libraries/agent-observable-core/README.md)** - Library overview and quick start
- **[Auto-Enabled Observability](libraries/agent-observable-core/docs/AUTO_ENABLED_OBSERVABILITY.md)** - What's automatically tracked
- **[Metrics Reference](libraries/agent-observable-core/docs/METRICS.md)** - All metrics automatically enabled
- **[Traces Reference](libraries/agent-observable-core/docs/TRACES.md)** - Distributed tracing details
- **[Policy Decisions](libraries/agent-observable-core/docs/POLICY_DECISIONS.md)** - Policy decision logging
- **[Docker Tools Integration](libraries/agent-observable-core/docs/DOCKER_TOOLS.md)** - Viewing data in Prometheus, Grafana, Jaeger, Kibana

### Example Documentation

**TaskPilot (example app):**
- **[README](examples/taskpilot/README.md)** - Example app overview
- **[Documentation](examples/taskpilot/docs/README.md)** - TaskPilot-specific docs

### Project Documentation

- `docs/CODE_GENERATION_SPECIFICATION.md` – **Spec-driven code generation guide** for LLMs and developers
- `docs/METRICS_DEMO_SCENARIOS.md` – **19 demo scenarios** showcasing metrics value in Docker tools
- `docs/DIRECT_DATA_GENERATION_GUIDE.md` – **How to directly generate logs, traces, decisions** for demos
- `docs/REFACTORING_PLAN.md` – Full refactoring roadmap.
- `docs/MUST_HAVE_FEATURES.md` – Prioritized feature list.
- `docs/IMPLEMENTATION_TRACKER.md` – 2-week sprint tracker.
- `docs/SETUP_MONOREPO.md` – How this monorepo is structured.
- `docs/SESSION_BOOTSTRAP.md` – Text to bootstrap future AI sessions.

## Getting Started

1. Create and activate a virtual environment.
2. Install dependencies for the example app (`examples/taskpilot/`) once libraries are extracted.
3. Follow `docs/IMPLEMENTATION_TRACKER.md` to implement Phase 0 tasks.

