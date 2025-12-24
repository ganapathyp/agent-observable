"""Framework detection and metric name standardization.

This module automatically detects which agent framework is being used
(MS Agent Framework, LangGraph, OpenAI custom routing) and provides
standardized metric names that work across all frameworks.

Teams just define their flows/tools/routing/agents, and the system
automatically wires up metrics, traces, and policy decisions.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AgentFramework(Enum):
    """Supported agent frameworks."""
    
    MS_AGENT_FRAMEWORK = "ms_agent_framework"
    LANGGRAPH = "langgraph"
    OPENAI_CUSTOM_ROUTING = "openai_custom_routing"
    UNKNOWN = "unknown"


class FrameworkDetector:
    """Detects which agent framework is being used."""
    
    _detected_framework: Optional[AgentFramework] = None
    
    @classmethod
    def detect(cls) -> AgentFramework:
        """Detect the agent framework being used.
        
        Returns:
            Detected framework or UNKNOWN
        """
        if cls._detected_framework:
            return cls._detected_framework
        
        # Try to detect MS Agent Framework
        try:
            import agent_framework
            if hasattr(agent_framework, 'WorkflowBuilder'):
                cls._detected_framework = AgentFramework.MS_AGENT_FRAMEWORK
                logger.debug("Detected framework: MS Agent Framework")
                return cls._detected_framework
        except ImportError:
            pass
        
        # Try to detect LangGraph
        try:
            import langgraph
            cls._detected_framework = AgentFramework.LANGGRAPH
            logger.debug("Detected framework: LangGraph")
            return cls._detected_framework
        except ImportError:
            pass
        
        # Try to detect OpenAI custom routing (check for common patterns)
        # This is harder to detect, so we'll use a heuristic
        # If we see OpenAI client usage with custom routing logic
        try:
            import openai
            # Check if there's custom routing logic in the codebase
            # For now, we'll default to MS_AGENT_FRAMEWORK if agent_framework is available
            # Otherwise, we'll need explicit configuration
            pass
        except ImportError:
            pass
        
        cls._detected_framework = AgentFramework.UNKNOWN
        logger.warning("Could not detect agent framework, using UNKNOWN")
        return cls._detected_framework
    
    @classmethod
    def set_framework(cls, framework: AgentFramework) -> None:
        """Manually set the framework (for testing or explicit configuration)."""
        cls._detected_framework = framework
        logger.debug(f"Framework manually set to: {framework.value}")
    
    @classmethod
    def reset(cls) -> None:
        """Reset detection (for testing)."""
        cls._detected_framework = None


class MetricNameStandardizer:
    """Standardizes metric names across different frameworks.
    
    Provides consistent metric naming regardless of which framework is used.
    All metric names follow the pattern: {category}.{entity}.{metric}
    """
    
    def __init__(self, service_name: str = "agent-service", framework: Optional[AgentFramework] = None):
        """Initialize metric name standardizer.
        
        Args:
            service_name: Service name for metrics (e.g., "taskpilot")
            framework: Optional framework override (auto-detects if None)
        """
        self.service_name = service_name
        self.framework = framework or FrameworkDetector.detect()
    
    # ============================================================================
    # Workflow Metrics (framework-agnostic)
    # ============================================================================
    
    def workflow_runs(self) -> str:
        """Workflow runs counter: workflow.runs"""
        return "workflow.runs"
    
    def workflow_success(self) -> str:
        """Workflow success counter: workflow.success"""
        return "workflow.success"
    
    def workflow_errors(self) -> str:
        """Workflow errors counter: workflow.errors"""
        return "workflow.errors"
    
    def workflow_latency_ms(self) -> str:
        """Workflow latency histogram: workflow.latency_ms"""
        return "workflow.latency_ms"
    
    # ============================================================================
    # Agent/Node Metrics (framework-agnostic)
    # ============================================================================
    # Works for: MS Agent Framework agents, LangGraph nodes, OpenAI routing roles
    
    def agent_invocations(self, agent_name: str) -> str:
        """Agent/node invocation counter: agent.{agent_name}.invocations"""
        return f"agent.{agent_name}.invocations"
    
    def agent_success(self, agent_name: str) -> str:
        """Agent/node success counter: agent.{agent_name}.success"""
        return f"agent.{agent_name}.success"
    
    def agent_errors(self, agent_name: str) -> str:
        """Agent/node error counter: agent.{agent_name}.errors"""
        return f"agent.{agent_name}.errors"
    
    def agent_latency_ms(self, agent_name: str) -> str:
        """Agent/node latency histogram: agent.{agent_name}.latency_ms"""
        return f"agent.{agent_name}.latency_ms"
    
    def agent_guardrails_blocked(self, agent_name: str) -> str:
        """Guardrails blocked counter: agent.{agent_name}.guardrails.blocked"""
        return f"agent.{agent_name}.guardrails.blocked"
    
    def agent_guardrails_output_blocked(self, agent_name: str) -> str:
        """Guardrails output blocked counter: agent.{agent_name}.guardrails.output_blocked"""
        return f"agent.{agent_name}.guardrails.output_blocked"
    
    def agent_policy_violations(self, agent_name: str) -> str:
        """Policy violations counter: agent.{agent_name}.policy.violations"""
        return f"agent.{agent_name}.policy.violations"
    
    # ============================================================================
    # Tool/Function Metrics (framework-agnostic)
    # ============================================================================
    # Works for: MS Agent Framework tools, LangGraph tools, OpenAI function calls
    
    def tool_calls(self, tool_name: str) -> str:
        """Tool/function call counter: tool.{tool_name}.calls"""
        return f"tool.{tool_name}.calls"
    
    def tool_success(self, tool_name: str) -> str:
        """Tool/function success counter: tool.{tool_name}.success"""
        return f"tool.{tool_name}.success"
    
    def tool_errors(self, tool_name: str) -> str:
        """Tool/function error counter: tool.{tool_name}.errors"""
        return f"tool.{tool_name}.errors"
    
    def tool_latency_ms(self, tool_name: str) -> str:
        """Tool/function latency histogram: tool.{tool_name}.latency_ms"""
        return f"tool.{tool_name}.latency_ms"
    
    # ============================================================================
    # LLM Metrics (framework-agnostic)
    # ============================================================================
    
    def llm_cost_total(self) -> str:
        """Total LLM cost: llm.cost.total"""
        return "llm.cost.total"
    
    def llm_cost_agent(self, agent_name: str) -> str:
        """LLM cost per agent: llm.cost.agent.{agent_name}"""
        return f"llm.cost.agent.{agent_name}"
    
    def llm_cost_model(self, model: str) -> str:
        """LLM cost per model: llm.cost.model.{model}"""
        return f"llm.cost.model.{model}"
    
    def llm_tokens_input_total(self) -> str:
        """Total input tokens: llm.tokens.input.total"""
        return "llm.tokens.input.total"
    
    def llm_tokens_output_total(self) -> str:
        """Total output tokens: llm.tokens.output.total"""
        return "llm.tokens.output.total"
    
    def llm_tokens_total_all(self) -> str:
        """Total tokens (all): llm.tokens.total.all"""
        return "llm.tokens.total.all"
    
    def llm_tokens_input_model(self, model: str) -> str:
        """Input tokens per model: llm.tokens.input.{model}"""
        return f"llm.tokens.input.{model}"
    
    def llm_tokens_output_model(self, model: str) -> str:
        """Output tokens per model: llm.tokens.output.{model}"""
        return f"llm.tokens.output.{model}"
    
    def llm_tokens_total_model(self, model: str) -> str:
        """Total tokens per model: llm.tokens.total.{model}"""
        return f"llm.tokens.total.{model}"
    
    # ============================================================================
    # Policy Metrics (framework-agnostic)
    # ============================================================================
    
    def policy_violations_total(self) -> str:
        """Total policy violations: policy.violations.total"""
        return "policy.violations.total"
    
    # ============================================================================
    # Observability Performance Metrics
    # ============================================================================
    
    def observability_trace_export_latency_ms(self) -> str:
        """Trace export latency: observability.trace_export_latency_ms"""
        return "observability.trace_export_latency_ms"
    
    def observability_trace_export_queue_size(self) -> str:
        """Trace export queue size: observability.trace_export_queue_size"""
        return "observability.trace_export_queue_size"
    
    def observability_trace_export_failures(self) -> str:
        """Trace export failures: observability.trace_export_failures"""
        return "observability.trace_export_failures"
    
    def observability_otel_collector_health(self) -> str:
        """OTEL collector health: observability.otel_collector_health"""
        return "observability.otel_collector_health"
    
    def observability_decision_log_flush_latency_ms(self) -> str:
        """Decision log flush latency: observability.decision_log_flush_latency_ms"""
        return "observability.decision_log_flush_latency_ms"
    
    # ============================================================================
    # Retry Metrics
    # ============================================================================
    
    def retry_attempts(self) -> str:
        """Retry attempts: retry.attempts"""
        return "retry.attempts"
    
    def retry_success_after_attempts(self) -> str:
        """Retry success after attempts: retry.success_after_attempts"""
        return "retry.success_after_attempts"
    
    def retry_exhausted(self) -> str:
        """Retry exhausted: retry.exhausted"""
        return "retry.exhausted"
    
    # ============================================================================
    # Health Check Metrics
    # ============================================================================
    
    def health_status(self) -> str:
        """Health status: health.status"""
        return "health.status"
    
    def health_check(self, check_name: str) -> str:
        """Health check gauge: health.check.{check_name}"""
        return f"health.check.{check_name}"


# Global instance for convenience (can be overridden)
_global_standardizer: Optional[MetricNameStandardizer] = None


def get_metric_standardizer(service_name: str = "agent-service") -> MetricNameStandardizer:
    """Get or create global metric name standardizer.
    
    Args:
        service_name: Service name for metrics
        
    Returns:
        MetricNameStandardizer instance
    """
    global _global_standardizer
    if _global_standardizer is None:
        _global_standardizer = MetricNameStandardizer(service_name=service_name)
    return _global_standardizer


def set_metric_standardizer(standardizer: MetricNameStandardizer) -> None:
    """Set global metric name standardizer (for testing)."""
    global _global_standardizer
    _global_standardizer = standardizer


__all__ = [
    "AgentFramework",
    "FrameworkDetector",
    "MetricNameStandardizer",
    "get_metric_standardizer",
    "set_metric_standardizer",
]
