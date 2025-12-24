from typing import Any, Optional
import re
import logging
from agent_framework import ai_function, WorkflowContext, AgentExecutorResponse  # type: ignore
from taskpilot.core.task_store import get_task_store, TaskStatus  # type: ignore
from taskpilot.core.validation import validate_priority  # type: ignore
from agent_observable_policy import OPAToolValidator  # type: ignore
from taskpilot.core.types import AgentType  # type: ignore

logger = logging.getLogger(__name__)

# Global OPA validator instance (using embedded OPA by default)
# Note: OPA validator will be created when needed with proper configuration
_opa_validator: Optional[OPAToolValidator] = None


def _get_opa_validator() -> OPAToolValidator:
    """Get or create OPA validator instance."""
    global _opa_validator
    if _opa_validator is None:
        _opa_validator = OPAToolValidator(
            use_embedded=True,
            package="taskpilot.tool_calls",
            service_name="taskpilot",
        )
    return _opa_validator


def _get_current_agent_type() -> str:
    """Get current agent type (simplified - in production, get from context)."""
    # For now, default to PlannerAgent
    # In production, this would come from execution context
    return "PlannerAgent"

# Agent-compatible tools (with @ai_function decorator)
@ai_function
def create_task(title: str, priority: str, description: str = "") -> str:
    """Create a task with title, priority, and description.
    
    Args:
        title: Task title (required, 1-500 characters)
        priority: Task priority - high, medium, or low (required)
        description: Task description (optional, max 10000 characters, default: empty string)
    
    This tool is validated with OPA before execution.
    """
    import asyncio
    
    # Normalize priority (handle case where LLM might not provide it, though schema requires it)
    if not priority:
        priority = "medium"
    
    # Validate tool call with OPA (sync wrapper for async validation)
    agent_type = _get_current_agent_type()
    
    # Check if we're in an async context
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context - can't use run_until_complete
        # Validation will be handled by middleware (which runs in async context)
        logger.debug("OPA validation skipped: running in async context, validation will be handled by middleware")
        allowed, reason, requires_approval = True, "Validation deferred to middleware", False
    except RuntimeError:
        # No event loop running - safe to use run_until_complete
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            allowed, reason, requires_approval = loop.run_until_complete(
                _get_opa_validator().validate_tool_call(
                    tool_name="create_task",
                    parameters={"title": title, "priority": priority, "description": description},
                    agent_type=agent_type,
                )
            )
            loop.close()
        except Exception as e:
            logger.warning(f"OPA validation failed: {e}, allowing tool call")
            allowed, reason, requires_approval = True, f"Validation error: {str(e)}", False
    
    if requires_approval:
        logger.warning(f"Tool call requires approval: {reason}")
        # In production, this would trigger approval workflow
        # For now, we'll allow but log
    
    if not allowed:
        logger.error(f"Tool call denied: {reason}")
        raise ValueError(f"Tool call denied: {reason}")
    
    store = get_task_store()
    task = store.create_task(title=title, priority=priority, description=description)
    return f"Task CREATED: {title} [{priority}] (ID: {task.id})"

@ai_function
def notify_external_system(message: str) -> str:
    """Notify external system (MCP-style tool).
    
    This tool is validated with OPA before execution.
    """
    import asyncio
    
    # Validate tool call with OPA (sync wrapper for async validation)
    agent_type = _get_current_agent_type()
    
    # Check if we're in an async context
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context - skip validation here (middleware will handle it)
        logger.warning("OPA validation skipped: running in async context, validation will be handled by middleware")
        allowed, reason, requires_approval = True, "Validation deferred to middleware", False
    except RuntimeError:
        # No event loop running - safe to use run_until_complete
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            allowed, reason, requires_approval = loop.run_until_complete(
                _get_opa_validator().validate_tool_call(
                    tool_name="notify_external_system",
                    parameters={"message": message},
                    agent_type=agent_type,
                )
            )
            loop.close()
        except Exception as e:
            logger.warning(f"OPA validation failed: {e}, allowing tool call")
            allowed, reason, requires_approval = True, f"Validation error: {str(e)}", False
    
    if requires_approval:
        logger.warning(f"Tool call requires approval: {reason}")
    
    if not allowed:
        logger.error(f"Tool call denied: {reason}")
        raise ValueError(f"Tool call denied: {reason}")
    
    return f"[MCP] External system notified: {message}"

