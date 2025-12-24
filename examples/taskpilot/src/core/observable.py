"""Simple observability setup - direct library usage, no adapters.

This module provides simple global instances and setup functions.
Use libraries directly - no adapters, no backward compatibility.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

# Direct imports from libraries - no adapters
from agent_observable_core.observability import (
    MetricsCollector,
    ErrorTracker,
    Tracer as CoreTracer,
    HealthChecker,
    RequestContext,
    TraceContext as CoreTraceContext,
    generate_request_id,
    get_request_id as _core_get_request_id,
    set_request_id as _core_set_request_id,
    Span as CoreSpan,
    get_global_tracer,
    set_global_tracer,
)

# Re-export RequestContext for convenience (already imported directly)

def get_request_id():
    """Get current request ID."""
    return _core_get_request_id()

def set_request_id(request_id):
    """Set request ID."""
    _core_set_request_id(request_id)
from agent_observable_core.otel_integration import OpenTelemetryIntegration
from agent_observable_guardrails import NeMoGuardrailsWrapper, GuardrailsConfig
from agent_observable_policy import DecisionLogger, EmbeddedOPA
from agent_observable_prompt import PromptManager, PromptConfig

# Simple global instances
_metrics: Optional[MetricsCollector] = None
_errors: Optional[ErrorTracker] = None
_tracer: Optional[Tracer] = None
_health: Optional[HealthChecker] = None
_otel: Optional[OpenTelemetryIntegration] = None
_guardrails: Optional[NeMoGuardrailsWrapper] = None
_decision_logger: Optional[DecisionLogger] = None
_opa: Optional[EmbeddedOPA] = None
_prompt_manager: Optional[PromptManager] = None


def setup_observability(
    service_name: str = "agent-service",
    base_dir: Optional[Path] = None,
    enable_otel: bool = True,
    enable_guardrails: bool = True,
    enable_policy: bool = True,
    otlp_endpoint: str = "http://localhost:4317",
    guardrails_config_path: Optional[Path] = None,
    policy_dir: Optional[Path] = None,
    prompts_dir: Optional[Path] = None,
    decision_logs_file: Optional[Path] = None,
) -> dict:
    """One-line setup for all observability features.
    
    Args:
        service_name: Service name for traces
        base_dir: Base directory (defaults to current directory)
        enable_otel: Enable OpenTelemetry
        enable_guardrails: Enable NeMo Guardrails
        enable_policy: Enable policy enforcement
        otlp_endpoint: OTLP endpoint URL
        guardrails_config_path: Path to guardrails config.yml
        policy_dir: Directory containing .rego policy files
        prompts_dir: Directory containing prompt YAML files
        decision_logs_file: Path to decision logs file
    
    Returns:
        Dict with all initialized components
    """
    global _metrics, _errors, _tracer, _health, _otel, _guardrails, _decision_logger, _opa, _prompt_manager
    
    if base_dir is None:
        base_dir = Path.cwd()
    
    # Core observability (always enabled)
    _metrics = MetricsCollector()
    _errors = ErrorTracker()
    # Create wrapped Tracer (exports to OTEL)
    _tracer = Tracer()
    _health = HealthChecker()
    
    # Set global tracer so library TraceContext uses shared instance
    # This ensures parent-child relationships work
    set_global_tracer(_tracer._core_tracer)
    
    # OpenTelemetry (optional)
    if enable_otel:
        def metrics_callback(name: str, value: float) -> None:
            if _metrics:
                if name == "trace_export_latency_ms":
                    _metrics.record_histogram("observability.trace_export_latency_ms", value)
                elif name == "trace_export_queue_size":
                    _metrics.set_gauge("observability.trace_export_queue_size", value)
                elif name == "trace_export_failures":
                    _metrics.increment_counter("observability.trace_export_failures", value)
                elif name == "otel_collector_health":
                    _metrics.set_gauge("observability.otel_collector_health", value)
        
        _otel = OpenTelemetryIntegration(
            service_name=service_name,
            otlp_endpoint=otlp_endpoint,
            enabled=True,
            metrics_callback=metrics_callback,
        )
        _otel.start_export_worker()
    else:
        _otel = None
    
    # Policy (optional) - must be before guardrails if guardrails needs decision logger
    if enable_policy:
        if decision_logs_file is None:
            decision_logs_file = base_dir / "decision_logs.jsonl"
        
        def metrics_callback(name: str, value: float) -> None:
            if _metrics and name == "decision_log_flush_latency_ms":
                _metrics.record_histogram("observability.decision_log_flush_latency_ms", value)
        
        _decision_logger = DecisionLogger(
            log_file=decision_logs_file,
            metrics_callback=metrics_callback,
        )
        
        if policy_dir is None:
            policy_dir = base_dir / "policies"
        _opa = EmbeddedOPA(policy_dir=policy_dir)
    
    # Guardrails (optional) - after policy so it can use decision logger
    if enable_guardrails:
        async def decision_logger_callback(decision):
            if _decision_logger:
                await _decision_logger.log_decision(decision)
        
        config = GuardrailsConfig.create(
            config_path=guardrails_config_path,
            decision_logger_callback=decision_logger_callback if enable_policy else None,
        )
        _guardrails = config.create_nemo_guardrails()
    
    # Prompts (optional)
    if prompts_dir is None:
        prompts_dir = base_dir / "prompts"
    
    prompt_config = PromptConfig.create(prompts_dir=prompts_dir)
    _prompt_manager = prompt_config.create_prompt_manager()
    
    return {
        "metrics": _metrics,
        "errors": _errors,
        "tracer": _tracer,
        "health": _health,
        "otel": _otel,
        "guardrails": _guardrails,
        "decision_logger": _decision_logger,
        "opa": _opa,
        "prompt_manager": _prompt_manager,
    }


# Simple getter functions (for convenience)
def get_metrics() -> MetricsCollector:
    """Get metrics collector."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def get_errors() -> ErrorTracker:
    """Get error tracker."""
    global _errors
    if _errors is None:
        _errors = ErrorTracker()
    return _errors


