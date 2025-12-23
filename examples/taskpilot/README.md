# TaskPilot — Agent Framework Reference App

TaskPilot is a **concise but complete reference project** that demonstrates *all major capabilities*
of the Microsoft Agent Framework using **OpenAI + Python**.

This extended version adds:
- Branching workflows + human approval
- MCP-style tool integration (mocked for local use)
- Multi-agent collaboration
- Blog-ready explanation + architecture diagram

> If you understand TaskPilot, you understand Agent Framework.

---

## Quick Start

### 1. Configure

```bash
# Copy example config
cp .env.example .env

# Edit .env and set your OpenAI API key
OPENAI_API_KEY=your-api-key-here
```

**That's it!** TaskPilot works out-of-the-box with sensible defaults.

### 2. Run

```bash
# Run workflow once
python main.py

# Or run as server (production mode)
python main.py --server --port 8000

# View tasks
python scripts/utils/list_tasks.py

# Review tasks (human-in-the-loop)
python scripts/utils/review_tasks.py
```

### 3. Production Deployment

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for production configuration.

---

## Documentation

All documentation is in the [`docs/`](docs/) directory:

### Essential Guides (Start Here)
- **[REFERENCE.md](docs/REFERENCE.md)** - 🆕 Complete reference implementation guide
- **[ONBOARDING.md](docs/ONBOARDING.md)** - Developer onboarding guide
- **[DESIGN.md](docs/DESIGN.md)** - Architecture and design documentation

### Deep Dives
- **[GUARDRAILS_ARCHITECTURE_EXPLAINED.md](docs/GUARDRAILS_ARCHITECTURE_EXPLAINED.md)** - Guardrails architecture deep dive
- **[PRODUCTION_GUARDRAILS_ARCHITECTURE.md](docs/PRODUCTION_GUARDRAILS_ARCHITECTURE.md)** - Production guardrails design
- **[EMBEDDED_OPA_IMPLEMENTATION.md](docs/EMBEDDED_OPA_IMPLEMENTATION.md)** - Embedded OPA implementation details

### Reference
- **[TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Testing instructions for all workflow states
- **[TASK_TRACKING.md](docs/TASK_TRACKING.md)** - Task storage and review flow
- **[STRUCTURED_OUTPUT.md](docs/STRUCTURED_OUTPUT.md)** - Structured output parsing strategies
- **[CAPABILITIES_MATRIX.md](docs/CAPABILITIES_MATRIX.md)** - Capabilities analysis vs. best practices
- **[CHANGELOG.md](docs/CHANGELOG.md)** - Version history

---

## What this app shows

1. Agents reason (Planner, Reviewer, Executor)
2. Middleware governs (policy, audit, guardrails)
3. Workflows orchestrate (branching + approval)
4. Humans stay in the loop
5. Tools act (including MCP-style tools)
6. Production guardrails (NeMo Guardrails + Embedded OPA)
7. Everything is auditable (decision logging)

---

## Structure

```
taskpilot/
  docs/                     # All documentation
  src/                      # Source code (package root)
  .venv/                    # Isolated virtual environment
  .env                       # API keys (not in git)
  main.py                    # Entry point script
  run.sh                     # Convenience script
  requirements.txt           # Dependencies
  pyproject.toml            # Package configuration
```

---

## Setup

See [docs/README.md](docs/README.md) for detailed setup instructions.

**Quick setup:**
```bash
./run.sh  # Creates venv, installs dependencies, runs app
```

### Automatic Virtual Environment Activation

To automatically activate the virtual environment when you `cd` into this folder, see [docs/AUTO_ACTIVATE_VENV.md](docs/AUTO_ACTIVATE_VENV.md).

**Quick setup with direnv (recommended):**
```bash
# 1. Install direnv
brew install direnv

# 2. Add to ~/.zshrc:
eval "$(direnv hook zsh)"

# 3. Allow in this directory (first time only)
cd taskpilot
direnv allow
```

Now the virtual environment will activate automatically when you enter the folder!

## Testing

**Run all tests:**
```bash
make test
# or
.venv/bin/python -m pytest tests/ -v
```

**Run with coverage report:**
```bash
make test-coverage
# or
.venv/bin/python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html
```

**View coverage report:**
```bash
# Terminal output (shown after running tests)
make test-coverage

# HTML report
# Option 1: Open in browser (macOS)
open htmlcov/index.html

# Option 2: In VS Code/Cursor
# Right-click htmlcov/index.html → "Open With" → Browser
# Or use Command Palette: "Simple Browser: Show"
```

See [docs/VIEWING_COVERAGE.md](docs/VIEWING_COVERAGE.md) for detailed instructions.

**Run unit tests only:**
```bash
make test-unit
# or
.venv/bin/python -m pytest tests/test_*.py -v -k "not integration"
```

**Run integration tests:**
```bash
make test-integration
# or
.venv/bin/python tests/test_integration.py
```

**Test structure:**
- `tests/` - Unit and integration tests
- `scripts/` - Helper scripts for testing workflows
- `htmlcov/` - HTML coverage reports (generated)

---

## License

See project root for license information.
