# File Organization

## Directory Structure

```
taskpilot/
├── main.py                    # Main entry point
├── README.md                  # Project README
├── pyproject.toml             # Python project config
├── requirements.txt          # Python dependencies
├── pytest.ini                # Pytest configuration
├── Makefile                  # Build automation
├── .env                      # Environment variables
├── .gitignore                # Git ignore rules
│
├── src/                      # Source code
│   ├── agents/               # Agent implementations
│   ├── core/                 # Core functionality
│   │   ├── guardrails/       # Guardrails implementation
│   │   └── ...
│   └── tools/                # Tool implementations
│
├── tests/                    # Test files
│   ├── test_*.py            # Unit and integration tests
│   └── ...
│
├── scripts/                  # Utility scripts
│   ├── observability/        # Observability scripts
│   │   ├── start-observability.sh
│   │   ├── check-observability.sh
│   │   └── ...
│   ├── utils/               # Utility Python scripts
│   │   ├── health_check.py
│   │   ├── view_traces.py
│   │   ├── view_decision_logs.py
│   │   ├── list_tasks.py
│   │   ├── create_review_task.py
│   │   └── review_tasks.py
│   ├── demo.sh              # Demo script
│   └── run.sh               # Run script
│
├── docs/                     # Documentation
│   ├── README.md            # Documentation index
│   ├── CURRENT_ARCHITECTURE.md
│   ├── OBSERVABILITY_INTEGRATION.md
│   └── ...
│
├── observability/            # Observability configs
│   ├── prometheus/
│   ├── grafana/
│   ├── otel/
│   └── filebeat/
│
├── prompts/                  # Agent prompts
│   ├── planner.yaml
│   ├── executor.yaml
│   └── reviewer.yaml
│
├── policies/                 # Policy files
│   └── tool_calls.rego
│
├── logs/                     # Log files
│   └── taskpilot.log
│
└── docker-compose.observability.yml  # Docker compose
```

---

## Key Directories

### `src/` - Source Code
- **agents/** - Agent implementations (planner, executor, reviewer)
- **core/** - Core functionality (workflow, middleware, observability, guardrails)
- **tools/** - Tool implementations

### `scripts/` - Utility Scripts
- **observability/** - Shell scripts for observability setup/testing
- **utils/** - Python utility scripts (health check, viewing traces/logs, task management)

### `docs/` - Documentation
- Core documentation (architecture, observability, testing, etc.)
- Reference documentation
- Troubleshooting guides

### `observability/` - Observability Configuration
- Prometheus, Grafana, OpenTelemetry, Filebeat configurations

### `tests/` - Test Files
- All test files (unit, integration, e2e)

---

## File Organization Principles

1. **Source code** → `src/`
2. **Tests** → `tests/`
3. **Scripts** → `scripts/` (organized by purpose)
4. **Documentation** → `docs/`
5. **Configuration** → Root or dedicated folders (`observability/`, `policies/`, `prompts/`)
6. **Root directory** → Only essential files (main.py, README.md, config files)

---

## Usage Examples

### Running Scripts

```bash
# Observability
./scripts/observability/start-observability.sh
./scripts/observability/check-observability.sh

# Utilities
python scripts/utils/health_check.py --metrics
python scripts/utils/view_traces.py --agents
python scripts/utils/list_tasks.py

# Demo
./scripts/demo.sh
```

### Running Tests

```bash
# All tests
pytest tests/

# Specific test
pytest tests/test_golden_signals.py
```

---

*This organization keeps the root directory clean and makes it easy to find files.*
