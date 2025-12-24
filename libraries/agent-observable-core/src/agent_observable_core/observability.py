"""Core observability primitives: Request IDs, metrics, tracing, errors, health."""
from __future__ import annotations

import uuid
import time
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
from contextvars import ContextVar
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class ObservabilityConfig:
    """Configuration for observability components."""

    # Metrics collector settings
    metrics_max_samples: int = 1000

    # Error tracker settings
    error_tracker_max_errors: int = 1000

    # Tracer settings
    tracer_max_spans: int = 1000

    def create_metrics_collector(self) -> "MetricsCollector":
        """Create a MetricsCollector with this configuration."""
        return MetricsCollector(max_samples=self.metrics_max_samples)

    def create_error_tracker(self) -> "ErrorTracker":
        """Create an ErrorTracker with this configuration."""
        return ErrorTracker(max_errors=self.error_tracker_max_errors)

    def create_tracer(self) -> "Tracer":
        """Create a Tracer with this configuration."""
        return Tracer(max_spans=self.tracer_max_spans)

# Request ID context variable (thread-safe, async-safe)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return _request_id.get()


def set_request_id(request_id: Optional[str]) -> None:
    """Set request ID in context."""
    _request_id.set(request_id)


@dataclass
class RequestContext:
    """Context manager for request ID correlation."""

    request_id: Optional[str] = None

    def __enter__(self) -> "RequestContext":
        self.request_id = self.request_id or generate_request_id()
        self._token = _request_id.set(self.request_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if hasattr(self, "_token"):
            _request_id.reset(self._token)


# ==========================================================================
# Metrics
# ==========================================================================


@dataclass
class MetricValue:
    """Single metric value with timestamp."""

    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """In-memory metrics collector with counters, gauges, histograms."""

    def __init__(self, max_samples: int = 1000) -> None:
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self._lock = threading.Lock()

    def increment_counter(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def record_histogram(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms[name].append(
                MetricValue(value=value, timestamp=time.time())
            )

    def get_counter(self, name: str) -> float:
        with self._lock:
            return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> float:
        with self._lock:
            return self._gauges.get(name, 0.0)

    def get_histogram_values(self, name: str) -> List[MetricValue]:
        with self._lock:
            return list(self._histograms.get(name, deque()))

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in Prometheus-style format.
        
        Returns:
            Dict with counters, gauges, and histograms
        """
        with self._lock:
            histograms = {}
            for name in self._histograms:
                values = [m.value for m in self._histograms.get(name, deque())]
                if not values:
                    histograms[name] = {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
                else:
                    sorted_values = sorted(values)
                    count = len(sorted_values)
                    histograms[name] = {
                        "count": count,
                        "min": min(sorted_values),
                        "max": max(sorted_values),
                        "avg": sum(sorted_values) / count,
                        "p50": sorted_values[int(count * 0.50)] if count > 0 else 0,
                        "p95": sorted_values[int(count * 0.95)] if count > 0 else 0,
                        "p99": sorted_values[int(count * 0.99)] if count > 0 else 0,
                    }
            
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": histograms
            }

    def get_golden_signals(
        self,
        workflow_runs_metric: str = "workflow.runs",
        workflow_success_metric: str = "workflow.success",
        workflow_latency_metric: str = "workflow.latency_ms",
        llm_cost_metric: str = "llm.cost.total",
        llm_quality_correct_metric: str = "llm.quality.user_confirmed_correct",
        llm_quality_incorrect_metric: str = "llm.quality.user_confirmed_incorrect",
        policy_violations_metric: str = "policy.violations.total",
    ) -> Dict[str, Any]:
        """Calculate Golden Signals for LLM production monitoring.
        
        Args:
            workflow_runs_metric: Metric name for workflow runs counter
            workflow_success_metric: Metric name for workflow success counter
            workflow_latency_metric: Metric name for workflow latency histogram
            llm_cost_metric: Metric name for LLM cost counter
            llm_quality_correct_metric: Metric name for user-confirmed correct counter
            llm_quality_incorrect_metric: Metric name for user-confirmed incorrect counter
            policy_violations_metric: Metric name for policy violations counter
        
        Returns:
            Dict with the 5 Golden Signals:
            - success_rate: Workflow success rate (%)
            - p95_latency: 95th percentile latency (ms)
            - cost_per_successful_task: Cost per successful task (USD)
            - user_confirmed_correctness: User-confirmed correctness rate (%)
            - policy_violation_rate: Policy violation rate (%)
        """
        with self._lock:
            # Calculate success rate
            total_runs = self._counters.get(workflow_runs_metric, 0.0)
            successful_runs = self._counters.get(workflow_success_metric, 0.0)
            success_rate = (successful_runs / total_runs * 100.0) if total_runs > 0 else 100.0

            # Calculate P95 latency
            latency_values = [m.value for m in self._histograms.get(workflow_latency_metric, deque())]
            if latency_values:
                sorted_latencies = sorted(latency_values)
                p95_index = int(len(sorted_latencies) * 0.95)
                p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]
            else:
                p95_latency = 0.0

            # Calculate cost per successful task
            total_cost = self._counters.get(llm_cost_metric, 0.0)
            cost_per_successful_task = (total_cost / successful_runs) if successful_runs > 0 else 0.0

            # Calculate user-confirmed correctness rate
            correct_count = self._counters.get(llm_quality_correct_metric, 0.0)
            incorrect_count = self._counters.get(llm_quality_incorrect_metric, 0.0)
            total_feedback = correct_count + incorrect_count
            user_confirmed_correctness = (correct_count / total_feedback * 100.0) if total_feedback > 0 else 0.0

            # Calculate policy violation rate
            violations = self._counters.get(policy_violations_metric, 0.0)
            policy_violation_rate = (violations / total_runs * 100.0) if total_runs > 0 else 0.0

            return {
                "success_rate": round(success_rate, 2),
                "p95_latency": round(p95_latency, 2),
                "cost_per_successful_task": round(cost_per_successful_task, 4),
                "user_confirmed_correctness": round(user_confirmed_correctness, 2),
                "policy_violation_rate": round(policy_violation_rate, 2),
            }


# ==========================================================================
# Error tracking
# ==========================================================================


@dataclass
class ErrorRecord:
    """Structured error record."""

    error_type: str
    error_message: str
    stack_trace: Optional[str]
    request_id: Optional[str]
    agent_name: Optional[str]
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    count: int = 1


class ErrorTracker:
    """Error tracking and aggregation."""

    def __init__(self, max_errors: int = 1000) -> None:
        self._errors: deque = deque(maxlen=max_errors)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def record_error(
        self,
        error: Exception,
        request_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        import traceback

        error_key = f"{type(error).__name__}:{str(error)[:100]}"

        with self._lock:
            self._error_counts[error_key] += 1

            error_record = ErrorRecord(
                error_type=type(error).__name__,
                error_message=str(error),
                stack_trace=traceback.format_exc(),
                request_id=request_id or get_request_id(),
                agent_name=agent_name,
                timestamp=time.time(),
                context=context or {},
                count=self._error_counts[error_key],
            )

            self._errors.append(error_record)

            logger.error(
                f"[ERROR] {error_record.error_type}: {error_record.error_message} "
                f"(request_id={error_record.request_id}, agent={agent_name})",
                exc_info=error,
            )

    def get_error_summary(self) -> Dict[str, Any]:
        with self._lock:
            recent_errors = [
                {
                    "error_type": e.error_type,
                    "error_message": e.error_message[:200],
                    "request_id": e.request_id,
                    "agent_name": e.agent_name,
                    "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                    "count": e.count,
                }
                for e in list(self._errors)[-10:]
            ]

            return {
                "total_errors": len(self._errors),
                "error_counts": dict(self._error_counts),
                "recent_errors": recent_errors,
            }


# ==========================================================================
# Tracing
# ==========================================================================


@dataclass
class Span:
    name: str
    start_time: float
    end_time: Optional[float] = None
    request_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "request_id": self.request_id,
            "parent_span_id": self.parent_span_id,
            "tags": self.tags,
            "logs": self.logs,
        }


class Tracer:
    def __init__(self, max_spans: int = 1000) -> None:
        self._spans: deque = deque(maxlen=max_spans)
        self._active_spans: Dict[str, Span] = {}
        self._lock = threading.Lock()

    def start_span(
        self,
        name: str,
        request_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Span:
        span = Span(
            name=name,
            start_time=time.time(),
            request_id=request_id or get_request_id(),
            parent_span_id=parent_span_id,
            tags=tags or {},
        )

        with self._lock:
            self._active_spans[span.span_id] = span

        return span

    def end_span(self, span: Span) -> None:
        span.end_time = time.time()

        with self._lock:
            if span.span_id in self._active_spans:
                del self._active_spans[span.span_id]
            self._spans.append(span)

    def get_trace(self, request_id: str) -> List[Span]:
        with self._lock:
            return [s for s in self._spans if s.request_id == request_id]

    def get_recent_spans(self, limit: int = 100) -> List[Span]:
        with self._lock:
            return list(self._spans)[-limit:]


# Global tracer instance (shared across all TraceContext instances)
_global_tracer: Optional[Tracer] = None

def get_global_tracer() -> Tracer:
    """Get or create global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer()
    return _global_tracer

def set_global_tracer(tracer: Tracer) -> None:
    """Set global tracer instance (for testing)."""
    global _global_tracer
    _global_tracer = tracer


class TraceContext:
    def __init__(
        self,
        name: str,
        request_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        tracer: Optional[Tracer] = None,
    ) -> None:
        self.name = name
        self.request_id = request_id
        self.parent_span_id = parent_span_id
        self.tags = tags
        self.span: Optional[Span] = None
        # Use provided tracer or shared global tracer
        self._tracer = tracer or get_global_tracer()

    def __enter__(self) -> Span:
        self.span = self._tracer.start_span(
            self.name,
            request_id=self.request_id,
            parent_span_id=self.parent_span_id,
            tags=self.tags,
        )
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.span:
            self._tracer.end_span(self.span)


# ==========================================================================
# Health checks
# ==========================================================================


@dataclass
class HealthStatus:
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: float
    checks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "checks": self.checks,
            "message": self.message,
        }


class HealthChecker:
    def __init__(self) -> None:
        self._checks: Dict[str, callable] = {}

    def register_check(self, name: str, check_func: callable) -> None:
        self._checks[name] = check_func

    def check_health(self) -> HealthStatus:
        checks: Dict[str, Dict[str, Any]] = {}
        all_healthy = True

        for name, check_func in self._checks.items():
            try:
                status, message, details = check_func()
                checks[name] = {
                    "status": "healthy" if status else "unhealthy",
                    "message": message,
                    "details": details,
                }
                if not status:
                    all_healthy = False
            except Exception as e:
                checks[name] = {
                    "status": "unhealthy",
                    "message": f"Check failed: {str(e)}",
                    "details": {},
                }
                all_healthy = False
                logger.error(f"Health check '{name}' failed: {e}", exc_info=True)

        overall_status = "healthy" if all_healthy else "unhealthy"
        return HealthStatus(status=overall_status, timestamp=time.time(), checks=checks)
