# TaskPilot Test Suite

## Structure

- **Unit Tests**: `test_*.py` - Fast, isolated tests for individual components
- **Integration Tests**: `test_integration.py` - End-to-end workflow tests
- **Helper Scripts**: `../scripts/` - Utilities for manual testing

## Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# Specific test file
.venv/bin/python -m pytest tests/test_task_store.py -v

# Specific test
.venv/bin/python -m pytest tests/test_task_store.py::TestTaskStore::test_create_task -v
```

## Test Coverage

- ✅ `test_task_store.py` - Task storage and management
- ✅ `test_workflow.py` - Workflow conditional logic
- ✅ `test_config.py` - Configuration management
- ✅ `test_middleware.py` - Middleware helper functions
- ✅ `test_integration.py` - Full workflow integration

## Adding Tests

Follow pytest conventions:
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

Use fixtures from `conftest.py` for common setup.
