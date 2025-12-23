"""Pytest configuration and fixtures."""
import pytest
import tempfile
from pathlib import Path
from taskpilot.core.task_store import TaskStore
from taskpilot.core.observability import MetricsCollector


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Set up test environment before any tests run."""
    import os
    # Set environment variable to indicate we're in test mode
    os.environ['TESTING'] = '1'
    yield
    # Clean up
    os.environ.pop('TESTING', None)


@pytest.fixture(autouse=True)
def reset_global_metrics_collector():
    """Reset global metrics collector before each test to avoid file I/O issues."""
    # Reset the global singleton to None so it gets recreated in test mode
    import taskpilot.core.observability as obs_module
    obs_module._metrics_collector = None
    yield
    # Clean up after test
    obs_module._metrics_collector = None


@pytest.fixture
def temp_task_store():
    """Create a temporary task store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TaskStore(Path(tmpdir) / "test_tasks.json")
        yield store


@pytest.fixture
def in_memory_metrics():
    """Create an in-memory metrics collector for testing (no file I/O)."""
    return MetricsCollector(metrics_file=None)
