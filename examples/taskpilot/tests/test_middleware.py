"""Unit tests for middleware module."""
import pytest
from taskpilot.core.middleware import (
    _extract_text_from_content,
    _extract_text_from_messages,
    _extract_text_from_result,
    _parse_task_from_planner,
)


class TestMiddlewareHelpers:
    """Test middleware helper functions."""
    
    def test_extract_text_from_content_string(self):
        """Test extracting text from string content."""
        assert _extract_text_from_content("test") == "test"
    
    def test_extract_text_from_content_textcontent(self):
        """Test extracting text from TextContent object."""
        class MockTextContent:
            def __init__(self, text):
                self.text = text
        
        content = MockTextContent("test text")
        assert _extract_text_from_content(content) == "test text"
    
    def test_extract_text_from_messages_empty(self):
        """Test extracting text from empty messages."""
        assert _extract_text_from_messages([]) == ""
    
    def test_extract_text_from_messages_with_user(self):
        """Test extracting text from messages with user message."""
        class MockMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content
        
        messages = [
            MockMessage("assistant", "response"),
            MockMessage("user", "user input")
        ]
        
        assert _extract_text_from_messages(messages) == "user input"
    
    def test_parse_task_from_planner_structured(self):
        """Test parsing structured planner output."""
        output = """**Task Title:** Test Task
**Priority:** high
**Description:** This is a test task"""
        
        title, priority, description = _parse_task_from_planner(output)
        
        assert title == "Test Task"
        assert priority == "high"
        assert "test task" in description.lower()
    
    def test_parse_task_from_planner_fallback(self):
        """Test parsing planner output with fallback."""
        output = "Simple task description"
        
        title, priority, description = _parse_task_from_planner(output)
        
        assert title is not None
        assert len(title) > 0
        assert priority == "medium"  # default
    
    def test_extract_text_from_content_with_text_attr(self):
        """Test extracting text from object with text attribute."""
        class MockContent:
            def __init__(self, text):
                self.text = text
        
        content = MockContent("test text")
        assert _extract_text_from_content(content) == "test text"
    
    def test_extract_text_from_result_with_messages(self):
        """Test extracting text from result with messages."""
        class MockMessage:
            def __init__(self, content):
                self.content = content
        
        class MockResult:
            def __init__(self, messages):
                self.messages = messages
        
        # Test with string content
        result = MockResult([MockMessage("result text")])
        assert _extract_text_from_result(result) == "result text"
    
    def test_extract_text_from_result_with_text_message(self):
        """Test extracting text from result message with text attribute."""
        class MockMessage:
            def __init__(self, text):
                self.text = text
        
        class MockResult:
            def __init__(self, messages):
                self.messages = messages
        
        result = MockResult([MockMessage("message text")])
        assert _extract_text_from_result(result) == "message text"
    
    def test_parse_task_from_planner_with_description(self):
        """Test parsing planner output with description."""
        output = """**Task Title:** Test Task
**Priority:** high
**Description:** This is a detailed description
with multiple lines"""
        
        title, priority, description = _parse_task_from_planner(output)
        
        assert title == "Test Task"
        assert priority == "high"
        assert "detailed description" in description
    
    def test_parse_task_from_planner_multiline_fallback(self):
        """Test parsing planner output with multiline fallback."""
        output = "First line\nSecond line\nThird line"
        
        title, priority, description = _parse_task_from_planner(output)
        
        assert title == "First line"
        assert "Second line" in description or "Third line" in description
    
    def test_extract_text_from_content_textcontent_import(self):
        """Test extracting text from TextContent type."""
        from agent_framework import TextContent  # type: ignore
        
        content = TextContent("test text")
        result = _extract_text_from_content(content)
        assert result == "test text"
    
    def test_extract_text_from_messages_with_text_attr(self):
        """Test extracting text from message with text attribute."""
        class MockMessage:
            def __init__(self, text):
                self.text = text
        
        messages = [MockMessage("message text")]
        text = _extract_text_from_messages(messages)
        assert text == "message text"
    
    def test_extract_text_from_messages_fallback_last_message(self):
        """Test fallback to last message when no user message."""
        class MockMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content
        
        messages = [
            MockMessage("system", "system message"),
            MockMessage("assistant", "assistant message")
        ]
        text = _extract_text_from_messages(messages)
        assert text == "assistant message"
    
    def test_extract_text_from_messages_no_user_message(self):
        """Test extracting text when no user message."""
        class MockMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content
        
        messages = [MockMessage("assistant", "response")]
        text = _extract_text_from_messages(messages)
        
        assert text == "response"
    
    def test_extract_text_from_messages_with_content_text(self):
        """Test extracting text from message with TextContent."""
        from taskpilot.core.middleware import TextContent
        
        class MockMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content
        
        content = TextContent("test text")
        messages = [MockMessage("user", content)]
        text = _extract_text_from_messages(messages)
        
        assert text == "test text"
