"""Core functionality: config, middleware, workflow.

This package exports:
- Configuration management (config.py)
- Middleware and observability (middleware.py, observable.py)
- Workflow orchestration (workflow.py)
- Standardized naming constants (metric_names.py, trace_names.py, policy_names.py)
"""

from taskpilot.core.config import get_config, create_config, Config  # type: ignore
from taskpilot.core.middleware import create_audit_and_policy_middleware  # type: ignore
from taskpilot.core.workflow import build_workflow  # type: ignore
from taskpilot.core.task_store import (  # type: ignore
    get_task_store,
    create_task_store,
    TaskStore,
    Task,
    TaskStatus,
)
from taskpilot.core.types import TaskPriority, AgentType  # type: ignore
from taskpilot.core.validation import ValidationError  # type: ignore
from taskpilot.core.models import TaskInfo  # type: ignore
from taskpilot.core.structured_output import parse_task_info_from_output  # type: ignore
from taskpilot.core.observable import (  # type: ignore
    RequestContext,
    get_request_id,
    get_metrics,
    get_errors,
    get_tracer,
    get_health,
    record_error,
)

__all__ = [
    "get_config",
    "create_config",
    "Config",
    "create_audit_and_policy_middleware",
    "build_workflow",
    "get_task_store",
    "create_task_store",
    "TaskStore",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "AgentType",
    "ValidationError",
    "TaskInfo",
    "parse_task_info_from_output",
    # Observability
    "RequestContext",
    "get_request_id",
    "get_metrics",
    "get_errors",
    "get_tracer",
    "get_health",
    "record_error",
]