class Tracer:
    """Tracer wrapper that integrates with OpenTelemetry."""
    
    def __init__(self, max_spans: int = 1000, trace_file=None):
        self._core_tracer = CoreTracer(max_spans=max_spans)
        self._trace_file = trace_file
    
    def start_span(self, name: str, request_id=None, parent_span_id=None, tags=None):
        """Start a span."""
        span = self._core_tracer.start_span(
            name=name,
            request_id=request_id,
            parent_span_id=parent_span_id,
            tags=tags or {},
        )
        # Create OTEL span for tracking
        create_otel_span_for_tracking(span)
        return span
    
    def end_span(self, span: CoreSpan):
        """End a span."""
        self._core_tracer.end_span(span)
        # Export to OTEL
        export_span_to_otel(
            span_name=span.name,
            start_time=span.start_time,
            end_time=span.end_time,
            request_id=span.request_id,
            parent_span_id=span.parent_span_id,
            span_id=span.span_id,
            tags=span.tags,
            logs=span.logs,
        )
    
    def get_trace(self, request_id: str):
        """Get trace for request ID."""
        return self._core_tracer.get_trace(request_id)
    
    def get_recent_spans(self, limit: int = 100):
        """Get recent spans."""
        return self._core_tracer.get_recent_spans(limit)
    
    @property
    def _active_spans(self):
        """Access to active spans (for parent lookup)."""
        return self._core_tracer._active_spans


class TraceContext:
    """Context manager for tracing spans."""
    
    def __init__(self, name: str, request_id=None, parent_span_id=None, tags=None, tracer=None):
        self.name = name
        self.request_id = request_id
        self.parent_span_id = parent_span_id
        self.tags = tags
        self.span = None
        # Use provided tracer or get wrapped Tracer instance (which exports to OTEL)
        if tracer:
            self._tracer = tracer
        else:
            # Use the wrapped Tracer instance (not the global core tracer)
            # This ensures OTEL export happens via end_span()
            self._tracer = get_tracer()
    
    def __enter__(self):
        self.span = self._tracer.start_span(
            self.name,
            request_id=self.request_id,
            parent_span_id=self.parent_span_id,
            tags=self.tags,
        )
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            self._tracer.end_span(self.span)


