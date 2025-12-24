"""Unit tests for tools module."""
import pytest
from unittest.mock import MagicMock, patch
from taskpilot.tools.tools import (
    _extract_task_info,
    create_task_workflow,
    notify_external_system_workflow,
    create_task,
    notify_external_system,
)


class TestExtractTaskInfo:
    """Test _extract_task_info function."""
    
    def test_extract_structured_format(self):
        """Test extracting from structured format."""
        text = """**Task Title:** Test Task
**Priority:** high
**Description:** Test description"""
        
        title, priority, description = _extract_task_info(text)
        
        assert title == "Test Task"
        assert priority == "high"
        assert description == "Test description"
    
    def test_extract_fallback(self):
        """Test fallback when no structured format."""
        text = "Simple task description"
        
        title, priority, description = _extract_task_info(text)
        
        assert title == "Simple task description"
        assert priority == "medium"  # default
        assert description == ""
    
    def test_extract_multiline_fallback(self):
        """Test fallback with multiple lines."""
        text = "First line\nSecond line\nThird line"
        
        title, priority, description = _extract_task_info(text)
        
        assert title == "First line"
        assert "Second line" in description or "Third line" in description
    
    def test_extract_case_insensitive(self):
        """Test case-insensitive matching."""
        text = """**task title:** Test
**priority:** HIGH
**description:** Desc"""
        
        title, priority, description = _extract_task_info(text)
        
        assert title == "Test"
        assert priority == "high"
        assert description == "Desc"


class TestWorkflowTools:
    """Test workflow-compatible tools."""
    
    @patch('taskpilot.tools.tools.get_task_store')
    def test_create_task_workflow_with_text_attr(self, mock_get_store):
        """Test create_task_workflow with message.text."""
        mock_store = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "test_123"
        mock_store.create_task.return_value = mock_task
        mock_get_store.return_value = mock_store
        
        class MockMessage:
            def __init__(self, text):
                self.text = text
        
        message = MockMessage("**Task Title:** Test\n**Priority:** high")
        result = create_task_workflow(message)
        
        assert "Task CREATED" in result
        assert "test_123" in result
        mock_store.create_task.assert_called_once()
    
    @patch('taskpilot.tools.tools.get_task_store')
    def test_create_task_workflow_with_string(self, mock_get_store):
        """Test create_task_workflow with string message."""
        mock_store = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "test_123"
        mock_store.create_task.return_value = mock_task
        mock_get_store.return_value = mock_store
        
        result = create_task_workflow("Test task")
        
        assert "Task CREATED" in result
        mock_store.create_task.assert_called_once()
    
    @patch('taskpilot.tools.tools.get_task_store')
    def test_create_task_workflow_with_object(self, mock_get_store):
        """Test create_task_workflow with object message."""
        mock_store = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "test_123"
        mock_store.create_task.return_value = mock_task
        mock_get_store.return_value = mock_store
        
        class MockObject:
            def __str__(self):
                return "Test task"
        
        result = create_task_workflow(MockObject())
        
        assert "Task CREATED" in result
        mock_store.create_task.assert_called_once()
    
    def test_notify_external_system_workflow_with_text(self):
        """Test notify_external_system_workflow with message.text."""
        class MockMessage:
            def __init__(self, text):
                self.text = text
        
        message = MockMessage("Test notification")
        result = notify_external_system_workflow(message)
        
        assert "[MCP] External system notified" in result
        assert "Test notification" in result
    
    def test_notify_external_system_workflow_with_string(self):
        """Test notify_external_system_workflow with string."""
        result = notify_external_system_workflow("Test notification")
        
        assert "[MCP] External system notified" in result
        assert "Test notification" in result
    
    def test_notify_external_system_workflow_with_object(self):
        """Test notify_external_system_workflow with object."""
        class MockObject:
            def __str__(self):
                return "Test notification"
        
        result = notify_external_system_workflow(MockObject())
        
        assert "[MCP] External system notified" in result
        assert "Test notification" in result


class TestAgentTools:
    """Test agent-compatible tools."""
    
    @patch('taskpilot.tools.tools.get_task_store')
    @patch('taskpilot.tools.tools._opa_validator')
    def test_create_task(self, mock_opa_validator, mock_get_store):
        """Test create_task agent tool."""
        # Mock OPA validation to allow the call
        mock_opa_validator.validate_tool_call = MagicMock(return_value=(True, "Allowed", False))
        
        mock_store = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "test_123"
        mock_store.create_task.return_value = mock_task
        mock_get_store.return_value = mock_store
        
        result = create_task("Test Task", "high")
        
        assert "Task CREATED" in result
        assert "Test Task" in result
        assert "high" in result
        assert "test_123" in result
        mock_store.create_task.assert_called_once_with(
            title="Test Task",
            priority="high",
            description=""  # description is now a parameter with default ""
        )
    
    @patch('taskpilot.tools.tools._opa_validator')
    def test_notify_external_system(self, mock_opa_validator):
        """Test notify_external_system agent tool."""
        # Mock OPA validation to allow the call
        mock_opa_validator.validate_tool_call = MagicMock(return_value=(True, "Allowed", False))
        
        result = notify_external_system("Test message")
        
        assert "[MCP] External system notified" in result
        assert "Test message" in result
