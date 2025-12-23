"""Unit tests for workflow module."""
import pytest
from taskpilot.core.workflow import _is_approved


class TestWorkflow:
    """Test workflow functions."""
    
    def test_is_approved_string(self):
        """Test _is_approved with string input."""
        assert _is_approved("APPROVE") is True
        assert _is_approved("approve") is True
        assert _is_approved("This is APPROVE") is True
        assert _is_approved("REVIEW") is False
        assert _is_approved("REJECTED") is False
        assert _is_approved("This is review") is False
    
    def test_is_approved_with_text_attribute(self):
        """Test _is_approved with object having text attribute."""
        class MockResponse:
            def __init__(self, text):
                self.text = text
        
        assert _is_approved(MockResponse("APPROVE")) is True
        assert _is_approved(MockResponse("approve")) is True
        assert _is_approved(MockResponse("REVIEW")) is False
    
    def test_is_approved_with_agent_run_response(self):
        """Test _is_approved with AgentExecutorResponse-like object."""
        class MockAgentResponse:
            def __init__(self, text):
                self.text = text
        
        class MockResponse:
            def __init__(self, text):
                self.agent_run_response = MockAgentResponse(text)
        
        assert _is_approved(MockResponse("APPROVE")) is True
        assert _is_approved(MockResponse("REVIEW")) is False
    
    def test_is_approved_fallback(self):
        """Test _is_approved fallback to string conversion."""
        class MockObject:
            def __str__(self):
                return "APPROVE"
        
        assert _is_approved(MockObject()) is True
    
    def test_is_approved_with_messages(self):
        """Test _is_approved with agent_run_response.messages."""
        class MockContent:
            def __init__(self, text):
                self.text = text
        
        class MockMessage:
            def __init__(self, content):
                self.content = content
        
        class MockAgentResponse:
            def __init__(self, messages):
                self.messages = messages
        
        class MockResponse:
            def __init__(self, messages):
                self.agent_run_response = MockAgentResponse(messages)
        
        # Test with content.text
        messages = [MockMessage(MockContent("APPROVE"))]
        assert _is_approved(MockResponse(messages)) is True
        
        # Test with string content
        class MockStringContent:
            def __init__(self, content):
                self.content = content
        
        messages = [MockMessage(MockStringContent("APPROVE"))]
        assert _is_approved(MockResponse(messages)) is True
    
    def test_is_approved_with_data_attribute(self):
        """Test _is_approved with .data attribute."""
        class MockDataResponse:
            def __init__(self, data):
                self.data = data
        
        assert _is_approved(MockDataResponse("APPROVE")) is True
        assert _is_approved(MockDataResponse("REVIEW")) is False
        
        # Test with non-string data
        class MockNonStringData:
            def __str__(self):
                return "APPROVE"
        
        assert _is_approved(MockDataResponse(MockNonStringData())) is True
    
    def test_build_workflow(self):
        """Test workflow building."""
        from unittest.mock import MagicMock
        
        planner = MagicMock()
        reviewer = MagicMock()
        executor = MagicMock()
        
        from taskpilot.core.workflow import build_workflow
        
        workflow = build_workflow(planner, reviewer, executor)
        
        assert workflow is not None
    
    def test_is_approved_with_messages_content_text(self):
        """Test _is_approved with messages containing content.text."""
        class MockContent:
            def __init__(self, text):
                self.text = text
        
        class MockMessage:
            def __init__(self, content):
                self.content = content
        
        class MockAgentResponse:
            def __init__(self, messages):
                self.messages = messages
        
        class MockResponse:
            def __init__(self, messages):
                self.agent_run_response = MockAgentResponse(messages)
        
        messages = [MockMessage(MockContent("APPROVE"))]
        assert _is_approved(MockResponse(messages)) is True
    
    def test_is_approved_with_messages_string_content(self):
        """Test _is_approved with messages containing string content."""
        class MockMessage:
            def __init__(self, content):
                self.content = content
        
        class MockAgentResponse:
            def __init__(self, messages):
                self.messages = messages
        
        class MockResponse:
            def __init__(self, messages):
                self.agent_run_response = MockAgentResponse(messages)
        
        messages = [MockMessage("APPROVE")]
        assert _is_approved(MockResponse(messages)) is True