def get_tracer() -> Tracer:
    """Get tracer."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer


def record_error(error: Exception, **context) -> None:
    """Record an error (convenience function)."""
    errors = get_errors()
    errors.record_error(
        error,
        request_id=get_request_id(),
        context=context
    )


def get_health() -> HealthChecker:
    """Get health checker."""
    global _health
    if _health is None:
        _health = HealthChecker()
    return _health


def get_otel() -> Optional[OpenTelemetryIntegration]:
    """Get OpenTelemetry integration."""
    return _otel


def create_otel_span_for_tracking(span) -> None:
    """Create OpenTelemetry span for tracking (for tracer integration)."""
    otel = get_otel()
    if not otel:
        return
    
    # Extract span info
    span_id = span.span_id
    span_name = span.name
    request_id = span.request_id
    parent_span_id = span.parent_span_id
    tags = span.tags
    
    # Handle parent lookup
    if not parent_span_id and request_id:
        from agent_observable_core import get_trace_standardizer
        trace_std = get_trace_standardizer(service_name="taskpilot")
        workflow_span_name = trace_std.workflow_run()
        if hasattr(otel, "_span_contexts"):
            workflow_key = f"{request_id}:{workflow_span_name}"
            if workflow_key in otel._span_contexts:
                parent_span_id = workflow_key
    
    otel.create_otel_span_for_tracking(
        span_id=span_id,
        span_name=span_name,
        request_id=request_id,
        parent_span_id=parent_span_id,
        tags=tags,
    )


def export_span_to_otel(
    span_name: str,
    start_time: float,
    end_time: Optional[float],
    request_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    span_id: Optional[str] = None,
    tags: Optional[dict] = None,
    logs: Optional[list] = None,
) -> None:
    """Export span to OpenTelemetry."""
    otel = get_otel()
    if not otel:
        return
    
    otel.export_span_to_otel(
        span_name=span_name,
        start_time=start_time,
        end_time=end_time,
        request_id=request_id,
        parent_span_id=parent_span_id,
        span_id=span_id,
        tags=tags,
        logs=logs,
    )


def get_guardrails() -> Optional[NeMoGuardrailsWrapper]:
    """Get guardrails."""
    return _guardrails


def get_decision_logger() -> Optional[DecisionLogger]:
    """Get decision logger."""
    return _decision_logger


def set_decision_logger(logger_instance: DecisionLogger) -> None:
    """Set decision logger (for testing)."""
    global _decision_logger
    _decision_logger = logger_instance


def get_opa() -> Optional[EmbeddedOPA]:
    """Get embedded OPA."""
    return _opa


def get_prompt_manager() -> PromptManager:
    """Get prompt manager."""
    global _prompt_manager
    if _prompt_manager is None:
        prompt_config = PromptConfig.create(prompts_dir=Path("prompts"))
        _prompt_manager = prompt_config.create_prompt_manager()
    return _prompt_manager


def load_prompt(agent_name: str) -> str:
    """Load prompt for an agent."""
    return get_prompt_manager().load_prompt(agent_name)


# Re-export for convenience
__all__ = [
    "setup_observability",
    "get_metrics",
    "get_errors",
    "get_tracer",
    "get_health",
    "get_otel",
    "get_guardrails",
    "get_decision_logger",
    "set_decision_logger",
    "get_opa",
    "get_prompt_manager",
    "load_prompt",
    "record_error",
    "RequestContext",
    "TraceContext",
    "Tracer",
    "get_request_id",
    "set_request_id",
    "generate_request_id",
    "create_otel_span_for_tracking",
    "export_span_to_otel",
]
