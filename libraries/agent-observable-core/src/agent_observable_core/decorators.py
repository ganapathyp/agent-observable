"""Declarative decorators for automatic observability wiring.

Engineers just add a decorator, and everything auto-wires:
- Metrics
- Traces
- Policy decisions
- Guardrails
- Cost tracking
- Error tracking

Usage:
    @observable(service_name="taskpilot")
    async def my_agent(input: str):
        return result
"""
from __future__ import annotations

import functools
import logging
from typing import Callable, Any, Optional

from agent_observable_core.middleware import create_observable_middleware, MiddlewareHooks
from agent_observable_core.observability import (
    RequestContext,
    MetricsCollector,
    ErrorTracker,
    Tracer,
)

logger = logging.getLogger(__name__)


def observable(
    service_name: str = "agent-service",
    enable_metrics: bool = True,
    enable_tracing: bool = True,
    enable_policy: bool = True,
    enable_guardrails: bool = True,
    enable_cost_tracking: bool = True,
    opa_package: Optional[str] = None,
    metrics_collector: Optional[MetricsCollector] = None,
    error_tracker: Optional[ErrorTracker] = None,
    tracer: Optional[Tracer] = None,
    hooks: Optional[MiddlewareHooks] = None,
):
    """Decorator that automatically enables observability for a function.
    
    Automatically wires up:
    - Request ID correlation
    - Metrics collection
    - Distributed tracing
    - Error tracking
    - Guardrails validation
    - Policy enforcement
    - Cost tracking
    
    Args:
        service_name: Service name for traces and metrics
        enable_metrics: Enable metrics collection
        enable_tracing: Enable distributed tracing
        enable_policy: Enable OPA policy enforcement
        enable_guardrails: Enable NeMo Guardrails validation
        enable_cost_tracking: Enable LLM cost tracking
        opa_package: Optional OPA package name
        metrics_collector: Optional MetricsCollector instance
        error_tracker: Optional ErrorTracker instance
        tracer: Optional Tracer instance
        hooks: Optional MiddlewareHooks for custom logic
    
    Returns:
        Decorated function with observability enabled
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get function name as agent name
            agent_name = func.__name__
            
            # Get observability components
            from agent_observable_core.observability import (
                get_metrics,
                get_errors,
                get_tracer,
            )
            from agent_observable_core.observable import (
                get_guardrails,
                get_decision_logger,
                get_opa,
            )
            
            metrics = metrics_collector or get_metrics()
            errors = error_tracker or get_errors()
            tracer_instance = tracer or get_tracer()
            
            # Get optional components
            guardrails = None
            if enable_guardrails:
                from agent_observable_core.observable import get_guardrails
                guardrails = get_guardrails()
            
            decision_logger = None
            opa_validator = None
            if enable_policy:
                from agent_observable_core.observable import get_decision_logger, get_opa
                decision_logger = get_decision_logger()
                
                # Create OPA validator if available
                opa = get_opa()
                if opa:
                    from agent_observable_policy.opa_tool_validator import OPAToolValidator
                    opa_validator = OPAToolValidator(
                        opa_package=opa_package or f"{service_name}.tool_calls",
                        use_embedded=True,
                        embedded_opa=opa,
                        decision_logger=decision_logger,
                        metrics_collector=metrics,
                        service_name=service_name,
                    )
            
            # Create middleware
            middleware = create_observable_middleware(
                agent_name=agent_name,
                service_name=service_name,
                enable_metrics=enable_metrics,
                enable_tracing=enable_tracing,
                enable_policy=enable_policy,
                enable_guardrails=enable_guardrails,
                enable_cost_tracking=enable_cost_tracking,
                metrics_collector=metrics,
                error_tracker=errors,
                tracer=tracer_instance,
                hooks=hooks,
                opa_package=opa_package,
                guardrails_wrapper=guardrails,
                decision_logger=decision_logger,
                opa_validator=opa_validator,
            )
            
            # Create a simple context object for the middleware
            class SimpleContext:
                def __init__(self, args, kwargs):
                    self.args = args
                    self.kwargs = kwargs
                    self.messages = []  # For framework compatibility
                    self.result = None
            
            # Wrap function execution
            with RequestContext():
                context = SimpleContext(args, kwargs)
                
                async def next_handler(ctx):
                    ctx.result = await func(*ctx.args, **ctx.kwargs)
                    return ctx.result
                
                return await middleware(context, next_handler)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, just add basic observability
            from agent_observable_core.observability import RequestContext, get_metrics
            from agent_observable_core.framework_detector import get_metric_standardizer
            
            with RequestContext():
                metrics = metrics_collector or get_metrics()
                standardizer = get_metric_standardizer(service_name=service_name)
                
                if enable_metrics:
                    metrics.increment_counter(standardizer.workflow_runs())
                
                try:
                    result = func(*args, **kwargs)
                    if enable_metrics:
                        metrics.increment_counter(standardizer.workflow_success())
                    return result
                except Exception as e:
                    if enable_metrics:
                        metrics.increment_counter(standardizer.workflow_errors())
                    if error_tracker:
                        error_tracker.record_error(e)
                    raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


__all__ = [
    "observable",
]
