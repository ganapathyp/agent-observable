"""agent-observable-core: metrics, traces, errors, health for agent systems.

Framework-agnostic observability for:
- MS Agent Framework
- LangGraph
- OpenAI custom routing
"""

from .observability import (
    RequestContext,
    generate_request_id,
    get_request_id,
    set_request_id,
    MetricsCollector,
    ErrorTracker,
    Tracer,
    TraceContext,
    HealthChecker,
    ObservabilityConfig,
)

from .framework_detector import (
    AgentFramework,
    FrameworkDetector,
    MetricNameStandardizer,
    get_metric_standardizer,
    set_metric_standardizer,
)

from .trace_standardizer import (
    TraceNameStandardizer,
    get_trace_standardizer,
    set_trace_standardizer,
)

from .exceptions import (
    BaseAgentException,
    AgentException,
    AgentExecutionError,
    AgentTimeoutError,
    AgentConfigurationError,
    ToolException,
    ToolExecutionError,
    ToolTimeoutError,
    ToolValidationError,
    ToolRateLimitError,
    ValidationError,
    InputValidationError,
    PolicyException,
    PolicyViolationError,
    GuardrailsBlockedError,
    LLMException,
    LLMAPIError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMTokenLimitError,
    SystemException,
    ConfigurationError,
    StorageError,
)

from .llm_cost_tracker import (
    extract_token_usage,
    calculate_cost,
    track_llm_metrics,
    MODEL_PRICING,
)

from .retry import (
    RetryConfig,
    retry_with_backoff,
    retry_with_backoff_decorator,
)

from .tool_executor import (
    execute_tool_with_timeout,
    execute_tool_sync_with_timeout,
)

from .structured_output import (
    extract_text_from_response,
    extract_function_call_arguments,
    parse_json_from_text,
)

from .middleware import (
    MiddlewareHooks,
    create_observable_middleware,
)

try:
    from .otel_integration import OpenTelemetryIntegration
    __all__ = [
        # Core observability
        "RequestContext",
        "generate_request_id",
        "get_request_id",
        "set_request_id",
        "MetricsCollector",
        "ErrorTracker",
        "Tracer",
        "TraceContext",
        "HealthChecker",
        "ObservabilityConfig",
        "OpenTelemetryIntegration",
        # Framework detection
        "AgentFramework",
        "FrameworkDetector",
        "MetricNameStandardizer",
        "get_metric_standardizer",
        "set_metric_standardizer",
        # Trace standardization
        "TraceNameStandardizer",
        "get_trace_standardizer",
        "set_trace_standardizer",
        # Exceptions
        "BaseAgentException",
        "AgentException",
        "AgentExecutionError",
        "AgentTimeoutError",
        "AgentConfigurationError",
        "ToolException",
        "ToolExecutionError",
        "ToolTimeoutError",
        "ToolValidationError",
        "ToolRateLimitError",
        "ValidationError",
        "InputValidationError",
        "PolicyException",
        "PolicyViolationError",
        "GuardrailsBlockedError",
        "LLMException",
        "LLMAPIError",
        "LLMRateLimitError",
        "LLMTimeoutError",
        "LLMTokenLimitError",
        "SystemException",
        "ConfigurationError",
        "StorageError",
        # LLM cost tracking
        "extract_token_usage",
        "calculate_cost",
        "track_llm_metrics",
        "MODEL_PRICING",
        # Retry logic
        "RetryConfig",
        "retry_with_backoff",
        "retry_with_backoff_decorator",
        # Tool execution
        "execute_tool_with_timeout",
        "execute_tool_sync_with_timeout",
        # Structured output
        "extract_text_from_response",
        "extract_function_call_arguments",
        "parse_json_from_text",
        # Middleware
        "MiddlewareHooks",
        "create_observable_middleware",
    ]
except ImportError:
    # OpenTelemetry not available
    __all__ = [
        # Core observability
        "RequestContext",
        "generate_request_id",
        "get_request_id",
        "set_request_id",
        "MetricsCollector",
        "ErrorTracker",
        "Tracer",
        "TraceContext",
        "HealthChecker",
        "ObservabilityConfig",
        # Framework detection
        "AgentFramework",
        "FrameworkDetector",
        "MetricNameStandardizer",
        "get_metric_standardizer",
        "set_metric_standardizer",
        # Trace standardization
        "TraceNameStandardizer",
        "get_trace_standardizer",
        "set_trace_standardizer",
        # Exceptions
        "BaseAgentException",
        "AgentException",
        "AgentExecutionError",
        "AgentTimeoutError",
        "AgentConfigurationError",
        "ToolException",
        "ToolExecutionError",
        "ToolTimeoutError",
        "ToolValidationError",
        "ToolRateLimitError",
        "ValidationError",
        "InputValidationError",
        "PolicyException",
        "PolicyViolationError",
        "GuardrailsBlockedError",
        "LLMException",
        "LLMAPIError",
        "LLMRateLimitError",
        "LLMTimeoutError",
        "LLMTokenLimitError",
        "SystemException",
        "ConfigurationError",
        "StorageError",
        # LLM cost tracking
        "extract_token_usage",
        "calculate_cost",
        "track_llm_metrics",
        "MODEL_PRICING",
        # Retry logic
        "RetryConfig",
        "retry_with_backoff",
        "retry_with_backoff_decorator",
        # Tool execution
        "execute_tool_with_timeout",
        "execute_tool_sync_with_timeout",
        # Structured output
        "extract_text_from_response",
        "extract_function_call_arguments",
        "parse_json_from_text",
        # Middleware
        "MiddlewareHooks",
        "create_observable_middleware",
    ]
