"""Pydantic models for structured data validation."""
import json
from pydantic import BaseModel, Field, field_validator
from taskpilot.core.types import TaskPriority  # type: ignore


class TaskInfo(BaseModel):
    """Structured task information from agent output.
    
    This model ensures agents return properly structured data
    instead of free-form text that requires regex parsing.
    """
    title: str = Field(
        ...,
        description="Task title",
        min_length=1,
        max_length=500
    )
    priority: str = Field(
        default="medium",
        description="Task priority: high, medium, or low"
    )
    description: str = Field(
        default="",
        description="Detailed task description",
        max_length=10000
    )
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate and normalize priority."""
        v_lower = v.lower().strip()
        try:
            # Validate against enum
            TaskPriority(v_lower)
            return v_lower
        except ValueError:
            raise ValueError(
                f"Invalid priority: {v}. Must be one of: "
                f"{', '.join(p.value for p in TaskPriority)}"
            )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate and sanitize title."""
        v = v.strip()
        if not v:
            raise ValueError("Task title cannot be empty")
        if len(v) > 500:
            raise ValueError("Task title cannot exceed 500 characters")
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate and sanitize description."""
        if not v:
            return ""
        v = v.strip()
        if len(v) > 10000:
            raise ValueError("Task description cannot exceed 10000 characters")
        return v
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "priority": self.priority,
            "description": self.description
        }
    
    @classmethod
    def from_json(cls, json_str: str) -> "TaskInfo":
        """Parse from JSON string.
        
        Args:
            json_str: JSON string containing task info
            
        Returns:
            TaskInfo instance
            
        Raises:
            ValueError: If JSON is invalid or doesn't match schema
        """
        try:
            data = json.loads(json_str)
            return cls(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e
        except Exception as e:
            raise ValueError(f"Invalid task info: {e}") from e
    
    @classmethod
    def get_json_schema(cls) -> dict:
        """Generate JSON Schema for OpenAI function calling or response format.
        
        This schema can be used with:
        - Function calling (tools parameter)
        - Response format with json_schema (GPT-4o models)
        
        Returns:
            JSON Schema dictionary compatible with OpenAI API
        """
        # OpenAI function calling with strict mode requires:
        # 1. All properties must be listed
        # 2. ALL properties MUST be in 'required' array (strict mode requirement)
        # 3. Optional fields can accept empty strings or be marked as nullable
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 500,
                    "description": "Task title (required, 1-500 characters)"
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Task priority: high, medium, or low"
                },
                "description": {
                    "type": "string",
                    "maxLength": 10000,
                    "description": "Task description (can be empty string, max 10000 characters)"
                }
            },
            "required": ["title", "priority", "description"],
            "additionalProperties": False
        }