def _extract_task_info(text: str) -> tuple[str, str, str]:
    """Extract task title, priority, and description from text.
    
    Uses modern structured output parsing with Pydantic validation.
    Falls back to legacy regex parsing if structured parsing fails.
    
    Args:
        text: Text containing task information
        
    Returns:
        Tuple of (title, priority, description)
    """
    from taskpilot.core.structured_output import parse_task_info_from_output  # type: ignore
    
    try:
        # Use structured output parser (preferred method)
        task_info = parse_task_info_from_output(text)
        return task_info.title, task_info.priority, task_info.description
    except Exception as e:
        logger.warning(f"Structured parsing failed: {e}, using legacy parser")
        # Fallback to legacy regex parsing
        return _extract_task_info_legacy(text)


def _extract_task_info_legacy(text: str) -> tuple[str, str, str]:
    """Legacy regex-based parsing (fallback only).
    
    Kept for backward compatibility but should not be used in new code.
    """
    title = ""
    priority = "medium"
    description = ""
    
    # Try to extract structured format
    title_match = re.search(r'\*\*Task Title:\*\*\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
    
    priority_match = re.search(r'\*\*Priority:\*\*\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if priority_match:
        priority = priority_match.group(1).strip().lower()
    
    desc_match = re.search(r'\*\*Description:\*\*\s*(.+?)(?:\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
    if desc_match:
        description = desc_match.group(1).strip()
    
    # Fallback: use first line as title if not found
    if not title:
        lines = text.split('\n')
        title = lines[0].strip() if lines else text[:50]
        description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
    
    return title, priority, description

# Workflow-compatible wrappers (without decorator, for FunctionExecutor)
def create_task_workflow(response: AgentExecutorResponse) -> str:
    """Create a task from workflow message.
    
    Extracts task information from the message and creates a task in the store.
    Used in workflows via FunctionExecutor.
    
    Args:
        response: AgentExecutorResponse from the agent executor
        
    Returns:
        WorkflowContext with task creation confirmation (str)
    """
    # Extract text from AgentExecutorResponse
    if hasattr(response, 'agent_run_response') and hasattr(response.agent_run_response, 'text'):
        text = response.agent_run_response.text
    elif hasattr(response, 'text'):
        text = response.text
    elif isinstance(response, str):
        text = response
    else:
        text = str(response)
    
    # Parse task information
    title, priority, description = _extract_task_info(text)
    
    # Create task in store
    store = get_task_store()
    task = store.create_task(
        title=title,
        priority=priority,
        description=description
    )
    
    logger.info(f"Created task in store: {task.id} - {title}")
    result = f"Task CREATED: {title} [{priority}] (ID: {task.id})"
    
    # Return string - FunctionExecutor will wrap it in WorkflowContext
    return result

def notify_external_system_workflow(response: AgentExecutorResponse) -> str:
    """Notify external system from workflow.
    
    Args:
        response: AgentExecutorResponse from the agent executor
        
    Returns:
        WorkflowContext with notification confirmation (str)
    """
    # Extract text from AgentExecutorResponse
    if hasattr(response, 'agent_run_response') and hasattr(response.agent_run_response, 'text'):
        text = response.agent_run_response.text
    elif hasattr(response, 'text'):
        text = response.text
    elif isinstance(response, str):
        text = response
    else:
        text = str(response)
    
    logger.info(f"Notifying external system: {text}")
    result = f"[MCP] External system notified: {text}"
    
    # Return string - FunctionExecutor will wrap it in WorkflowContext
    return result
