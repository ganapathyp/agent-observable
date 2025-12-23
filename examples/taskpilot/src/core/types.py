"""Type definitions and enums for TaskPilot."""
from enum import Enum

class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"      # Created by planner, awaiting review
    APPROVED = "approved"     # Reviewed and approved, awaiting execution
    REJECTED = "rejected"     # Reviewed and rejected by agent
    REVIEW = "review"         # Requires human review (human-in-the-loop)
    EXECUTED = "executed"     # Successfully executed
    FAILED = "failed"         # Execution failed

class TaskPriority(str, Enum):
    """Task priority enumeration."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class AgentType(str, Enum):
    """Agent type enumeration."""
    PLANNER = "planner"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"

# Valid status transitions
VALID_STATUS_TRANSITIONS = {
    TaskStatus.PENDING: {TaskStatus.APPROVED, TaskStatus.REJECTED, TaskStatus.REVIEW},
    TaskStatus.APPROVED: {TaskStatus.EXECUTED, TaskStatus.FAILED},
    TaskStatus.REVIEW: {TaskStatus.APPROVED, TaskStatus.REJECTED},
    TaskStatus.REJECTED: set(),  # Terminal state
    TaskStatus.EXECUTED: set(),   # Terminal state
    TaskStatus.FAILED: {TaskStatus.APPROVED},  # Can retry
}
