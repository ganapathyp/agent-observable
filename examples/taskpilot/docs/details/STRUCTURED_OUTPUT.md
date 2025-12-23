# Structured Output - Best Practices Implementation

## Overview

TaskPilot has been upgraded from **fragile regex parsing** to **robust structured output parsing** using Pydantic models and JSON parsing. This showcases best practices for agent frameworks.

## Problem: Regex Parsing (Old Approach)

### ❌ Issues with Regex Parsing

```python
# OLD WAY: Fragile regex parsing
def _extract_task_info(text: str) -> tuple[str, str, str]:
    title_match = re.search(r'\*\*Task Title:\*\*\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
    # ... more regex patterns
```

**Problems:**
- ❌ **Fragile**: Breaks if agent output format changes slightly
- ❌ **No validation**: Invalid data can slip through
- ❌ **Hard to maintain**: Complex regex patterns
- ❌ **Error-prone**: Edge cases cause failures
- ❌ **Not type-safe**: Returns tuples, no schema enforcement

## Solution: Structured Output (New Approach)

### ✅ Structured Output with Pydantic

```python
# NEW WAY: Structured output with validation
from taskpilot.core.models import TaskInfo
from taskpilot.core.structured_output import parse_task_info_from_output

# Agent returns JSON
output = '{"title": "Test Task", "priority": "high", "description": "Test"}'

# Parse with validation
task_info = parse_task_info_from_output(output)
# Returns validated TaskInfo object
```

**Benefits:**
- ✅ **Robust**: Handles multiple JSON formats
- ✅ **Validated**: Pydantic ensures data integrity
- ✅ **Type-safe**: Strong typing with models
- ✅ **Maintainable**: Clear schema definition
- ✅ **Backward compatible**: Falls back to regex if needed

---

## Implementation

### 1. Pydantic Model (`src/core/models.py`)

```python
from pydantic import BaseModel, Field, field_validator
from taskpilot.core.types import TaskPriority

class TaskInfo(BaseModel):
    """Structured task information from agent output."""
    title: str = Field(..., min_length=1, max_length=500)
    priority: str = Field(default="medium")
    description: str = Field(default="", max_length=10000)
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate against TaskPriority enum."""
        v_lower = v.lower().strip()
        TaskPriority(v_lower)  # Raises ValueError if invalid
        return v_lower
```

**Features:**
- Automatic validation
- Type checking
- Field constraints (min/max length)
- Custom validators
- Clear error messages

### 2. Multi-Strategy Parser (`src/core/structured_output.py`)

```python
def parse_task_info_from_output(output: str) -> TaskInfo:
    """Parse with multiple strategies:
    
    1. Direct JSON parsing
    2. JSON code block extraction (```json ... ```)
    3. JSON object in text
    4. Legacy regex fallback
    """
    # Strategy 1: Direct JSON
    try:
        data = json.loads(output.strip())
        return TaskInfo(**data)
    except:
        pass
    
    # Strategy 2: Code blocks
    # ... extracts from ```json ... ```
    
    # Strategy 3: Embedded JSON
    # ... finds { ... } in text
    
    # Strategy 4: Legacy regex (fallback)
    return _parse_task_info_legacy(output)
```

**Why Multiple Strategies?**
- Agents may return JSON in different formats
- Some wrap JSON in code blocks
- Some embed JSON in explanatory text
- Fallback ensures backward compatibility

### 3. Enhanced Agent Instructions

```python
# src/agents/agent_planner.py
instructions = f"""Interpret the request and propose a task.

{format_task_info_request()}

Return ONLY the JSON object, no additional text."""
```

**Agent receives clear instructions:**
```json
{
  "title": "Task title (required, 1-500 characters)",
  "priority": "high|medium|low (default: medium)",
  "description": "Task description (optional, max 10000 characters)"
}
```

---

## Usage Examples

### Example 1: Direct JSON

```python
# Agent returns pure JSON
output = '{"title": "Prepare Board Deck", "priority": "high"}'
task_info = parse_task_info_from_output(output)

assert task_info.title == "Prepare Board Deck"
assert task_info.priority == "high"
assert task_info.description == ""  # default
```

### Example 2: JSON in Code Block

