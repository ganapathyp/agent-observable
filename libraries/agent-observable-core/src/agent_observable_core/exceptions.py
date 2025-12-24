"""Exception hierarchy with error codes for structured error handling (framework-agnostic).

This module provides a comprehensive exception hierarchy with error codes
for better debugging, user experience, and observability.

Works across all frameworks: MS Agent Framework, LangGraph, OpenAI routing.

Error Code Format: {CATEGORY}{NUMBER}
- AGENT_XXX: Agent-related errors (001-099)
- TOOL_XXX: Tool execution errors (100-199)
- VALIDATION_XXX: Validation errors (200-299)
- POLICY_XXX: Policy/guardrails errors (300-399)
- LLM_XXX: LLM API errors (400-499)
- SYSTEM_XXX: System/infrastructure errors (500-599)
"""
from __future__ import annotations

from typing import Optional, Dict, Any


class BaseAgentException(Exception):
    """Base exception for all agent framework errors.
    
    All exceptions in this hierarchy include:
    - error_code: Structured error code (e.g., "AGENT_001")
    - user_message: User-friendly error message
    - details: Additional context for debugging
    """
    
    def __init__(
        self,
        error_code: str,
        message: str,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.user_message = user_message or message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


# ============================================================================
# Agent Errors (AGENT_001 - AGENT_099)
# ============================================================================

class AgentException(BaseAgentException):
    """Base class for agent-specific errors."""
    pass


class AgentExecutionError(AgentException):
    """Agent execution failed."""
    
    def __init__(self, agent_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="AGENT_001",
            message=f"Agent {agent_name} execution failed: {reason}",
            user_message="Agent execution failed. Please try again.",
            details={"agent_name": agent_name, "reason": reason, **(details or {})}
        )


class AgentTimeoutError(AgentException):
    """Agent execution timed out."""
    
    def __init__(self, agent_name: str, timeout_seconds: float, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="AGENT_002",
            message=f"Agent {agent_name} execution timed out after {timeout_seconds}s",
            user_message="Request took too long to process. Please try again.",
            details={"agent_name": agent_name, "timeout_seconds": timeout_seconds, **(details or {})}
        )


class AgentConfigurationError(AgentException):
    """Agent configuration is invalid."""
    
    def __init__(self, agent_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="AGENT_003",
            message=f"Agent {agent_name} configuration error: {reason}",
            user_message="Configuration error. Please contact support.",
            details={"agent_name": agent_name, "reason": reason, **(details or {})}
        )


# ============================================================================
# Tool Errors (TOOL_100 - TOOL_199)
# ============================================================================

class ToolException(BaseAgentException):
    """Base class for tool-specific errors."""
    pass


class ToolExecutionError(ToolException):
    """Tool execution failed."""
    
    def __init__(self, tool_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="TOOL_100",
            message=f"Tool {tool_name} execution failed: {reason}",
            user_message="Tool execution failed. Please try again.",
            details={"tool_name": tool_name, "reason": reason, **(details or {})}
        )


class ToolTimeoutError(ToolException):
    """Tool execution timed out."""
    
    def __init__(self, tool_name: str, timeout_seconds: float, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="TOOL_101",
            message=f"Tool {tool_name} execution timed out after {timeout_seconds}s",
            user_message="Tool execution took too long. Please try again.",
            details={"tool_name": tool_name, "timeout_seconds": timeout_seconds, **(details or {})}
        )


class ToolValidationError(ToolException):
    """Tool call validation failed."""
    
    def __init__(self, tool_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="TOOL_102",
            message=f"Tool {tool_name} validation failed: {reason}",
            user_message=f"Tool call was not allowed: {reason}",
            details={"tool_name": tool_name, "reason": reason, **(details or {})}
        )


class ToolRateLimitError(ToolException):
    """Tool rate limit exceeded."""
    
    def __init__(self, tool_name: str, max_calls: int, window_seconds: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="TOOL_103",
            message=f"Tool {tool_name} rate limit exceeded: {max_calls} calls per {window_seconds}s",
            user_message="Too many requests. Please try again later.",
            details={"tool_name": tool_name, "max_calls": max_calls, "window_seconds": window_seconds, **(details or {})}
        )


# ============================================================================
# Validation Errors (VALIDATION_200 - VALIDATION_299)
# ============================================================================

class ValidationError(BaseAgentException):
    """Base class for validation errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_200",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            user_message=user_message or message,
            details=details or {}
        )


class InputValidationError(ValidationError):
    """Input validation failed."""
    
    def __init__(self, field: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="VALIDATION_201",
            message=f"Input validation failed for {field}: {reason}",
            user_message=f"Invalid input: {reason}",
            details={"field": field, "reason": reason, **(details or {})}
        )


# ============================================================================
# Policy/Guardrails Errors (POLICY_300 - POLICY_399)
# ============================================================================

class PolicyException(BaseAgentException):
    """Base class for policy/guardrails errors."""
    pass


class PolicyViolationError(PolicyException):
    """Policy violation detected."""
    
    def __init__(self, policy_type: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="POLICY_300",
            message=f"Policy violation ({policy_type}): {reason}",
            user_message=f"Request was blocked by policy: {reason}",
            details={"policy_type": policy_type, "reason": reason, **(details or {})}
        )


class GuardrailsBlockedError(PolicyException):
    """NeMo Guardrails blocked the request."""
    
    def __init__(self, check_type: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="POLICY_301",
            message=f"Guardrails blocked {check_type}: {reason}",
            user_message=f"Request was blocked: {reason}",
            details={"check_type": check_type, "reason": reason, **(details or {})}
        )


# ============================================================================
# LLM Errors (LLM_400 - LLM_499)
# ============================================================================

class LLMException(BaseAgentException):
    """Base class for LLM API errors."""
    pass


class LLMAPIError(LLMException):
    """LLM API call failed."""
    
    def __init__(self, model: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="LLM_400",
            message=f"LLM API error for {model}: {reason}",
            user_message="AI service error. Please try again.",
            details={"model": model, "reason": reason, **(details or {})}
        )


class LLMRateLimitError(LLMException):
    """LLM API rate limit exceeded."""
    
    def __init__(self, model: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="LLM_401",
            message=f"LLM API rate limit exceeded for {model}",
            user_message="Too many requests. Please try again later.",
            details={"model": model, "retry_after": retry_after, **(details or {})}
        )


class LLMTimeoutError(LLMException):
    """LLM API call timed out."""
    
    def __init__(self, model: str, timeout_seconds: float, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="LLM_402",
            message=f"LLM API call to {model} timed out after {timeout_seconds}s",
            user_message="Request took too long. Please try again.",
            details={"model": model, "timeout_seconds": timeout_seconds, **(details or {})}
        )


class LLMTokenLimitError(LLMException):
    """LLM token limit exceeded."""
    
    def __init__(self, model: str, max_tokens: int, requested_tokens: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="LLM_403",
            message=f"Token limit exceeded for {model}: requested {requested_tokens}, max {max_tokens}",
            user_message="Request too large. Please reduce input size.",
            details={"model": model, "max_tokens": max_tokens, "requested_tokens": requested_tokens, **(details or {})}
        )


# ============================================================================
# System Errors (SYSTEM_500 - SYSTEM_599)
# ============================================================================

class SystemException(BaseAgentException):
    """Base class for system/infrastructure errors."""
    pass


class ConfigurationError(SystemException):
    """System configuration error."""
    
    def __init__(self, config_key: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="SYSTEM_500",
            message=f"Configuration error for {config_key}: {reason}",
            user_message="System configuration error. Please contact support.",
            details={"config_key": config_key, "reason": reason, **(details or {})}
        )


class StorageError(SystemException):
    """Storage operation failed."""
    
    def __init__(self, operation: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="SYSTEM_501",
            message=f"Storage {operation} failed: {reason}",
            user_message="Storage error. Please try again.",
            details={"operation": operation, "reason": reason, **(details or {})}
        )


__all__ = [
    # Base
    "BaseAgentException",
    # Agent
    "AgentException",
    "AgentExecutionError",
    "AgentTimeoutError",
    "AgentConfigurationError",
    # Tool
    "ToolException",
    "ToolExecutionError",
    "ToolTimeoutError",
    "ToolValidationError",
    "ToolRateLimitError",
    # Validation
    "ValidationError",
    "InputValidationError",
    # Policy
    "PolicyException",
    "PolicyViolationError",
    "GuardrailsBlockedError",
    # LLM
    "LLMException",
    "LLMAPIError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMTokenLimitError",
    # System
    "SystemException",
    "ConfigurationError",
    "StorageError",
]
