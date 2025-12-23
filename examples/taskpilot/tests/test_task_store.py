"""Unit tests for task_store module."""
import pytest
import tempfile
import json
from pathlib import Path
from taskpilot.core.task_store import TaskStore, TaskStatus, Task, get_task_store


class TestTaskStore:
    """Test TaskStore functionality."""
    
    def test_create_task(self):
        """Test task creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "test_tasks.json")
            
            task = store.create_task(
                title="Test Task",
                priority="high",
                description="Test description"
            )
            
            assert task.title == "Test Task"
            assert task.priority == "high"
            assert task.description == "Test description"
            assert task.status == TaskStatus.PENDING
            assert task.id is not None
    
    def test_get_task(self):
        """Test retrieving a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "test_tasks.json")
            
            created = store.create_task("Test", "medium")
            retrieved = store.get_task(created.id)
            
            assert retrieved is not None
            assert retrieved.id == created.id
            assert retrieved.title == "Test"
    
    def test_update_task_status(self):
        """Test updating task status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "test_tasks.json")
            
            task = store.create_task("Test", "high")
            success = store.update_task_status(
                task.id,
                TaskStatus.APPROVED,
                reviewer_response="Approved"
            )
            
            assert success is True
            updated = store.get_task(task.id)
            assert updated.status == TaskStatus.APPROVED
            assert updated.reviewer_response == "Approved"
    
    def test_list_tasks(self):
        """Test listing tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "test_tasks.json")
            
            store.create_task("Task 1", "high")
            store.create_task("Task 2", "medium")
            store.create_task("Task 3", "low")
            
            all_tasks = store.list_tasks()
            assert len(all_tasks) == 3
    
    def test_list_tasks_by_status(self):
        """Test filtering tasks by status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "test_tasks.json")
            
            task1 = store.create_task("Task 1", "high")
            task2 = store.create_task("Task 2", "medium")
            
            store.update_task_status(task1.id, TaskStatus.APPROVED)
            store.update_task_status(task2.id, TaskStatus.REJECTED)
            
            approved = store.list_tasks(status=TaskStatus.APPROVED)
            rejected = store.list_tasks(status=TaskStatus.REJECTED)
            
            assert len(approved) == 1
            assert len(rejected) == 1
            assert approved[0].id == task1.id
            assert rejected[0].id == task2.id
    
    def test_get_stats(self):
        """Test getting task statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "test_tasks.json")
            
            task1 = store.create_task("Task 1", "high")
            task2 = store.create_task("Task 2", "medium")
            
            store.update_task_status(task1.id, TaskStatus.APPROVED)
            store.update_task_status(task2.id, TaskStatus.REJECTED)
            
            stats = store.get_stats()
            assert stats[TaskStatus.APPROVED.value] == 1
            assert stats[TaskStatus.REJECTED.value] == 1
            assert stats[TaskStatus.PENDING.value] == 0
    
    def test_persistence(self):
        """Test that tasks persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_tasks.json"
            
            # Create store and task
            store1 = TaskStore(storage_path)
            task = store1.create_task("Persistent Task", "high")
            
            # Create new store instance
            store2 = TaskStore(storage_path)
            retrieved = store2.get_task(task.id)
            
            assert retrieved is not None
            assert retrieved.title == "Persistent Task"
    
    def test_update_task_not_found(self):
        """Test updating non-existent task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "test_tasks.json")
            
            success = store.update_task_status("nonexistent", TaskStatus.APPROVED)
            assert success is False
    
    def test_update_task_with_error(self):
        """Test updating task with error message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "test_tasks.json")
            
            task = store.create_task("Test", "high")
            # First approve, then fail (valid transition)
            store.update_task_status(task.id, TaskStatus.APPROVED)
            success = store.update_task_status(
                task.id,
                TaskStatus.FAILED,
                error="Test error"
            )
            
            assert success is True
            updated = store.get_task(task.id)
            assert updated.error == "Test error"
    
    def test_load_with_invalid_json(self):
        """Test loading with invalid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_tasks.json"
            storage_path.write_text("invalid json{")
            
            store = TaskStore(storage_path)
            # Should handle error gracefully
            assert len(store.list_tasks()) == 0
    
    def test_update_task_executed_sets_timestamp(self):
        """Test that updating to EXECUTED sets executed_at."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "test_tasks.json")
            
            task = store.create_task("Test", "high")
            # First approve, then execute (valid transition)
            store.update_task_status(task.id, TaskStatus.APPROVED)
            store.update_task_status(task.id, TaskStatus.EXECUTED)
            
            updated = store.get_task(task.id)
            assert updated.executed_at is not None
            assert updated.status == TaskStatus.EXECUTED
    
    def test_list_tasks_with_limit(self):
        """Test listing tasks with limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(Path(tmpdir) / "test_tasks.json")
            
            store.create_task("Task 1", "high")
            store.create_task("Task 2", "medium")
            store.create_task("Task 3", "low")
            
            limited = store.list_tasks(limit=2)
            assert len(limited) == 2
    
    def test_load_error_handling(self):
        """Test error handling when loading invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_tasks.json"
            # Write invalid JSON
            storage_path.write_text("{ invalid json }")
            
            store = TaskStore(storage_path)
            # Should handle error gracefully
            assert len(store.list_tasks()) == 0


class TestTask:
    """Test Task dataclass."""
    
    def test_task_to_dict(self):
        """Test task serialization."""
        task = Task(
            id="test_123",
            title="Test",
            priority="high",
            description="Desc",
            status=TaskStatus.PENDING,
            created_at="2024-01-01T00:00:00"
        )
        
        data = task.to_dict()
        assert data["id"] == "test_123"
        assert data["title"] == "Test"
        assert data["status"] == "pending"
    
    def test_task_from_dict(self):
        """Test task deserialization."""
        data = {
            "id": "test_123",
            "title": "Test",
            "priority": "high",
            "description": "Desc",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00"
        }
        
        task = Task.from_dict(data)
        assert task.id == "test_123"
        assert task.status == TaskStatus.PENDING
