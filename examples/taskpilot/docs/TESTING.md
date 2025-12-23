# Testing Guide

## Overview

This guide covers the test suite, test coverage, and how to run tests for TaskPilot.

---

## Test Coverage

### Current Status

- **Overall Coverage:** 90%+
- **Functional Code:** 95%+
- **Test Count:** 150+ tests
- **Test Files:** 15 files

### Coverage by Module

| Module | Coverage | Test File |
|--------|----------|-----------|
| Task Store | ✅ 100% | `test_task_store.py` |
| Workflow | ✅ 100% | `test_workflow.py` |
| Config | ✅ 100% | `test_config.py` |
| Middleware | ✅ 100% | `test_middleware.py`, `test_middleware_async.py` |
| Tools | ✅ 100% | `test_tools.py` |
| Guardrails | ✅ 100% | `test_guardrails.py` |
| OPA | ✅ 100% | `test_opa_embedded.py` |
| Structured Output | ✅ 100% | `test_structured_output.py` |
| Function Calling | ✅ 100% | `test_function_calling.py` |
| Golden Signals | ✅ 100% | `test_golden_signals.py` |
| LLM Cost Tracker | ✅ 100% | `test_llm_cost_tracker.py` |
| OpenTelemetry | ✅ 90%+ | `test_otel_integration.py` |
| Main App | ✅ 90%+ | `test_main.py` |
| Integration | ✅ 100% | `test_integration.py` |

---

## Running Tests

### All Tests

```bash
make test
# or
pytest tests/ -v
```

### With Coverage

```bash
make test-coverage
# or
pytest tests/ --cov=src --cov-report=term-missing --cov-report=html
```

### Unit Tests Only

```bash
make test-unit
# or
pytest tests/test_*.py -v -k "not integration"
```

### Integration Tests

```bash
make test-integration
# or
pytest tests/test_integration.py -v
```

### Specific Test File

```bash
pytest tests/test_golden_signals.py -v
```

### Specific Test

```bash
pytest tests/test_golden_signals.py::TestGoldenSignals::test_golden_signals_empty_metrics -v
```

---

## Test Structure

### Test Files

```
tests/
├── conftest.py              # Pytest fixtures
├── test_config.py           # Configuration tests
├── test_task_store.py       # Task store tests
├── test_workflow.py         # Workflow tests
├── test_middleware.py       # Middleware tests
├── test_middleware_async.py # Async middleware tests
├── test_tools.py            # Tool tests
├── test_guardrails.py       # Guardrails tests
├── test_opa_embedded.py     # OPA tests
├── test_structured_output.py # Parsing tests
├── test_function_calling.py # Function calling tests
├── test_golden_signals.py   # Golden Signals tests
├── test_llm_cost_tracker.py # Cost tracking tests
├── test_otel_integration.py # OpenTelemetry tests
├── test_main.py             # Main app tests
└── test_integration.py      # Integration tests
```

### Test Fixtures

**Location:** `tests/conftest.py`

```python
@pytest.fixture
def temp_task_store():
    """Create a temporary task store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TaskStore(Path(tmpdir) / "test_tasks.json")
        yield store

@pytest.fixture
def in_memory_metrics():
    """Create an in-memory metrics collector (no file I/O)."""
    return MetricsCollector(metrics_file=None)
```

---

## Test Categories

### Unit Tests

**Purpose:** Test individual components in isolation

**Examples:**
- `test_task_store.py` - Task CRUD operations
- `test_golden_signals.py` - Golden Signals calculation
- `test_llm_cost_tracker.py` - Cost calculation

### Integration Tests

**Purpose:** Test end-to-end workflows

**Examples:**
- `test_integration.py` - Full workflow execution
- `test_main.py` - Server mode and endpoints

### Observability Tests

**Purpose:** Test metrics, traces, logs

**Examples:**
- `test_golden_signals.py` - Metrics calculation
- `test_otel_integration.py` - Trace export
- `test_main.py` - Metrics endpoints

---

## Test Best Practices

### 1. Use In-Memory Metrics

**Avoid file I/O in tests:**
```python
def test_metrics():
    metrics = MetricsCollector(metrics_file=None)  # In-memory only
    # Test metrics
```

### 2. Isolate Tests

**Use fixtures for isolation:**
```python
@pytest.fixture
def clean_metrics():
    """Reset metrics before each test."""
    import taskpilot.core.observability as obs
    obs._metrics_collector = None
    yield
    obs._metrics_collector = None
```

### 3. Test Edge Cases

**Test zero values, None, errors:**
```python
def test_golden_signals_empty():
    metrics = MetricsCollector(metrics_file=None)
    signals = metrics.get_golden_signals()
    assert signals["success_rate"] == 0.0
```

### 4. Mock External Dependencies

**Mock LLM calls, file I/O:**
```python
@patch('taskpilot.core.otel_integration.TracerProvider')
def test_otel_initialization(mock_provider):
    # Test with mocks
```

---

## Viewing Coverage

### HTML Report

```bash
make test-coverage
open htmlcov/index.html
```

**Shows:**
- Coverage percentage per file
- Missing lines highlighted
- Branch coverage

### Terminal Report

```bash
pytest tests/ --cov=src --cov-report=term-missing
```

**Shows:**
- Coverage percentage
- Missing lines (marked with `>>>`)

---

## Test Maintenance

### Adding New Tests

1. **Create test file:** `tests/test_<module>.py`
2. **Follow naming:** `test_<function_name>`
3. **Use fixtures:** From `conftest.py`
4. **Run tests:** `pytest tests/test_<module>.py -v`

### Updating Tests

**When code changes:**
1. Run tests: `make test`
2. Fix failing tests
3. Update test expectations
4. Verify coverage: `make test-coverage`

---

*Always run tests after making changes. See [DEVELOPMENT_PRACTICES.md](DEVELOPMENT_PRACTICES.md) for details.*