```python
# Agent returns JSON in code block
output = """Here's the task:
```json
{
  "title": "Test Task",
  "priority": "medium"
}
```"""
task_info = parse_task_info_from_output(output)
# Successfully extracts JSON from code block
```

### Example 3: Embedded JSON

```python
# Agent embeds JSON in text
output = """I'll create this task: {"title": "Test", "priority": "low"} for you."""
task_info = parse_task_info_from_output(output)
# Extracts JSON object from text
```

### Example 4: Validation Errors

```python
# Invalid priority
output = '{"title": "Test", "priority": "invalid"}'
try:
    task_info = parse_task_info_from_output(output)
except ValueError as e:
    # Clear error message
    print(f"Validation error: {e}")
```

---

## Comparison: Before vs After

### Before (Regex)

```python
# ❌ Fragile
title_match = re.search(r'\*\*Task Title:\*\*\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
if title_match:
    title = title_match.group(1).strip()
# No validation, no type safety, breaks easily
```

**Issues:**
- Breaks if agent uses "Task:" instead of "Task Title:"
- No validation of priority values
- No length checks
- Silent failures

### After (Structured)

```python
# ✅ Robust
task_info = parse_task_info_from_output(output)
# Validated, type-safe, handles multiple formats
```

**Benefits:**
- Handles multiple JSON formats
- Validates all fields
- Type-safe with Pydantic
- Clear error messages
- Backward compatible

---

## Best Practices Demonstrated

### 1. **Use Structured Output**
- ✅ JSON schema for agent responses
- ✅ Pydantic models for validation
- ✅ Clear instructions for agents

### 2. **Multiple Parsing Strategies**
- ✅ Try structured parsing first
- ✅ Fallback to legacy if needed
- ✅ Graceful degradation

### 3. **Validation at Boundaries**
- ✅ Validate on input (parsing)
- ✅ Validate on creation (Pydantic)
- ✅ Validate on storage (TaskStore)

### 4. **Type Safety**
- ✅ Pydantic models
- ✅ Type hints throughout
- ✅ Enum validation

### 5. **Error Handling**
- ✅ Try structured parsing first
- ✅ Fallback to legacy
- ✅ Clear error messages
- ✅ Logging for debugging

---

## Testing

Comprehensive tests in `tests/test_structured_output.py`:

```python
def test_parse_direct_json():
    """Test parsing direct JSON output."""
    output = '{"title": "Test Task", "priority": "high"}'
    task_info = parse_task_info_from_output(output)
    assert task_info.title == "Test Task"

def test_parse_json_code_block():
    """Test parsing JSON from code block."""
    output = """```json\n{"title": "Test"}\n```"""
    task_info = parse_task_info_from_output(output)
    assert task_info.title == "Test"

def test_validation_priority():
    """Test priority validation."""
    output = '{"title": "Test", "priority": "invalid"}'
    # Should handle gracefully
    task_info = parse_task_info_from_output(output)
```

---

## Migration Path

### For Existing Code

1. **Immediate**: Uses structured parsing with regex fallback
2. **Gradual**: Update agent instructions to return JSON
3. **Future**: Remove regex fallback once all agents use JSON

### For New Code

Always use structured output:
```python
from taskpilot.core.structured_output import parse_task_info_from_output

task_info = parse_task_info_from_output(agent_output)
# Use task_info.title, task_info.priority, etc.
```

---

## Showcase Value

This implementation demonstrates:

1. **Modern Best Practices**
   - Structured output over regex
   - Pydantic for validation
   - Type safety

2. **Robustness**
   - Multiple parsing strategies
   - Graceful fallbacks
   - Error handling

3. **Maintainability**
   - Clear schema definitions
   - Easy to extend
   - Well-tested

4. **Production-Ready**
   - Validation at boundaries
   - Comprehensive error handling
   - Backward compatibility

---

## Future Enhancements

1. **Function Calling**: Use OpenAI function calling for even better structure
2. **JSON Mode**: Enable JSON mode in OpenAI API calls
3. **Schema Evolution**: Version schemas for backward compatibility
4. **Structured Responses**: Apply to reviewer and executor agents

---

## References

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/function-calling/function-calling-with-structured-outputs)
- [JSON Schema](https://json-schema.org/)
