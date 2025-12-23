"""Tests for function calling structured output approach."""
import pytest
import json
from unittest.mock import MagicMock
from taskpilot.core.structured_output import parse_task_info_from_response
from taskpilot.core.models import TaskInfo


class TestFunctionCallingParsing:
    """Test parsing from function calling responses."""
    
    def test_parse_from_tool_calls(self):
        """Test parsing from direct tool_calls attribute."""
        # Mock function call response
        mock_function = MagicMock()
        mock_function.name = "create_task"
        mock_function.arguments = '{"title": "Test Task", "priority": "high", "description": "Test"}'
        
        mock_tool_call = MagicMock()
        mock_tool_call.function = mock_function
        
        mock_response = MagicMock()
        mock_response.tool_calls = [mock_tool_call]
        
        # Parse
        task_info = parse_task_info_from_response(mock_response)
        
        assert task_info.title == "Test Task"
        assert task_info.priority == "high"
        assert task_info.description == "Test"
    
    def test_parse_from_agent_run_response(self):
        """Test parsing from agent_run_response.tool_calls."""
        # Mock nested response structure
        mock_function = MagicMock()
        mock_function.name = "create_task"
        mock_function.arguments = '{"title": "Nested Task", "priority": "medium"}'
        
        mock_tool_call = MagicMock()
        mock_tool_call.function = mock_function
        
        mock_agent_response = MagicMock()
        mock_agent_response.tool_calls = [mock_tool_call]
        
        mock_response = MagicMock()
        mock_response.agent_run_response = mock_agent_response
        
        # Parse
        task_info = parse_task_info_from_response(mock_response)
        
        assert task_info.title == "Nested Task"
        assert task_info.priority == "medium"
    
    def test_parse_invalid_function_call(self):
        """Test handling invalid function call arguments."""
        mock_function = MagicMock()
        mock_function.name = "create_task"
        mock_function.arguments = '{"invalid": "json"'  # Invalid JSON
        
        mock_tool_call = MagicMock()
        mock_tool_call.function = mock_function
        
        mock_response = MagicMock()
        mock_response.tool_calls = [mock_tool_call]
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid function call arguments"):
            parse_task_info_from_response(mock_response)
    
    def test_parse_wrong_function_name(self):
        """Test that wrong function name falls through to text parsing."""
        # Create proper mock structure
        class MockFunction:
            def __init__(self):
                self.name = "other_function"  # Wrong name
                self.arguments = '{"title": "Test"}'
        
        class MockToolCall:
            def __init__(self):
                self.function = MockFunction()
        
        class MockResponse:
            def __init__(self):
                self.tool_calls = [MockToolCall()]
                self.text = '{"title": "Text Task", "priority": "low"}'  # Fallback
        
        mock_response = MockResponse()
        
        # Should fall back to text parsing
        task_info = parse_task_info_from_response(mock_response)
        
        assert task_info.title == "Text Task"
        assert task_info.priority == "low"
    
    def test_parse_multiple_tool_calls(self):
        """Test parsing when multiple tool calls exist."""
        # First tool call (wrong function)
        mock_function1 = MagicMock()
        mock_function1.name = "other_function"
        mock_function1.arguments = '{"title": "Wrong"}'
        
        mock_tool_call1 = MagicMock()
        mock_tool_call1.function = mock_function1
        
        # Second tool call (correct function)
        mock_function2 = MagicMock()
        mock_function2.name = "create_task"
        mock_function2.arguments = '{"title": "Correct Task", "priority": "high"}'
        
        mock_tool_call2 = MagicMock()
        mock_tool_call2.function = mock_function2
        
        mock_response = MagicMock()
        mock_response.tool_calls = [mock_tool_call1, mock_tool_call2]
        
        # Should use the correct function call
        task_info = parse_task_info_from_response(mock_response)
        
        assert task_info.title == "Correct Task"
        assert task_info.priority == "high"


class TestFunctionCallingFallback:
    """Test fallback to text parsing when function calls not available."""
    
    def test_fallback_to_text_when_no_tool_calls(self):
        """Test fallback to text parsing when no tool_calls."""
        # Create a simple mock that has text attribute as string
        class MockResponse:
            def __init__(self):
                self.tool_calls = None
                self.text = '{"title": "Fallback Task", "priority": "medium"}'
        
        mock_response = MockResponse()
        
        task_info = parse_task_info_from_response(mock_response)
        
        assert task_info.title == "Fallback Task"
        assert task_info.priority == "medium"
    
    def test_fallback_to_string_response(self):
        """Test fallback to string response."""
        response = '{"title": "String Task", "priority": "low"}'
        
        task_info = parse_task_info_from_response(response)
        
        assert task_info.title == "String Task"
        assert task_info.priority == "low"


class TestFunctionCallingValidation:
    """Test validation of function call arguments."""
    
    def test_validate_priority_in_function_call(self):
        """Test that invalid priority in function call is caught."""
        mock_function = MagicMock()
        mock_function.name = "create_task"
        mock_function.arguments = '{"title": "Test", "priority": "invalid"}'
        
        mock_tool_call = MagicMock()
        mock_tool_call.function = mock_function
        
        mock_response = MagicMock()
        mock_response.tool_calls = [mock_tool_call]
        
        # Should raise validation error
        with pytest.raises(ValueError, match="Invalid priority"):
            parse_task_info_from_response(mock_response)
    
    def test_validate_title_length_in_function_call(self):
        """Test that title length validation works in function calls."""
        long_title = "x" * 501
        mock_function = MagicMock()
        mock_function.name = "create_task"
        mock_function.arguments = json.dumps({"title": long_title, "priority": "high"})
        
        mock_tool_call = MagicMock()
        mock_tool_call.function = mock_function
        
        mock_response = MagicMock()
        mock_response.tool_calls = [mock_tool_call]
        
        # Should raise validation error
        with pytest.raises(ValueError):
            parse_task_info_from_response(mock_response)
