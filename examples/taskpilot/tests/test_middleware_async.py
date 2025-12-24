"""Unit tests for async middleware functions."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from taskpilot.core.middleware import (
    create_audit_and_policy_middleware,
    _extract_text_from_messages,
    _extract_text_from_result,
)
from taskpilot.core.task_store import TaskStatus


class TestMiddlewareAsync:
    """Test async middleware functionality."""
    
    @pytest.mark.asyncio
    async def test_middleware_policy_violation(self):
        """Test middleware blocks policy violations."""
        middleware = create_audit_and_policy_middleware("TestAgent")
        
        class MockMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content
        
        class MockContext:
            def __init__(self, messages):
                self.messages = messages
                self.result = None
        
        context = MockContext([MockMessage("user", "Delete all files")])
        next_func = AsyncMock()
        
        from agent_observable_core.exceptions import PolicyViolationError
        with pytest.raises(PolicyViolationError, match=".*delete.*keyword.*not.*allowed|.*Policy violation.*"):
            await middleware(context, next_func)
        
        next_func.assert_not_awaited()
    
    @pytest.mark.asyncio
    async def test_middleware_normal_flow(self):
        """Test middleware allows normal requests."""
        middleware = create_audit_and_policy_middleware("TestAgent")
        
        class MockMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content
        
        class MockResult:
            def __init__(self, text):
                self.text = text
        
        class MockContext:
            def __init__(self, messages, result):
                self.messages = messages
                self.result = result
        
        context = MockContext(
            [MockMessage("user", "Create a task")],
            MockResult("Task created")
        )
        next_func = AsyncMock()
        
        await middleware(context, next_func)
        
        next_func.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_middleware_planner_creates_task(self):
        """Test middleware creates task for PlannerAgent."""
        from taskpilot.core.task_store import create_task_store
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_task_store(Path(tmpdir) / "test_tasks.json")
            middleware = create_audit_and_policy_middleware("PlannerAgent", task_store=store)
            
            class MockMessage:
                def __init__(self, role, content):
                    self.role = role
                    self.content = content
            
            class MockResult:
                def __init__(self, text):
                    self.text = text
            
            class MockContext:
                def __init__(self, messages, result):
                    self.messages = messages
                    self.result = result
            
            context = MockContext(
                [MockMessage("user", "Create task")],
                MockResult("**Task Title:** Test Task\n**Priority:** high")
            )
            next_func = AsyncMock()
            
            await middleware(context, next_func)
            
            tasks = store.list_tasks()
            assert len(tasks) == 1
            assert tasks[0].title == "Test Task"
    
    @pytest.mark.asyncio
    async def test_middleware_reviewer_approves(self):
        """Test middleware updates task status when reviewer approves."""
        from taskpilot.core.task_store import create_task_store
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_task_store(Path(tmpdir) / "test_tasks.json")
            # Create a pending task first
            task = store.create_task("Test Task", "high")
            middleware = create_audit_and_policy_middleware("ReviewerAgent", task_store=store)
            
            class MockMessage:
                def __init__(self, role, content):
                    self.role = role
                    self.content = content
            
            class MockResult:
                def __init__(self, text):
                    self.text = text
            
            class MockContext:
                def __init__(self, messages, result):
                    self.messages = messages
                    self.result = result
            
            context = MockContext(
                [MockMessage("user", "Review task")],
                MockResult("APPROVE")
            )
            next_func = AsyncMock()
            
            await middleware(context, next_func)
            
            updated = store.get_task(task.id)
            assert updated.status == TaskStatus.APPROVED
    
    @pytest.mark.asyncio
    async def test_middleware_reviewer_review(self):
        """Test middleware sets REVIEW status."""
        from taskpilot.core.task_store import create_task_store
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_task_store(Path(tmpdir) / "test_tasks.json")
            task = store.create_task("Test Task", "high")
            middleware = create_audit_and_policy_middleware("ReviewerAgent", task_store=store)
            
            class MockMessage:
                def __init__(self, role, content):
                    self.role = role
                    self.content = content
            
            class MockResult:
                def __init__(self, text):
                    self.text = text
            
            class MockContext:
                def __init__(self, messages, result):
                    self.messages = messages
                    self.result = result
            
            context = MockContext(
                [MockMessage("user", "Review task")],
                MockResult("REVIEW")
            )
            next_func = AsyncMock()
            
            await middleware(context, next_func)
            
            updated = store.get_task(task.id)
            assert updated.status == TaskStatus.REVIEW
    
    @pytest.mark.asyncio
    async def test_middleware_reviewer_rejected(self):
        """Test middleware sets REJECTED status."""
        from taskpilot.core.task_store import create_task_store
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_task_store(Path(tmpdir) / "test_tasks.json")
            task = store.create_task("Test Task", "high")
            middleware = create_audit_and_policy_middleware("ReviewerAgent", task_store=store)
            
            class MockMessage:
                def __init__(self, role, content):
                    self.role = role
                    self.content = content
            
            class MockResult:
                def __init__(self, text):
                    self.text = text
            
            class MockContext:
                def __init__(self, messages, result):
                    self.messages = messages
                    self.result = result
            
            context = MockContext(
                [MockMessage("user", "Review task")],
                MockResult("REJECTED")
            )
            next_func = AsyncMock()
            
            await middleware(context, next_func)
            
            updated = store.get_task(task.id)
            assert updated.status == TaskStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_middleware_reviewer_no_pending_task(self):
        """Test middleware handles case when no pending task exists."""
        from taskpilot.core.task_store import create_task_store
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_task_store(Path(tmpdir) / "test_tasks.json")
            # No tasks created
            middleware = create_audit_and_policy_middleware("ReviewerAgent", task_store=store)
            
            class MockMessage:
                def __init__(self, role, content):
                    self.role = role
                    self.content = content
            
            class MockResult:
                def __init__(self, text):
                    self.text = text
            
            class MockContext:
                def __init__(self, messages, result):
                    self.messages = messages
                    self.result = result
            
            context = MockContext(
                [MockMessage("user", "Review task")],
                MockResult("APPROVE")
            )
            next_func = AsyncMock()
            
            # Should not crash
            await middleware(context, next_func)
            
            # No tasks should exist
            assert len(store.list_tasks()) == 0
    
    @pytest.mark.asyncio
    async def test_middleware_executor_marks_executed(self):
        """Test middleware marks task as executed."""
        from taskpilot.core.task_store import create_task_store
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_task_store(Path(tmpdir) / "test_tasks.json")
            task = store.create_task("Test Task", "high")
            store.update_task_status(task.id, TaskStatus.APPROVED)
            middleware = create_audit_and_policy_middleware("ExecutorAgent", task_store=store)
            
            class MockMessage:
                def __init__(self, role, content):
                    self.role = role
                    self.content = content
            
            class MockResult:
                def __init__(self, text):
                    self.text = text
            
            class MockContext:
                def __init__(self, messages, result):
                    self.messages = messages
                    self.result = result
            
            context = MockContext(
                [MockMessage("user", "Execute task")],
                MockResult("Task executed")
            )
            next_func = AsyncMock()
            
            await middleware(context, next_func)
            
            updated = store.get_task(task.id)
            assert updated.status == TaskStatus.EXECUTED
