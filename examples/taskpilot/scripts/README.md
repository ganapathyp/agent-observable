# Scripts Directory

This directory contains utility scripts organized by purpose.

## Structure

```
scripts/
├── observability/     # Observability-related shell scripts
├── utils/            # Utility Python scripts
└── README.md         # This file
```

---

## Observability Scripts

**Location:** `scripts/observability/`

### Setup & Management
- `start-observability.sh` - Start all observability services (Docker)
- `check-observability.sh` - Check status of observability services
- `verify-observability.sh` - Verify observability setup
- `setup-docker-configs.sh` - Setup Docker configuration files
- `fix-docker-mounts.sh` - Fix Docker volume mount issues

### Testing
- `test-metrics-flow.sh` - Test metrics collection flow
- `test-observability-integration.sh` - Test observability integration

### Utilities
- `demo-observability.sh` - Demo observability features
- `kill-port-8000.sh` - Kill process on port 8000

---

## Utility Scripts

**Location:** `scripts/utils/`

### Health & Monitoring
- `health_check.py` - Health check utility
  ```bash
  python scripts/utils/health_check.py --metrics
  python scripts/utils/health_check.py --health
  ```

### Viewing Data
- `view_traces.py` - View distributed traces
  ```bash
  python scripts/utils/view_traces.py --agents
  python scripts/utils/view_traces.py --request-id abc-123
  ```

- `view_decision_logs.py` - View decision logs
  ```bash
  python scripts/utils/view_decision_logs.py
  ```

### Task Management
- `list_tasks.py` - List tasks
  ```bash
  python scripts/utils/list_tasks.py
  ```

- `create_review_task.py` - Create review task
  ```bash
  python scripts/utils/create_review_task.py
  ```

- `review_tasks.py` - Review tasks
  ```bash
  python scripts/utils/review_tasks.py
  ```

- `test_review_flow.py` - Test review flow

---

## Usage Examples

### Start Observability Stack
```bash
./scripts/observability/start-observability.sh
```

### Check Health
```bash
python scripts/utils/health_check.py --health
```

### View Traces
```bash
python scripts/utils/view_traces.py --agents
```

### List Tasks
```bash
python scripts/utils/list_tasks.py
```

---

## Notes

- All scripts should be run from the `taskpilot/` root directory
- Python scripts use relative imports, so they must be run from the project root
- Shell scripts use relative paths, so they should be run from the project root
