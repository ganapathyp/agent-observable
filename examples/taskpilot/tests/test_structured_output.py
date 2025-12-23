"""Tests for structured output parsing (text-based fallback)."""
import pytest
from taskpilot.core.structured_output import parse_task_info_from_output, parse_task_info_from_response
from taskpilot.core.models import TaskInfo


class TestStructuredOutput:
    """Test structured output parsing."""
    
    def test_parse_direct_json(self):
        """Test parsing direct JSON output."""
        output = '{"title": "Test Task", "priority": "high", "description": "Test description"}'
        task_info = parse_task_info_from_output(output)
        
        assert task_info.title == "Test Task"
        assert task_info.priority == "high"
        assert task_info.description == "Test description"
    
    def test_parse_json_code_block(self):
        """Test parsing JSON from code block."""
        output = """Here's the task:
```json
{
  "title": "Test Task",
  "priority": "medium",
  "description": "Test description"
}
```"""
        task_info = parse_task_info_from_output(output)
        
        assert task_info.title == "Test Task"
        assert task_info.priority == "medium"
        assert task_info.description == "Test description"
    
    def test_parse_json_in_text(self):
        """Test parsing JSON object embedded in text."""
        output = """I'll create this task: {"title": "Test Task", "priority": "low"} for you."""
        task_info = parse_task_info_from_output(output)
        
        assert task_info.title == "Test Task"
        assert task_info.priority == "low"
    
    def test_parse_legacy_format(self):
        """Test fallback to legacy format parsing."""
        output = """**Task Title:** Test Task
**Priority:** high
**Description:** Test description"""
        task_info = parse_task_info_from_output(output)
        
        assert task_info.title == "Test Task"
        assert task_info.priority == "high"
        assert "description" in task_info.description.lower()
    
    def test_validation_priority(self):
        """Test priority validation."""
        output = '{"title": "Test", "priority": "invalid"}'
        
        # Should fall back to legacy parsing or use default
        task_info = parse_task_info_from_output(output)
        # Legacy parser might use "invalid", but validation should catch it
        assert task_info.priority in ["high", "medium", "low"]
    
    def test_validation_title_length(self):
        """Test title length validation."""
        long_title = "x" * 600
        output = f'{{"title": "{long_title}", "priority": "high"}}'
        
        task_info = parse_task_info_from_output(output)
        # Should be truncated or validated
        assert len(task_info.title) <= 500
    
    def test_minimal_json(self):
        """Test parsing minimal JSON with only title."""
        output = '{"title": "Minimal Task"}'
        task_info = parse_task_info_from_output(output)
        
        assert task_info.title == "Minimal Task"
        assert task_info.priority == "medium"  # default
        assert task_info.description == ""  # default


class TestTaskInfoModel:
    """Test TaskInfo Pydantic model."""
    
    def test_create_task_info(self):
        """Test creating TaskInfo instance."""
        task_info = TaskInfo(
            title="Test Task",
            priority="high",
            description="Test description"
        )
        
        assert task_info.title == "Test Task"
        assert task_info.priority == "high"
        assert task_info.description == "Test description"
    
    def test_priority_validation(self):
        """Test priority validation."""
        task_info = TaskInfo(title="Test", priority="HIGH")
        assert task_info.priority == "high"  # Normalized to lowercase
    
    def test_priority_invalid(self):
        """Test invalid priority raises error."""
        with pytest.raises(ValueError, match="Invalid priority"):
            TaskInfo(title="Test", priority="invalid")
    
    def test_title_validation(self):
        """Test title validation."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            TaskInfo(title="", priority="high")
    
    def test_title_too_long(self):
        """Test title length validation."""
        from pydantic import ValidationError
        long_title = "x" * 501
        with pytest.raises(ValidationError):
            TaskInfo(title=long_title, priority="high")
    
    def test_from_json(self):
        """Test parsing from JSON string."""
        json_str = '{"title": "Test", "priority": "high", "description": "Test"}'
        task_info = TaskInfo.from_json(json_str)
        
        assert task_info.title == "Test"
        assert task_info.priority == "high"
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        task_info = TaskInfo(title="Test", priority="high", description="Desc")
        data = task_info.to_dict()
        
        assert data["title"] == "Test"
        assert data["priority"] == "high"
        assert data["description"] == "Desc"
