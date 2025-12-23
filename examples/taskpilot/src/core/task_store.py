"""Task storage and management system."""
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

from taskpilot.core.types import TaskStatus, TaskPriority  # type: ignore
from taskpilot.core.validation import (  # type: ignore
    validate_priority,
    validate_title,
    validate_description,
    validate_status_transition,
    ValidationError,
)

logger = logging.getLogger(__name__)

@dataclass
class Task:
    """Task data structure."""
    id: str
    title: str
    priority: str
    description: str
    status: TaskStatus
    created_at: str
    reviewed_at: Optional[str] = None
    executed_at: Optional[str] = None
    reviewer_response: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from dictionary."""
        if isinstance(data.get("status"), str):
            data["status"] = TaskStatus(data["status"])
        return cls(**data)
    
    def validate(self) -> None:
        """Validate task data."""
        validate_title(self.title)
        validate_priority(self.priority)
        validate_description(self.description)

class TaskStore:
    """Simple file-based task storage."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize task store.
        
        Args:
            storage_path: Path to JSON file for storage. Defaults to configured path from PathConfig
        """
        if storage_path is None:
            # Use configured path from PathConfig
            try:
                from taskpilot.core.config import get_paths
                paths = get_paths()
                storage_path = paths.tasks_file
            except Exception:
                # Fallback to old behavior if config not available
                taskpilot_dir = Path(__file__).parent.parent.parent
                storage_path = taskpilot_dir / ".tasks.json"
        
        self.storage_path = Path(storage_path)
        self._tasks: Dict[str, Task] = {}
        self._load()
    
    def _load(self) -> None:
        """Load tasks from storage file with error recovery."""
        if not self.storage_path.exists():
            logger.info(f"Task storage file not found, starting fresh: {self.storage_path}")
            self._tasks = {}
            return
        
        # Try to load from backup if main file is corrupted
        backup_path = self.storage_path.with_suffix('.json.bak')
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self._tasks = {}
                for task_id, task_data in data.items():
                    try:
                        task = Task.from_dict(task_data)
                        task.validate()
                        self._tasks[task_id] = task
                    except (KeyError, ValueError, ValidationError) as e:
                        logger.warning(f"Skipping invalid task {task_id}: {e}")
                        continue
                
                logger.info(f"Loaded {len(self._tasks)} tasks from {self.storage_path}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error loading tasks: {e}")
            if backup_path.exists():
                logger.info(f"Attempting to recover from backup: {backup_path}")
                try:
                    with open(backup_path, 'r') as f:
                        data = json.load(f)
                        self._tasks = {
                            task_id: Task.from_dict(task_data)
                            for task_id, task_data in data.items()
                        }
                    logger.info(f"Recovered {len(self._tasks)} tasks from backup")
                    # Restore backup as main file
                    shutil.copy(backup_path, self.storage_path)
                except Exception as backup_error:
                    logger.error(f"Backup recovery failed: {backup_error}")
                    self._tasks = {}
            else:
                logger.error("No backup available, starting fresh")
                self._tasks = {}
        except Exception as e:
            logger.error(f"Error loading tasks: {e}", exc_info=True)
            self._tasks = {}
    
    def _save(self) -> None:
        """Save tasks to storage file with atomic write and backup."""
        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup of existing file
            if self.storage_path.exists():
                backup_path = self.storage_path.with_suffix('.json.bak')
                try:
                    shutil.copy(self.storage_path, backup_path)
                except Exception as e:
                    logger.warning(f"Could not create backup: {e}")
            
            # Convert to dict format
            data = {
                task_id: task.to_dict()
                for task_id, task in self._tasks.items()
            }
            
            # Atomic write: write to temp file, then rename
            temp_path = self.storage_path.with_suffix('.json.tmp')
            try:
                with open(temp_path, 'w') as f:
                    json.dump(data, f, indent=2)
                    # Ensure file is flushed before closing
                    f.flush()
                    # Force write to disk if possible
                    try:
                        if hasattr(f, 'fileno'):
                            os.fsync(f.fileno())
                    except (OSError, AttributeError):
                        # fsync may not be available on all systems
                        pass
            except Exception as e:
                # Clean up temp file if write failed
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                raise
            
            # Atomic rename (replace existing file)
            try:
                # On Windows, we need to remove the target first if it exists
                if self.storage_path.exists():
                    self.storage_path.unlink()
                temp_path.replace(self.storage_path)
            except Exception as e:
                # Clean up temp file if rename failed
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                raise
            
            logger.debug(f"Saved {len(self._tasks)} tasks to {self.storage_path}")
        except Exception as e:
            logger.error(f"Error saving tasks: {e}", exc_info=True)
            raise
    
    def create_task(
        self,
        title: str,
        priority: str,
        description: str = "",
        task_id: Optional[str] = None
    ) -> Task:
        """Create a new task with validation.
        
        Args:
            title: Task title
            priority: Task priority (high, medium, low)
            description: Task description
            task_id: Optional task ID. If not provided, generates one.
        
        Returns:
            Created Task object
            
        Raises:
            ValidationError: If input validation fails
        """
        # Validate inputs
        title = validate_title(title)
        priority_enum = validate_priority(priority)
        description = validate_description(description)
        
        if task_id is None:
            # Generate ID from timestamp
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        task = Task(
            id=task_id,
            title=title,
            priority=priority_enum.value,
            description=description,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        task.validate()
        self._tasks[task_id] = task
        self._save()
        logger.info(f"Created task: {task_id} - {title}")
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        reviewer_response: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        """Update task status with validation.
        
        Args:
            task_id: Task ID
            status: New status
            reviewer_response: Optional reviewer response
            error: Optional error message
        
        Returns:
            True if task was updated, False if not found
            
        Raises:
            ValidationError: If status transition is invalid
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return False
        
        # Validate status transition
        validate_status_transition(task.status, status)
        
        task.status = status
        if reviewer_response:
            task.reviewer_response = reviewer_response
            task.reviewed_at = datetime.now().isoformat()
        
        if status == TaskStatus.EXECUTED:
            task.executed_at = datetime.now().isoformat()
        
        if error:
            task.error = error
        
        self._save()
        logger.info(f"Updated task {task_id} to status: {status}")
        return True
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: Optional[int] = None
    ) -> List[Task]:
        """List tasks, optionally filtered by status.
        
        Args:
            status: Optional status filter
            limit: Optional limit on number of tasks
        
        Returns:
            List of tasks, sorted by creation time (newest first)
        """
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        if limit:
            tasks = tasks[:limit]
        
        return tasks
    
    def get_stats(self) -> Dict[str, int]:
        """Get task statistics."""
        stats = {status.value: 0 for status in TaskStatus}
        for task in self._tasks.values():
            stats[task.status.value] = stats.get(task.status.value, 0) + 1
        return stats
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID.
        
        Args:
            task_id: Task ID to delete
            
        Returns:
            True if task was deleted, False if not found
        """
        if task_id not in self._tasks:
            logger.warning(f"Task not found for deletion: {task_id}")
            return False
        
        del self._tasks[task_id]
        self._save()
        logger.info(f"Deleted task: {task_id}")
        return True
    
    def delete_tasks_by_status(self, status: TaskStatus) -> int:
        """Delete all tasks with a specific status.
        
        Args:
            status: Status to filter by
            
        Returns:
            Number of tasks deleted
        """
        task_ids_to_delete = [
            task_id for task_id, task in self._tasks.items()
            if task.status == status
        ]
        
        for task_id in task_ids_to_delete:
            del self._tasks[task_id]
        
        if task_ids_to_delete:
            self._save()
            logger.info(f"Deleted {len(task_ids_to_delete)} tasks with status: {status.value}")
        
        return len(task_ids_to_delete)
    
    def delete_old_tasks(self, keep_count: int = 200) -> int:
        """Delete old tasks, keeping only the most recent N tasks.
        
        Args:
            keep_count: Number of most recent tasks to keep (default: 200)
            
        Returns:
            Number of tasks deleted
        """
        if len(self._tasks) <= keep_count:
            return 0
        
        # Sort tasks by creation time (newest first)
        sorted_tasks = sorted(
            self._tasks.items(),
            key=lambda x: x[1].created_at,
            reverse=True
        )
        
        # Keep the most recent tasks
        tasks_to_keep = sorted_tasks[:keep_count]
        tasks_to_delete = sorted_tasks[keep_count:]
        
        # Delete old tasks
        for task_id, _ in tasks_to_delete:
            del self._tasks[task_id]
        
        if tasks_to_delete:
            self._save()
            logger.info(f"Deleted {len(tasks_to_delete)} old tasks, kept {len(tasks_to_keep)} most recent")
        
        return len(tasks_to_delete)
    
    def clear_all_tasks(self) -> int:
        """Delete all tasks.
        
        Returns:
            Number of tasks deleted
        """
        count = len(self._tasks)
        self._tasks = {}
        self._save()
        logger.info(f"Deleted all {count} tasks")
        return count

# Factory function for creating task stores
def create_task_store(storage_path: Optional[Path] = None) -> TaskStore:
    """Create a new TaskStore instance.
    
    Args:
        storage_path: Optional path to storage file
        
    Returns:
        New TaskStore instance
    """
    return TaskStore(storage_path)


# Global task store instance (for backward compatibility)
# Prefer using dependency injection with create_task_store() in new code
_task_store: Optional[TaskStore] = None

def get_task_store() -> TaskStore:
    """Get the global task store instance (backward compatibility).
    
    Note: For new code, prefer using dependency injection with create_task_store().
    
    Returns:
        Global TaskStore instance
    """
    global _task_store
    if _task_store is None:
        _task_store = TaskStore()
    return _task_store
