"""Main middleware entry point - composes observability and task logic.

This module provides the main middleware factory function that composes:
- Observability middleware (library integration)
- Task middleware (project-specific business logic)

The middleware is split into separate concerns for better maintainability.
"""
from __future__ import annotations

import logging
from typing import Callable, Awaitable, Optional

from agent_framework import AgentRunContext  # type: ignore
from taskpilot.core.task_store import TaskStore, get_task_store  # type: ignore
from taskpilot.core.task_hooks import TaskPilotHooks  # type: ignore
from taskpilot.core.observability_middleware import create_observability_middleware  # type: ignore

logger = logging.getLogger(__name__)


def create_audit_and_policy_middleware(
    agent_name: str,
    task_store: Optional[TaskStore] = None
) -> Callable[[AgentRunContext, Callable], Awaitable[None]]:
    """Create middleware with agent name captured.
    
    This is the main entry point for creating middleware. It composes:
    - Observability middleware (metrics, traces, logs, policy, guardrails)
    - Task hooks (project-specific business logic)
    
    Args:
        agent_name: Name of the agent (e.g., "PlannerAgent")
        task_store: Optional TaskStore instance. If None, uses global instance.
    
    Returns:
        Middleware function
    """
    # Create hooks for project-specific logic
    hooks = TaskPilotHooks()
    if task_store:
        hooks.store = task_store
    
    # Create observability middleware with hooks
    return create_observability_middleware(agent_name, hooks=hooks)
