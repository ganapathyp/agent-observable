"""Trace/span name standardization (framework-agnostic).

Provides consistent trace/span names across all frameworks.
Automatically uses service_name for proper hierarchy.
"""
from __future__ import annotations

from typing import Optional


class TraceNameStandardizer:
    """Standardizes trace/span names across different frameworks.
    
    All span names follow the pattern: {service_name}.{entity}.{operation}
    This ensures proper hierarchy in Jaeger regardless of framework.
    """
    
    def __init__(self, service_name: str = "agent-service"):
        """Initialize trace name standardizer.
        
        Args:
            service_name: Service name for traces (e.g., "taskpilot")
        """
        self.service_name = service_name
    
    # ============================================================================
    # Workflow Spans
    # ============================================================================
    
    def workflow_run(self) -> str:
        """Workflow execution span: {service_name}.workflow.run"""
        return f"{self.service_name}.workflow.run"
    
    # ============================================================================
    # Agent/Node Spans (framework-agnostic)
    # ============================================================================
    # Works for: MS Agent Framework agents, LangGraph nodes, OpenAI routing roles
    
    def agent_run(self, agent_name: str) -> str:
        """Agent/node execution span: {service_name}.agent.{agent_name}.run"""
        return f"{self.service_name}.agent.{agent_name}.run"
    
    # ============================================================================
    # Tool/Function Spans (framework-agnostic)
    # ============================================================================
    # Works for: MS Agent Framework tools, LangGraph tools, OpenAI function calls
    
    def tool_call(self, tool_name: str) -> str:
        """Tool/function call span: {service_name}.tool.{tool_name}.call"""
        return f"{self.service_name}.tool.{tool_name}.call"
    
    # ============================================================================
    # LLM Spans
    # ============================================================================
    
    def llm_call(self, model: str) -> str:
        """LLM API call span: {service_name}.llm.{model}.call"""
        return f"{self.service_name}.llm.{model}.call"
    
    # ============================================================================
    # Policy/Guardrails Spans
    # ============================================================================
    
    def policy_evaluation(self, policy_type: str) -> str:
        """Policy evaluation span: {service_name}.policy.{policy_type}.evaluate"""
        return f"{self.service_name}.policy.{policy_type}.evaluate"
    
    def guardrails_check(self, check_type: str) -> str:
        """Guardrails check span: {service_name}.guardrails.{check_type}.check"""
        return f"{self.service_name}.guardrails.{check_type}.check"


# Global instance for convenience
_global_trace_standardizer: Optional[TraceNameStandardizer] = None


def get_trace_standardizer(service_name: str = "agent-service") -> TraceNameStandardizer:
    """Get or create global trace name standardizer.
    
    Args:
        service_name: Service name for traces
        
    Returns:
        TraceNameStandardizer instance
    """
    global _global_trace_standardizer
    if _global_trace_standardizer is None or _global_trace_standardizer.service_name != service_name:
        _global_trace_standardizer = TraceNameStandardizer(service_name=service_name)
    return _global_trace_standardizer


def set_trace_standardizer(standardizer: TraceNameStandardizer) -> None:
    """Set global trace name standardizer (for testing)."""
    global _global_trace_standardizer
    _global_trace_standardizer = standardizer


__all__ = [
    "TraceNameStandardizer",
    "get_trace_standardizer",
    "set_trace_standardizer",
]
