"""Utilities for parsing structured output from agents."""
import json
import logging
import re
from typing import Any
from taskpilot.core.models import TaskInfo  # type: ignore

logger = logging.getLogger(__name__)


def parse_task_info_from_response(response: Any) -> TaskInfo:
    """Parse task info from agent response (function call preferred, text fallback).
    
    This is the PRIMARY method for parsing structured output. It prioritizes
    function calling responses (native structured output) and falls back to
    text parsing only when necessary.
    
    Args:
        response: Agent response (can be function call or text)
        
    Returns:
        TaskInfo instance with validated data
        
    Raises:
        ValueError: If parsing fails
    """
    # Strategy 1: Function calling response (PRIMARY - native structured output)
    # Check direct tool_calls attribute
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            if hasattr(tool_call, 'function') and tool_call.function.name == "create_task":
                try:
                    args = json.loads(tool_call.function.arguments)
                    logger.debug("Parsed task info from function call")
                    return TaskInfo(**args)  # ✅ Direct, validated, no parsing needed
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Failed to parse function call arguments: {e}")
                    raise ValueError(f"Invalid function call arguments: {e}") from e
    
    # Strategy 1b: Check for function call in messages (agent framework format)
    if hasattr(response, 'messages') and response.messages:
        for msg in reversed(response.messages):  # Check last messages first
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if hasattr(tool_call, 'function') and tool_call.function.name == "create_task":
                        try:
                            args = json.loads(tool_call.function.arguments)
                            logger.debug("Parsed task info from message tool_calls")
                            return TaskInfo(**args)
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.error(f"Failed to parse function call from messages: {e}")
                            continue
    
    # Strategy 2: Extract from agent_run_response if present
    if hasattr(response, 'agent_run_response'):
        agent_response = response.agent_run_response
        # Check for function calls in agent response
        if hasattr(agent_response, 'tool_calls') and agent_response.tool_calls:
            for tool_call in agent_response.tool_calls:
                if hasattr(tool_call, 'function') and tool_call.function.name == "create_task":
                    try:
                        args = json.loads(tool_call.function.arguments)
                        logger.debug("Parsed task info from agent_run_response function call")
                        return TaskInfo(**args)
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(f"Failed to parse function call from agent_run_response: {e}")
                        raise ValueError(f"Invalid function call arguments: {e}") from e
        # Fall back to text extraction
        if hasattr(agent_response, 'text'):
            logger.debug("Falling back to text parsing from agent_run_response")
            return parse_task_info_from_output(agent_response.text)
    
    # Strategy 3: Text response (fallback - for backward compatibility)
    if hasattr(response, 'text'):
        logger.debug("Parsing from text response (fallback)")
        return parse_task_info_from_output(response.text)
    
    # Strategy 4: String response (fallback)
    if isinstance(response, str):
        logger.debug("Parsing from string response (fallback)")
        return parse_task_info_from_output(response)
    
    # Strategy 5: Try to extract text from various response formats
    text = _extract_text_from_response(response)
    if text:
        logger.debug("Extracted text from response, parsing")
        return parse_task_info_from_output(text)
    
    raise ValueError(f"Could not parse task info from response: {type(response)}")


def _extract_text_from_response(response: Any) -> str:
    """Extract text from various response formats."""
    if isinstance(response, str):
        return response
    
    if hasattr(response, 'text'):
        return response.text
    
    if hasattr(response, 'content'):
        if isinstance(response.content, str):
            return response.content
        if hasattr(response.content, 'text'):
            return response.content.text
    
    if hasattr(response, 'message'):
        return _extract_text_from_response(response.message)
    
    return str(response)


def parse_task_info_from_output(output: str) -> TaskInfo:
    """Parse structured task information from agent output text (fallback only).
    
    This function is used as a fallback when function calling is not available.
    It attempts multiple parsing strategies for text-based output:
    1. Direct JSON parsing (if output is pure JSON)
    2. JSON code block extraction (if wrapped in ```json ... ```)
    3. JSON embedded in text
    4. Legacy regex parsing (for backward compatibility)
    
    Note: For production use, prefer function calling which guarantees structured output.
    This text-based parsing is kept for backward compatibility.
    
    Args:
        output: Agent output text
        
    Returns:
        TaskInfo instance with validated data
        
    Raises:
        ValueError: If parsing fails and no fallback works
    """
    # Strategy 1: Try direct JSON parsing
    try:
        data = json.loads(output.strip())
        if isinstance(data, dict):
            logger.debug("Parsed JSON directly from output")
            return TaskInfo(**data)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Strategy 2: Extract JSON from code blocks
    try:
        json_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        matches = re.findall(json_block_pattern, output, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            try:
                data = json.loads(match.strip())
                if isinstance(data, dict):
                    logger.debug("Parsed JSON from code block")
                    return TaskInfo(**data)
            except (json.JSONDecodeError, ValueError):
                continue
    except Exception:
        pass
    
    # Strategy 3: Try to find JSON object in text
    try:
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, output, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and 'title' in data:
                    logger.debug("Parsed JSON embedded in text")
                    return TaskInfo(**data)
            except (json.JSONDecodeError, ValueError):
                continue
    except Exception:
        pass
    
    # Strategy 4: Fallback to legacy regex parsing (for backward compatibility)
    # Only warn if we're actually in a context where function calling should work
    # (i.e., not for reviewer/executor agents that use text responses)
    logger.debug(
        "Could not parse structured JSON from text, falling back to regex parsing. "
        "Consider using function calling for guaranteed structured output."
    )
    return _parse_task_info_legacy(output)


def _parse_task_info_legacy(output: str) -> TaskInfo:
    """Legacy regex-based parsing (fallback only).
    
    This is kept for backward compatibility but should be replaced
    with structured output in production.
    
    Args:
        output: Agent output text
        
    Returns:
        TaskInfo instance
    """
    title = ""
    priority = "medium"
    description = ""
    
    # Try to extract structured format
    title_match = re.search(r'\*\*Task Title:\*\*\s*(.+?)(?:\n|$)', output, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
    
    priority_match = re.search(r'\*\*Priority:\*\*\s*(.+?)(?:\n|$)', output, re.IGNORECASE)
    if priority_match:
        priority = priority_match.group(1).strip().lower()
    
    desc_match = re.search(r'\*\*Description:\*\*\s*(.+?)(?:\n\n|\Z)', output, re.IGNORECASE | re.DOTALL)
    if desc_match:
        description = desc_match.group(1).strip()
    
    # Fallback: use first line as title
    if not title:
        lines = output.split('\n')
        title = lines[0].strip() if lines else output[:50]
        description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
    
    # Create TaskInfo with validation
    try:
        return TaskInfo(title=title, priority=priority, description=description)
    except ValueError as e:
        # If validation fails, use defaults
        logger.error(f"Legacy parsing validation failed: {e}, using defaults")
        return TaskInfo(
            title=title[:500] if title else "Untitled Task",
            priority="medium",
            description=description[:10000] if description else ""
        )


