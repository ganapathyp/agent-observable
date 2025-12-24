"""TaskPilot-specific middleware hooks.

This file contains ONLY project-specific logic that extends
the generic observability middleware from the library.

Generic observability (metrics, traces, policy, guardrails) is
handled automatically by the library middleware.
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from agent_observable_core.middleware import MiddlewareHooks
from taskpilot.core.task_store import get_task_store, TaskStatus  # type: ignore
from taskpilot.core.types import AgentType  # type: ignore
from taskpilot.core.structured_output import parse_task_info_from_response  # type: ignore
from taskpilot.core.metric_names import (  # type: ignore
    TASKS_CREATED,
    TASKS_APPROVED,
    TASKS_REJECTED,
    TASKS_REVIEW,
    TASKS_EXECUTED,
    TASKS_REVIEWER_OUTPUT_EMPTY,
    TASKS_NO_PENDING_FOR_REVIEWER,
)
from taskpilot.core.observable import get_metrics  # type: ignore

logger = logging.getLogger(__name__)


def _detect_agent_type(agent_name: str) -> Optional[AgentType]:
    """Detect agent type from agent name (project-specific)."""
    name_lower = agent_name.lower()
    if "planner" in name_lower:
        return AgentType.PLANNER
    elif "reviewer" in name_lower:
        return AgentType.REVIEWER
    elif "executor" in name_lower:
        return AgentType.EXECUTOR
    return None


def _extract_text_from_messages(messages) -> str:
    """Extract text from message list (project-specific for MS Agent Framework)."""
    if not messages:
        return ""
    
    # Look for user messages first
    for msg in reversed(messages):
        if hasattr(msg, 'role') and msg.role == 'user':
            if hasattr(msg, 'content'):
                from agent_observable_core.structured_output import extract_text_from_response
                return extract_text_from_response(msg.content)
            if hasattr(msg, 'text'):
                return msg.text
    
    # Fallback: get text from last message
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, 'content'):
            from agent_observable_core.structured_output import extract_text_from_response
            return extract_text_from_response(last_msg.content)
        if hasattr(last_msg, 'text'):
            return last_msg.text
    
    return ""


def _extract_output_from_context(context: Any, result: Any) -> str:
    """Extract output text from context/result (project-specific for MS Agent Framework)."""
    from agent_observable_core.structured_output import extract_text_from_response
    
    # Check if result is an async generator
    is_async_gen = False
    if hasattr(result, '__class__'):
        class_name = result.__class__.__name__
        if 'async_generator' in class_name.lower() or 'generator' in class_name.lower():
            is_async_gen = True
    
    # Primary: Check context.result.agent_run_response.text
    if not is_async_gen and hasattr(result, 'agent_run_response'):
        agent_response = result.agent_run_response
        if hasattr(agent_response, 'text') and agent_response.text:
            return agent_response.text
        elif hasattr(agent_response, 'messages') and agent_response.messages:
            last_msg = agent_response.messages[-1]
            if hasattr(last_msg, 'content'):
                return extract_text_from_response(last_msg.content)
    
    # Check context.messages for assistant messages
    if hasattr(context, 'messages') and context.messages:
        assistant_messages = []
        for msg in context.messages:
            msg_role = getattr(msg, 'role', None)
            role_str = str(msg_role).lower() if msg_role else ''
            if role_str == 'assistant' or (hasattr(msg_role, 'value') and msg_role.value == 'assistant'):
                assistant_messages.append(msg)
        
        if assistant_messages:
            last_assistant = assistant_messages[-1]
            if hasattr(last_assistant, 'content'):
                return extract_text_from_response(last_assistant.content)
            elif hasattr(last_assistant, 'text'):
                return last_assistant.text
    
    # Fallback: use generic extractor
    return extract_text_from_response(result) if result else ""


class TaskPilotHooks(MiddlewareHooks):
    """TaskPilot-specific hooks for middleware extensions."""
    
    def __init__(self):
        self.store = get_task_store()
        self.metrics = get_metrics()
    
    def extract_input_text(self, context: Any) -> str:
        """Extract input text from MS Agent Framework context."""
        if hasattr(context, 'messages'):
            return _extract_text_from_messages(context.messages)
        return super().extract_input_text(context)
    
    def extract_output_text(self, context: Any, result: Any) -> str:
        """Extract output text from MS Agent Framework context/result."""
        return _extract_output_from_context(context, result)
    
    def on_agent_start(
        self,
        agent_name: str,
        input_text: str,
        context: Any,
        request_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Add task-specific tags to span."""
        agent_type = _detect_agent_type(agent_name)
        tags = {
            "agent_type": agent_type.value if agent_type else "unknown"
        }
        
        if input_text:
            tags["input_length"] = str(len(input_text))
            tags["input_preview"] = input_text[:100] + "..." if len(input_text) > 100 else input_text
        
        return tags
    
    def on_agent_complete(
        self,
        agent_name: str,
        output_text: str,
        context: Any,
        request_id: str,
        latency_ms: float,
    ) -> None:
        """Handle task-specific logic on agent completion."""
        agent_type = _detect_agent_type(agent_name)
        
        if agent_type == AgentType.PLANNER:
            self._handle_planner_complete(context, output_text, request_id)
        elif agent_type == AgentType.REVIEWER:
            self._handle_reviewer_complete(context, output_text, request_id)
        elif agent_type == AgentType.EXECUTOR:
            self._handle_executor_complete(context, output_text, request_id)
    
    def _handle_planner_complete(self, context: Any, output_text: str, request_id: str) -> None:
        """Handle planner completion - create task."""
        try:
            title, priority, description = self._parse_task_from_planner(context.result)
            if title:
                task = self.store.create_task(
                    title=title,
                    priority=priority,
                    description=description
                )
                self.metrics.increment_counter(TASKS_CREATED)
                logger.info(f"[TASK] Created task: {task.id} - {title} (request_id={request_id})")
        except Exception as e:
            logger.error(f"Failed to create task from planner: {e}", exc_info=True)
    
    def _handle_reviewer_complete(self, context: Any, output_text: str, request_id: str) -> None:
        """Handle reviewer completion - update task status."""
        pending_tasks = self.store.list_tasks(status=TaskStatus.PENDING, limit=1)
        if pending_tasks:
            task = pending_tasks[0]
            if not output_text:
                self.metrics.increment_counter(TASKS_REVIEWER_OUTPUT_EMPTY)
                logger.warning(f"[TASK] Reviewer output is empty (request_id={request_id})")
            else:
                output_upper = output_text.upper()
                try:
                    if "APPROVE" in output_upper:
                        self.store.update_task_status(
                            task.id,
                            TaskStatus.APPROVED,
                            reviewer_response=output_text
                        )
                        self.metrics.increment_counter(TASKS_APPROVED)
                        logger.info(f"[TASK] Task {task.id} approved (request_id={request_id})")
                    elif "REVIEW" in output_upper:
                        self.store.update_task_status(
                            task.id,
                            TaskStatus.REVIEW,
                            reviewer_response=output_text
                        )
                        self.metrics.increment_counter(TASKS_REVIEW)
                        logger.info(f"[TASK] Task {task.id} requires human review (request_id={request_id})")
                    else:
                        self.store.update_task_status(
                            task.id,
                            TaskStatus.REJECTED,
                            reviewer_response=output_text
                        )
                        self.metrics.increment_counter(TASKS_REJECTED)
                        logger.info(f"[TASK] Task {task.id} rejected (request_id={request_id})")
                except Exception as e:
                    logger.error(f"Failed to update task status: {e}", exc_info=True)
        else:
            self.metrics.increment_counter(TASKS_NO_PENDING_FOR_REVIEWER)
            logger.warning(f"[TASK] No pending tasks for reviewer (request_id={request_id})")
    
    def _handle_executor_complete(self, context: Any, output_text: str, request_id: str) -> None:
        """Handle executor completion - mark task as executed."""
        approved_tasks = self.store.list_tasks(status=TaskStatus.APPROVED, limit=1)
        if approved_tasks:
            task = approved_tasks[0]
            try:
                self.store.update_task_status(task.id, TaskStatus.EXECUTED)
                self.metrics.increment_counter(TASKS_EXECUTED)
                logger.info(f"[TASK] Task {task.id} executed (request_id={request_id})")
            except Exception as e:
                logger.error(f"Failed to mark task as executed: {e}", exc_info=True)
    
    def _parse_task_from_planner(self, response: Any) -> tuple[str, str, str]:
        """Parse task information from planner output (project-specific)."""
        try:
            task_info = parse_task_info_from_response(response)
            return task_info.title, task_info.priority, task_info.description
        except Exception as e:
            logger.warning(f"Structured parsing failed: {e}")
            return "", "medium", ""


__all__ = [
    "TaskPilotHooks",
    "_detect_agent_type",
]
