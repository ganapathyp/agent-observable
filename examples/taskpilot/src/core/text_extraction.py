"""Text extraction utilities for agent responses.

This module provides reusable functions to extract text from various
agent framework response types (AgentRunResponse, messages, async generators, etc.).
"""
from __future__ import annotations

import logging
from typing import Any
from agent_framework import TextContent  # type: ignore

logger = logging.getLogger(__name__)


def extract_text_from_content(content: Any) -> str:
    """Extract text from various content types.
    
    Args:
        content: Content object (str, TextContent, or object with .text attribute)
        
    Returns:
        Extracted text string, or empty string if extraction fails
    """
    if isinstance(content, str):
        return content
    if isinstance(content, TextContent):
        return content.text
    if hasattr(content, 'text'):
        return str(content.text)
    return str(content)


def extract_text_from_messages(messages: list[Any]) -> str:
    """Extract text from message list, prioritizing user messages.
    
    Args:
        messages: List of message objects
        
    Returns:
        Extracted text string, or empty string if no messages
    """
    if not messages:
        return ""
    
    # Look for user messages first (most recent)
    for msg in reversed(messages):
        if hasattr(msg, 'role') and msg.role == 'user':
            if hasattr(msg, 'content'):
                return extract_text_from_content(msg.content)
            if hasattr(msg, 'text'):
                return msg.text
    
    # Fallback: get text from last message
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, 'content'):
            return extract_text_from_content(last_msg.content)
        if hasattr(last_msg, 'text'):
            return last_msg.text
    
    return ""


def extract_text_from_result(result: Any) -> str:
    """Extract text from agent run result.
    
    Handles various result types:
    - Async generators (skipped)
    - AgentRunResponse objects
    - Event objects with .data attribute
    - Objects with .text attribute
    - String representations
    
    Args:
        result: Agent execution result (various types)
        
    Returns:
        Extracted text string, or empty string if extraction fails
    """
    if not result:
        return ""
    
    # Skip async generators and similar objects
    if hasattr(result, '__class__'):
        class_name = result.__class__.__name__
        if 'async_generator' in class_name.lower() or 'generator' in class_name.lower():
            logger.debug(f"Skipping {class_name} object in result extraction")
            return ""
    
    # Check for event objects with data attribute (AgentRunEvent, etc.)
    if hasattr(result, 'data'):
        data = result.data
        if isinstance(data, str):
            return data
        # If data is not a string, try to extract from it recursively
        if data:
            return extract_text_from_result(data)
    
    # Direct text attribute
    if hasattr(result, 'text'):
        text = result.text
        if text and isinstance(text, str):
            return text
    
    # AgentRunResponse with text
    if hasattr(result, 'agent_run_response'):
        agent_response = result.agent_run_response
        if hasattr(agent_response, 'text'):
            text = agent_response.text
            if text and isinstance(text, str):
                return text
        if hasattr(agent_response, 'messages') and agent_response.messages:
            last_msg = agent_response.messages[-1]
            if hasattr(last_msg, 'content'):
                return extract_text_from_content(last_msg.content)
            if hasattr(last_msg, 'text'):
                return last_msg.text
    
    # Messages in result
    if hasattr(result, 'messages') and result.messages:
        last_msg = result.messages[-1]
        if hasattr(last_msg, 'content'):
            return extract_text_from_content(last_msg.content)
        if hasattr(last_msg, 'text'):
            return last_msg.text
    
    # String representation (last resort, but only if it looks like text)
    result_str = str(result)
    if result_str and len(result_str) < 1000 and not result_str.startswith('<'):
        return result_str
    
    return ""


def extract_text_from_context(context: Any, is_async_gen: bool = False) -> str:
    """Extract text from agent run context.
    
    This is a comprehensive extraction function that handles:
    - Async generators (must check context.messages)
    - AgentRunResponse objects
    - Event objects
    - Direct text attributes
    - Message lists
    
    Args:
        context: AgentRunContext object
        is_async_gen: Whether context.result is an async generator
        
    Returns:
        Extracted text string, or empty string if extraction fails
    """
    output_text = ""
    
    # Primary: Check context.result.agent_run_response.text (if not async generator)
    if not is_async_gen and hasattr(context.result, 'agent_run_response'):
        agent_response = context.result.agent_run_response
        if hasattr(agent_response, 'text') and agent_response.text:
            output_text = agent_response.text
        elif hasattr(agent_response, 'messages') and agent_response.messages:
            # Get the last message from agent_run_response (this is the agent's actual output)
            last_msg = agent_response.messages[-1]
            if hasattr(last_msg, 'content'):
                content = last_msg.content
                if isinstance(content, str):
                    output_text = content
                elif hasattr(content, 'text'):
                    output_text = content.text
                else:
                    output_text = extract_text_from_content(content)
    
    # Check if result has a 'data' attribute (like AgentRunEvent) - works even with async gen
    if not output_text and hasattr(context.result, 'data'):
        data = context.result.data
        if isinstance(data, str):
            output_text = data
        elif data:
            # Try to extract from data object
            output_text = extract_text_from_result(data)
    
    # IMPORTANT: For async generators, context.messages is the most reliable source
    # The agent's response is added to context.messages during execution
    if not output_text and hasattr(context, 'messages') and context.messages:
        # Get the LAST assistant message (should be this agent's response)
        assistant_messages = []
        for msg in context.messages:
            msg_role = getattr(msg, 'role', None)
            role_str = str(msg_role).lower() if msg_role else ''
            if role_str == 'assistant' or (hasattr(msg_role, 'value') and msg_role.value == 'assistant'):
                assistant_messages.append(msg)
        
        # Use the last assistant message (most recent response)
        if assistant_messages:
            last_assistant = assistant_messages[-1]
            if hasattr(last_assistant, 'content'):
                content_text = extract_text_from_content(last_assistant.content)
                if content_text:
                    output_text = content_text
            elif hasattr(last_assistant, 'text'):
                output_text = last_assistant.text
    
    # Fallback: Check if result itself is a string
    if not output_text and isinstance(context.result, str):
        output_text = context.result
    
    # Fallback: Check if context.result itself has text
    if not output_text and not is_async_gen and hasattr(context.result, 'text'):
        output_text = context.result.text or ""
    
    # Final fallback: Use the helper function (skips async generators)
    if not output_text and not is_async_gen:
        output_text = extract_text_from_result(context.result)
    
    return output_text


def is_async_generator(obj: Any) -> bool:
    """Check if an object is an async generator.
    
    Args:
        obj: Object to check
        
    Returns:
        True if object is an async generator, False otherwise
    """
    if hasattr(obj, '__class__'):
        class_name = obj.__class__.__name__
        return 'async_generator' in class_name.lower() or 'generator' in class_name.lower()
    return False
