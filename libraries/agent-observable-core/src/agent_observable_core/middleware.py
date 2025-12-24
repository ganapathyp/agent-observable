"""Generic observability middleware (framework-agnostic).

Automatically wires up:
- Metrics (workflow, agent, tool, LLM)
- Traces (with proper hierarchy)
- Policy decisions (OPA)
- Guardrails (NeMo)
- Cost tracking
- Error tracking

Engineers just use decorator/config - everything auto-wires.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, Awaitable, Optional, Any, Dict

from agent_observable_core.observability import (
    RequestContext,
    get_request_id,
    set_request_id,
    MetricsCollector,
    ErrorTracker,
    Tracer,
    TraceContext,
)
from agent_observable_core.framework_detector import get_metric_standardizer
from agent_observable_core.trace_standardizer import TraceNameStandardizer, get_trace_standardizer
from agent_observable_core.exceptions import (
    PolicyViolationError,
    GuardrailsBlockedError,
    AgentExecutionError,
    ToolValidationError,
)
from agent_observable_core.llm_cost_tracker import track_llm_metrics
from agent_observable_core.structured_output import extract_text_from_response

logger = logging.getLogger(__name__)


class MiddlewareHooks:
    """Hooks for project-specific middleware extensions.
    
    Projects can extend this to add custom logic while keeping
    all observability automatic.
    """
    
    def on_agent_start(
        self,
        agent_name: str,
        input_text: str,
        context: Any,
        request_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Called when agent execution starts.
        
        Args:
            agent_name: Name of the agent
            input_text: Extracted input text
            context: Framework-specific context
            request_id: Request ID for correlation
            
        Returns:
            Optional dict with additional span tags
        """
        return None
    
    def on_agent_complete(
        self,
        agent_name: str,
        output_text: str,
        context: Any,
        request_id: str,
        latency_ms: float,
    ) -> None:
        """Called when agent execution completes successfully.
        
        Args:
            agent_name: Name of the agent
            output_text: Extracted output text
            context: Framework-specific context
            request_id: Request ID for correlation
            latency_ms: Execution latency in milliseconds
        """
        pass
    
    def on_agent_error(
        self,
        agent_name: str,
        error: Exception,
        context: Any,
        request_id: str,
    ) -> None:
        """Called when agent execution fails.
        
        Args:
            agent_name: Name of the agent
            error: Exception that occurred
            context: Framework-specific context
            request_id: Request ID for correlation
        """
        pass
    
    def extract_input_text(self, context: Any) -> str:
        """Extract input text from context (project-specific if needed).
        
        Args:
            context: Framework-specific context
            
        Returns:
            Extracted input text
        """
        # Default: use generic extractor
        return extract_text_from_response(context)
    
    def extract_output_text(self, context: Any, result: Any) -> str:
        """Extract output text from context/result (project-specific if needed).
        
        Args:
            context: Framework-specific context
            result: Agent execution result
            
        Returns:
            Extracted output text
        """
        # Default: use generic extractor
        if result:
            return extract_text_from_response(result)
        return extract_text_from_response(context)


