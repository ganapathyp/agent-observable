"""Generic structured output parsing utilities (framework-agnostic).

Provides generic parsing patterns that work across all frameworks:
- MS Agent Framework
- LangGraph
- OpenAI custom routing

Project-specific model parsing should stay in the project.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)


def extract_text_from_response(response: Any) -> str:
    """Extract text from various response formats (framework-agnostic).
    
    Works with:
    - MS Agent Framework responses
    - LangGraph responses
    - OpenAI direct responses
    - Custom routing responses
    
    Args:
        response: Response object from any framework
        
    Returns:
        Extracted text or empty string
    """
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
        return extract_text_from_response(response.message)
    
    if hasattr(response, 'agent_run_response'):
        agent_response = response.agent_run_response
        if hasattr(agent_response, 'text'):
            return agent_response.text
        if hasattr(agent_response, 'messages') and agent_response.messages:
            last_msg = agent_response.messages[-1]
            if hasattr(last_msg, 'content'):
                content = last_msg.content
                if isinstance(content, str):
                    return content
                if hasattr(content, 'text'):
                    return content.text
    
    if hasattr(response, 'messages') and response.messages:
        last_msg = response.messages[-1]
        if hasattr(last_msg, 'content'):
            content = last_msg.content
            if isinstance(content, str):
                return content
            if hasattr(content, 'text'):
                return content.text
    
    return str(response)


def extract_function_call_arguments(
    response: Any,
    function_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Extract function call arguments from response (framework-agnostic).
    
    Works with:
    - MS Agent Framework function calls
    - LangGraph function calls
    - OpenAI function calls
    
    Args:
        response: Response object from any framework
        function_name: Optional function name to filter by
        
    Returns:
        Dict with function arguments or None if not found
    """
    # Strategy 1: Direct tool_calls attribute
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            if hasattr(tool_call, 'function'):
                func_name = getattr(tool_call.function, 'name', '')
                if function_name is None or func_name == function_name:
                    try:
                        args_str = getattr(tool_call.function, 'arguments', '{}')
                        if isinstance(args_str, str):
                            return json.loads(args_str)
                        return args_str
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.debug(f"Failed to parse function call arguments: {e}")
                        continue
    
    # Strategy 2: Check messages for tool_calls
    if hasattr(response, 'messages') and response.messages:
        for msg in reversed(response.messages):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if hasattr(tool_call, 'function'):
                        func_name = getattr(tool_call.function, 'name', '')
                        if function_name is None or func_name == function_name:
                            try:
                                args_str = getattr(tool_call.function, 'arguments', '{}')
                                if isinstance(args_str, str):
                                    return json.loads(args_str)
                                return args_str
                            except (json.JSONDecodeError, ValueError) as e:
                                logger.debug(f"Failed to parse function call from messages: {e}")
                                continue
    
    # Strategy 3: Check agent_run_response
    if hasattr(response, 'agent_run_response'):
        agent_response = response.agent_run_response
        if hasattr(agent_response, 'tool_calls') and agent_response.tool_calls:
            for tool_call in agent_response.tool_calls:
                if hasattr(tool_call, 'function'):
                    func_name = getattr(tool_call.function, 'name', '')
                    if function_name is None or func_name == function_name:
                        try:
                            args_str = getattr(tool_call.function, 'arguments', '{}')
                            if isinstance(args_str, str):
                                return json.loads(args_str)
                            return args_str
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.debug(f"Failed to parse function call from agent_run_response: {e}")
                            continue
    
    return None


def parse_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from text using multiple strategies (framework-agnostic).
    
    Strategies:
    1. Direct JSON parsing
    2. JSON code block extraction (```json ... ```)
    3. JSON embedded in text
    
    Args:
        text: Text containing JSON
        
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    if not text:
        return None
    
    # Strategy 1: Try direct JSON parsing
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict):
            logger.debug("Parsed JSON directly from text")
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Strategy 2: Extract JSON from code blocks
    try:
        json_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        matches = re.findall(json_block_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            try:
                data = json.loads(match.strip())
                if isinstance(data, dict):
                    logger.debug("Parsed JSON from code block")
                    return data
            except (json.JSONDecodeError, ValueError):
                continue
    except Exception:
        pass
    
    # Strategy 3: Try to find JSON object in text
    try:
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict):
                    logger.debug("Parsed JSON embedded in text")
                    return data
            except (json.JSONDecodeError, ValueError):
                continue
    except Exception:
        pass
    
    return None


__all__ = [
    "extract_text_from_response",
    "extract_function_call_arguments",
    "parse_json_from_text",
]
