"""Validation utilities for TaskPilot."""
from taskpilot.core.types import TaskStatus, TaskPriority, VALID_STATUS_TRANSITIONS  # type: ignore
from taskpilot.core.exceptions import ValidationError, InputValidationError, TaskValidationError  # type: ignore

# Re-export for backward compatibility
__all__ = ["ValidationError", "InputValidationError", "TaskValidationError", "validate_priority", "validate_title", "validate_description", "validate_status_transition"]


def validate_priority(priority: str) -> TaskPriority:
    """Validate and normalize task priority.
    
    Args:
        priority: Priority string (case-insensitive)
        
    Returns:
        TaskPriority enum value
        
    Raises:
        ValidationError: If priority is invalid
    """
    try:
        return TaskPriority(priority.lower())
    except ValueError:
        raise ValidationError(
            f"Invalid priority: {priority}. Must be one of: {', '.join(p.value for p in TaskPriority)}"
        )


def validate_title(title: str) -> str:
    """Validate task title.
    
    Args:
        title: Task title
        
    Returns:
        Sanitized title
        
    Raises:
        ValidationError: If title is invalid
    """
    if not title:
        raise InputValidationError(field="title", reason="Task title cannot be empty")
    
    title = title.strip()
    
    if len(title) < 1:
        raise InputValidationError(field="title", reason="Task title cannot be empty")
    
    if len(title) > 500:
        raise InputValidationError(field="title", reason="Task title cannot exceed 500 characters")
    
    return title


def validate_description(description: str) -> str:
    """Validate task description.
    
    Args:
        description: Task description
        
    Returns:
        Sanitized description
    """
    if not description:
        return ""
    
    description = description.strip()
    
    if len(description) > 10000:
        raise ValidationError("Task description cannot exceed 10000 characters")
    
    return description


def validate_status_transition(current_status: TaskStatus, new_status: TaskStatus) -> bool:
    """Validate status transition.
    
    Args:
        current_status: Current task status
        new_status: Desired new status
        
    Returns:
        True if transition is valid
        
    Raises:
        ValidationError: If transition is invalid
    """
    if current_status == new_status:
        return True  # No-op transition is valid
    
    allowed = VALID_STATUS_TRANSITIONS.get(current_status, set())
    
    if new_status not in allowed:
        raise TaskValidationError(
            task_id=None,
            reason=f"Invalid status transition: {current_status.value} -> {new_status.value}. "
                   f"Allowed transitions: {', '.join(s.value for s in allowed) if allowed else 'none'}"
        )
    
    return True