def create_observable_middleware(
    agent_name: str,
    service_name: str = "agent-service",
    enable_metrics: bool = True,
    enable_tracing: bool = True,
    enable_policy: bool = True,
    enable_guardrails: bool = True,
    enable_cost_tracking: bool = True,
    metrics_collector: Optional[MetricsCollector] = None,
    error_tracker: Optional[ErrorTracker] = None,
    tracer: Optional[Tracer] = None,
    hooks: Optional[MiddlewareHooks] = None,
    opa_package: Optional[str] = None,
    guardrails_wrapper: Optional[Any] = None,
    decision_logger: Optional[Any] = None,
    opa_validator: Optional[Any] = None,
) -> Callable:
    """Create generic observability middleware (framework-agnostic).
    
    Automatically wires up all observability features. Projects can
    provide hooks for custom logic.
    
    Args:
        agent_name: Name of the agent
        service_name: Service name for metric/trace standardization
        enable_metrics: Enable metrics collection
        enable_tracing: Enable distributed tracing
        enable_policy: Enable OPA policy enforcement
        enable_guardrails: Enable NeMo Guardrails validation
        enable_cost_tracking: Enable LLM cost tracking
        metrics_collector: Optional MetricsCollector instance
        error_tracker: Optional ErrorTracker instance
        tracer: Optional Tracer instance
        hooks: Optional MiddlewareHooks for project-specific extensions
        opa_package: Optional OPA package name (defaults to "{service_name}.tool_calls")
        guardrails_wrapper: Optional NeMo Guardrails wrapper
        decision_logger: Optional DecisionLogger instance
        opa_validator: Optional OPAToolValidator instance
    
    Returns:
        Middleware function (framework-specific signature)
    """
    # Get standardizers
    metric_standardizer = get_metric_standardizer(service_name=service_name)
    trace_standardizer = get_trace_standardizer(service_name=service_name)
    
    # Default hooks (no-op if not provided)
    if hooks is None:
        hooks = MiddlewareHooks()
    
    # Default OPA package
    if opa_package is None:
        opa_package = f"{service_name}.tool_calls"
    
    async def observable_middleware(
        context: Any,
        next_handler: Callable[[Any], Awaitable[Any]]
    ) -> Any:
        """Generic observability middleware.
        
        Automatically handles:
        - Request ID correlation
        - Metrics collection
        - Distributed tracing
        - Guardrails validation
        - Policy enforcement
        - Cost tracking
        - Error tracking
        
        Projects can extend via hooks for custom logic.
        """
        # Get or create request ID
        request_id = get_request_id() or str(uuid.uuid4())
        set_request_id(request_id)
        
        # Get observability components
        if metrics_collector is None:
            from agent_observable_core.observability import MetricsCollector
            metrics_collector = MetricsCollector()
        
        if error_tracker is None:
            from agent_observable_core.observability import ErrorTracker
            error_tracker = ErrorTracker()
        
        if tracer is None:
            from agent_observable_core.observability import Tracer
            tracer = Tracer()
        
        # Extract input text (using hooks for project-specific extraction)
        input_text = hooks.extract_input_text(context)
        
        # Try to get parent span ID from active spans (workflow span)
        parent_span_id = None
        try:
            active_spans = getattr(tracer, '_active_spans', {})
            workflow_span_name = trace_standardizer.workflow_run()
            for active_span in active_spans.values():
                if active_span.name == workflow_span_name and active_span.request_id == request_id:
                    parent_span_id = active_span.span_id
                    break
        except Exception:
            pass
        
        # Start tracing span
        span_name = trace_standardizer.agent_run(agent_name)
        with TraceContext(
            name=span_name,
            request_id=request_id,
            parent_span_id=parent_span_id,
            tags={"agent_name": agent_name}
        ) as span:
            start_time = time.time()
            
            # Record metrics
            if enable_metrics:
                metrics_collector.increment_counter(metric_standardizer.agent_invocations(agent_name))
            
            # Call project-specific hook
            custom_tags = hooks.on_agent_start(agent_name, input_text, context, request_id)
            if custom_tags:
                span.tags.update(custom_tags)
            
            try:
                # Guardrails input validation
                if enable_guardrails and guardrails_wrapper:
                    allowed, reason = await guardrails_wrapper.validate_input(input_text)
                    if not allowed:
                        if enable_metrics:
                            metrics_collector.increment_counter(
                                metric_standardizer.agent_guardrails_blocked(agent_name)
                            )
                        error = GuardrailsBlockedError(
                            check_type="input",
                            reason=reason,
                            details={"agent_name": agent_name, "request_id": request_id}
                        )
                        logger.error(f"[GUARDRAILS] [{error.error_code}] Input blocked: {reason}")
                        raise error
                
                # Policy enforcement (simple keyword-based - projects can extend)
                # This is a simple example - projects can add custom policy logic via hooks
                if enable_policy and input_text and "delete" in input_text.lower():
                    if enable_metrics:
                        metrics_collector.increment_counter(
                            metric_standardizer.agent_policy_violations(agent_name)
                        )
                        metrics_collector.increment_counter(metric_standardizer.policy_violations_total())
                    error = PolicyViolationError(
                        policy_type="keyword_filter",
                        reason="'delete' keyword not allowed",
                        details={"agent_name": agent_name, "request_id": request_id}
                    )
                    logger.error(f"[POLICY] [{error.error_code}] Policy violation: 'delete' keyword detected")
                    raise error
                
                # Execute the agent
                result = await next_handler(context)
                
                # Extract output text (using hooks for project-specific extraction)
                output_text = hooks.extract_output_text(context, result)
                
                # Guardrails output validation
                if enable_guardrails and guardrails_wrapper:
                    allowed, reason = await guardrails_wrapper.validate_output(output_text)
                    if not allowed:
                        if enable_metrics:
                            metrics_collector.increment_counter(
                                metric_standardizer.agent_guardrails_output_blocked(agent_name)
                            )
                        logger.error(f"[GUARDRAILS] Output blocked: {reason}")
                        raise ValueError(f"Output validation failed: {reason}")
                
                # Validate tool calls with OPA (if any were made)
                if enable_policy and opa_validator:
                    # Check for tool calls in result (framework-agnostic)
                    from agent_observable_core.structured_output import extract_function_call_arguments
                    tool_calls = extract_function_call_arguments(result)
                    if tool_calls:
                        # Validate with OPA (opa_validator handles logging)
                        allowed, reason, requires_approval = await opa_validator.validate_tool_call(
                            tool_name="unknown",  # Will be extracted from tool_calls
                            parameters=tool_calls,
                            agent_type=agent_name,
                            agent_id=agent_name,
                        )
                        if not allowed:
                            error = ToolValidationError(
                                tool_name="unknown",
                                reason=reason,
                                details={"agent_name": agent_name, "request_id": request_id}
                            )
                            logger.warning(f"[OPA] [{error.error_code}] Tool call denied: {reason}")
                
                # Track LLM cost (if available)
                if enable_cost_tracking:
                    try:
                        track_llm_metrics(result, agent_name, metrics_collector, service_name=service_name)
                    except Exception as e:
                        logger.debug(f"Failed to track LLM metrics: {e}")
                
                # Record latency
                latency_ms = (time.time() - start_time) * 1000
                if enable_metrics:
                    metrics_collector.record_histogram(
                        metric_standardizer.agent_latency_ms(agent_name),
                        latency_ms
                    )
                    metrics_collector.increment_counter(metric_standardizer.agent_success(agent_name))
                
                # Update span
                span.tags["latency_ms"] = str(latency_ms)
                span.tags["output_length"] = str(len(output_text)) if output_text else "0"
                
                # Call project-specific hook
                hooks.on_agent_complete(agent_name, output_text, context, request_id, latency_ms)
                
                return result
                
            except Exception as e:
                # Record error
                if enable_metrics:
                    metrics_collector.increment_counter(metric_standardizer.agent_errors(agent_name))
                
                # Extract error code if available
                error_code = getattr(e, 'error_code', None)
                if error_code:
                    logger.error(f"[{error_code}] Agent {agent_name} error: {getattr(e, 'message', str(e))}")
                else:
                    logger.error(f"Agent {agent_name} error: {e}")
                
                # Track error
                if error_tracker:
                    error_tracker.record_error(e, request_id=request_id, context={"agent_name": agent_name})
                
                # Call project-specific hook
                hooks.on_agent_error(agent_name, e, context, request_id)
                
                raise
    
    return observable_middleware


__all__ = [
    "MiddlewareHooks",
    "create_observable_middleware",
]
