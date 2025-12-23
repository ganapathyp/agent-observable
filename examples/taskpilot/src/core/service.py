"""Service layer for business logic."""
import logging
from typing import Optional
from taskpilot.core.task_store import TaskStore, Task  # type: ignore
from taskpilot.core.types import TaskStatus  # type: ignore
from taskpilot.core.validation import ValidationError  # type: ignore

logger = logging.getLogger(__name__)


class TaskService:
    """Service layer for task management business logic."""
    
    def __init__(self, task_store: TaskStore):
        """Initialize task service.
        
        Args:
            task_store: TaskStore instance
        """
        self.store = task_store
    
    def create_task(
        self,
        title: str,
        priority: str,
        description: str = ""
    ) -> Task:
        """Create a new task with business logic.
        
        Args:
            title: Task title
            priority: Task priority
            description: Task description
            
        Returns:
            Created Task
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            task = self.store.create_task(
                title=title,
                priority=priority,
                description=description
            )
            logger.info(f"Task service created task: {task.id}")
            return task
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating task: {e}", exc_info=True)
            raise
    
    def approve_task(self, task_id: str, reviewer_response: Optional[str] = None) -> bool:
        """Approve a task.
        
        Args:
            task_id: Task ID
            reviewer_response: Optional reviewer response
            
        Returns:
            True if approved, False if not found
            
        Raises:
            ValidationError: If status transition is invalid
        """
        try:
            return self.store.update_task_status(
                task_id,
                TaskStatus.APPROVED,
                reviewer_response=reviewer_response
            )
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error approving task: {e}", exc_info=True)
            raise
    
    def reject_task(self, task_id: str, reviewer_response: Optional[str] = None) -> bool:
        """Reject a task.
        
        Args:
            task_id: Task ID
            reviewer_response: Optional reviewer response
            
        Returns:
            True if rejected, False if not found
            
        Raises:
            ValidationError: If status transition is invalid
        """
        try:
            return self.store.update_task_status(
                task_id,
                TaskStatus.REJECTED,
                reviewer_response=reviewer_response
            )
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error rejecting task: {e}", exc_info=True)
            raise
    
    def mark_for_review(self, task_id: str, reviewer_response: Optional[str] = None) -> bool:
        """Mark a task for human review.
        
        Args:
            task_id: Task ID
            reviewer_response: Optional reviewer response
            
        Returns:
            True if marked, False if not found
            
        Raises:
            ValidationError: If status transition is invalid
        """
        try:
            return self.store.update_task_status(
                task_id,
                TaskStatus.REVIEW,
                reviewer_response=reviewer_response
            )
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error marking task for review: {e}", exc_info=True)
            raise
    
    def execute_task(self, task_id: str) -> bool:
        """Mark a task as executed.
        
        Args:
            task_id: Task ID
            
        Returns:
            True if executed, False if not found
            
        Raises:
            ValidationError: If status transition is invalid
        """
        try:
            return self.store.update_task_status(task_id, TaskStatus.EXECUTED)
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error executing task: {e}", exc_info=True)
            raise
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark a task as failed.
        
        Args:
            task_id: Task ID
            error: Error message
            
        Returns:
            True if marked, False if not found
            
        Raises:
            ValidationError: If status transition is invalid
        """
        try:
            return self.store.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=error
            )
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error marking task as failed: {e}", exc_info=True)
            raise
