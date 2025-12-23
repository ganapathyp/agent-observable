"""Production observability: Request IDs, Metrics, Tracing, Error Tracking, Health Checks."""
import uuid
import time
import logging
import threading
import os
import sys
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict, deque
from contextvars import ContextVar
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Request ID context variable (thread-safe, async-safe)
_request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


# ============================================================================
# Request ID Correlation
# ============================================================================

def generate_request_id() -> str:
    """Generate a unique request ID.
    
    Returns:
        UUID-based request ID string
    """
    return str(uuid.uuid4())


def get_request_id() -> Optional[str]:
    """Get current request ID from context.
    
    Returns:
        Current request ID or None
    """
    return _request_id.get()


def set_request_id(request_id: Optional[str]) -> None:
    """Set request ID in context.
    
    Args:
        request_id: Request ID to set (or None to clear)
    """
    _request_id.set(request_id)


class RequestContext:
    """Context manager for request ID correlation."""
    
    def __init__(self, request_id: Optional[str] = None):
        """Initialize request context.
        
        Args:
            request_id: Optional request ID (generates new if None)
        """
        self.request_id = request_id or generate_request_id()
        self._token = None
    
    def __enter__(self):
        """Enter context - set request ID."""
        self._token = _request_id.set(self.request_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore previous request ID."""
        if self._token:
            _request_id.reset(self._token)


# ============================================================================
# Metrics Collection
# ============================================================================

@dataclass
class MetricValue:
    """Single metric value with timestamp."""
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Simple in-memory metrics collector (Prometheus-style) with file persistence."""
    
    def __init__(self, max_samples: int = 1000, metrics_file: Optional[Path] = None):
        """Initialize metrics collector.
        
        Args:
            max_samples: Maximum samples to keep per metric
            metrics_file: Optional path to persist metrics (for cross-process sharing)
        """
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self._lock = threading.Lock()
        
        # File persistence for cross-process sharing
        if metrics_file is None:
            # None means in-memory only (no file I/O) - used for testing
            self._metrics_file = None
        else:
            self._metrics_file = Path(metrics_file)
            self._metrics_file.parent.mkdir(parents=True, exist_ok=True)
            # Load existing metrics from file
            self._load_from_file()
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric.
        
        Args:
            name: Metric name
            value: Increment value (default: 1.0)
            labels: Optional labels (for future use)
        """
        # Track collection latency
        collection_start = time.time()
        
        with self._lock:
            self._counters[name] += value
        
        # Save outside lock to avoid blocking
        self._save_to_file()
        
        # Track metrics collection latency (only for observability metrics to avoid recursion)
        if not name.startswith("observability."):
            collection_latency = (time.time() - collection_start) * 1000
            try:
                from .metric_names import OBSERVABILITY_METRICS_COLLECTION_LATENCY_MS
                self.record_histogram(OBSERVABILITY_METRICS_COLLECTION_LATENCY_MS, collection_latency)
            except Exception:
                pass  # Don't fail on metrics tracking
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric.
        
        Args:
            name: Metric name
            value: Gauge value
            labels: Optional labels (for future use)
        """
        # Track collection latency
        collection_start = time.time()
        
        with self._lock:
            self._gauges[name] = value
        
        # Save outside lock to avoid blocking
        self._save_to_file()
        
        # Track metrics collection latency (only for observability metrics to avoid recursion)
        if not name.startswith("observability."):
            collection_latency = (time.time() - collection_start) * 1000
            try:
                from .metric_names import OBSERVABILITY_METRICS_COLLECTION_LATENCY_MS
                self.record_histogram(OBSERVABILITY_METRICS_COLLECTION_LATENCY_MS, collection_latency)
            except Exception:
                pass  # Don't fail on metrics tracking
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram value.
        
        Args:
            name: Metric name
            value: Value to record
            labels: Optional labels (for future use)
        """
        with self._lock:
            self._histograms[name].append(MetricValue(
                value=value,
                timestamp=time.time(),
                labels=labels or {}
            ))
    
    def get_counter(self, name: str) -> float:
        """Get counter value.
        
        Args:
            name: Metric name
            
        Returns:
            Counter value
        """
        with self._lock:
            return self._counters.get(name, 0.0)
    
    def get_gauge(self, name: str) -> float:
        """Get gauge value.
        
        Args:
            name: Metric name
            
        Returns:
            Gauge value
        """
        with self._lock:
            return self._gauges.get(name, 0.0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics.
        
        Args:
            name: Metric name
            
        Returns:
            Dict with min, max, avg, count, p50, p95, p99
        """
        with self._lock:
            return self._get_histogram_stats_unlocked(name)
    
    def _get_histogram_stats_unlocked(self, name: str) -> Dict[str, float]:
        """Get histogram statistics without acquiring lock (caller must hold lock).
        
        Args:
            name: Metric name
            
        Returns:
            Dict with min, max, avg, count, p50, p95, p99
        """
        values = [m.value for m in self._histograms.get(name, deque())]
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        return {
            "count": count,
            "min": min(sorted_values),
            "max": max(sorted_values),
            "avg": sum(sorted_values) / count,
            "p50": sorted_values[int(count * 0.50)] if count > 0 else 0,
            "p95": sorted_values[int(count * 0.95)] if count > 0 else 0,
            "p99": sorted_values[int(count * 0.99)] if count > 0 else 0,
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in Prometheus-style format.
        
        Returns:
            Dict with counters, gauges, and histograms
        """
        # Reload from file to get latest metrics from other processes (outside lock)
        # Skip if in-memory only mode
        if self._metrics_file is not None:
            self._load_from_file()
        
        with self._lock:
            histograms = {}
            for name in self._histograms:
                # Get histogram stats without lock (we're already locked)
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
    
    def get_golden_signals(self) -> Dict[str, Any]:
        """Calculate Golden Signals for LLM production monitoring.
        
        Returns:
            Dict with the 5 Golden Signals:
            - success_rate: Workflow success rate (%)
            - p95_latency: 95th percentile latency (ms)
            - cost_per_successful_task: Cost per successful task (USD)
            - user_confirmed_correctness: User-confirmed correctness rate (%)
            - policy_violation_rate: Policy violation rate (%)
        """
        # Reload from file to get latest metrics (if file persistence enabled)
        if self._metrics_file is not None:
            self._load_from_file()
        
        with self._lock:
            # Import metric names (inside lock to avoid circular import issues)
            from .metric_names import (
                WORKFLOW_RUNS,
                WORKFLOW_SUCCESS,
                WORKFLOW_LATENCY_MS,
                LLM_COST_TOTAL,
                LLM_QUALITY_USER_CONFIRMED_CORRECT,
                LLM_QUALITY_USER_CONFIRMED_INCORRECT,
                POLICY_VIOLATIONS_TOTAL
            )
            
            # 1. Success Rate
            workflow_runs = self._counters.get(WORKFLOW_RUNS, 0.0)
            workflow_success = self._counters.get(WORKFLOW_SUCCESS, 0.0)
            success_rate = (workflow_success / workflow_runs * 100) if workflow_runs > 0 else 0.0
            
            # 2. p95 Latency (use unlocked version since we already have the lock)
            workflow_latency_stats = self._get_histogram_stats_unlocked(WORKFLOW_LATENCY_MS)
            p95_latency = workflow_latency_stats.get("p95", 0.0)
            
            # 3. Cost per Successful Task
            total_cost = self._counters.get(LLM_COST_TOTAL, 0.0)
            cost_per_successful_task = (total_cost / workflow_success) if workflow_success > 0 else 0.0
            
            # 4. User-Confirmed Correctness (if available)
            user_correct = self._counters.get(LLM_QUALITY_USER_CONFIRMED_CORRECT, 0.0)
            user_incorrect = self._counters.get(LLM_QUALITY_USER_CONFIRMED_INCORRECT, 0.0)
            total_feedback = user_correct + user_incorrect
            user_confirmed_correctness = (user_correct / total_feedback * 100) if total_feedback > 0 else None
            
            # 5. Policy Violation Rate
            total_violations = self._counters.get(POLICY_VIOLATIONS_TOTAL, 0.0)
            policy_violation_rate = (total_violations / workflow_runs * 100) if workflow_runs > 0 else 0.0
            
            return {
                "success_rate": round(success_rate, 2),
                "p95_latency_ms": round(p95_latency, 2),
                "cost_per_successful_task_usd": round(cost_per_successful_task, 4),
                "user_confirmed_correctness_percent": round(user_confirmed_correctness, 2) if user_confirmed_correctness is not None else None,
                "policy_violation_rate_percent": round(policy_violation_rate, 2),
                "metadata": {
                    "workflow_runs": int(workflow_runs),
                    "workflow_success": int(workflow_success),
                    "total_cost_usd": round(total_cost, 4),
                    "total_violations": int(total_violations),
                    "total_feedback": int(total_feedback) if total_feedback > 0 else None
                }
            }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
        # Save outside lock to avoid blocking
        self._save_to_file()
    
    def _save_to_file(self):
        """Save current metrics to file (for cross-process sharing).
        
        Note: Called without lock to avoid blocking. Uses lock internally to read data.
        """
        # Skip file I/O if metrics_file is None (in-memory only mode)
        if self._metrics_file is None:
            return
        
        try:
            # Acquire lock to read current state
            with self._lock:
                # Calculate histogram stats inline
                histograms = {}
                for name in self._histograms.keys():
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
                
                # Copy data while holding lock
                metrics_data = {
                    "counters": dict(self._counters),
                    "gauges": dict(self._gauges),
                    "histograms": histograms,
                    "timestamp": time.time()
                }
            
            # Do file I/O outside lock to avoid blocking
            with open(self._metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save metrics to file: {e}")
    
    def _load_from_file(self):
        """Load metrics from file (for cross-process sharing)."""
        # Skip file I/O if metrics_file is None (in-memory only mode)
        if self._metrics_file is None:
            return
        
        try:
            if self._metrics_file.exists():
                with open(self._metrics_file, 'r') as f:
                    data = json.load(f)
                    # Load counters and gauges with lock
                    with self._lock:
                        if "counters" in data:
                            self._counters.update(data["counters"])
                        if "gauges" in data:
                            self._gauges.update(data["gauges"])
                        # Note: Histograms are not fully restored (would need full data)
                        # but stats are available
        except Exception as e:
            logger.debug(f"Could not load metrics from file (first run?): {e}")


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance.
    
    Returns:
        Global MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        # Check if running in test mode (pytest sets this env var or we detect it)
        # Use environment variable first (most reliable), then check sys.modules
        is_test_mode = (
            os.environ.get('PYTEST_CURRENT_TEST') is not None or
            os.environ.get('TESTING') == '1' or
            'pytest' in sys.modules or 
            any('pytest' in arg for arg in sys.argv)
        )
        # Use in-memory mode for tests to avoid file locking
        # In production, use configured path from PathConfig
        if is_test_mode:
            _metrics_collector = MetricsCollector(metrics_file=None)  # In-memory only
        else:
            # Use configured path from PathConfig
            try:
                from taskpilot.core.config import get_paths
                paths = get_paths()
                metrics_file = paths.metrics_file
            except Exception:
                # Fallback to old behavior if config not available
                metrics_file = None  # Will use default in MetricsCollector
            _metrics_collector = MetricsCollector(metrics_file=metrics_file)
    return _metrics_collector


# ============================================================================
# Error Tracking & Aggregation
# ============================================================================

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
    count: int = 1  # Aggregation count


class ErrorTracker:
    """Error tracking and aggregation."""
    
    def __init__(self, max_errors: int = 1000):
        """Initialize error tracker.
        
        Args:
            max_errors: Maximum errors to keep in memory
        """
        self._errors: deque = deque(maxlen=max_errors)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def record_error(
        self,
        error: Exception,
        request_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Record an error.
        
        Args:
            error: Exception that occurred
            request_id: Optional request ID for correlation
            agent_name: Optional agent name
            context: Optional additional context
        """
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
                count=self._error_counts[error_key]
            )
            
            self._errors.append(error_record)
            
            # Log error with request ID
            logger.error(
                f"[ERROR] {error_record.error_type}: {error_record.error_message} "
                f"(request_id={error_record.request_id}, agent={agent_name})",
                exc_info=error
            )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary statistics.
        
        Returns:
            Dict with error counts and recent errors
        """
        with self._lock:
            recent_errors = [
                {
                    "error_type": e.error_type,
                    "error_message": e.error_message[:200],
                    "request_id": e.request_id,
                    "agent_name": e.agent_name,
                    "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                    "count": e.count
                }
                for e in list(self._errors)[-10:]  # Last 10 errors
            ]
            
            return {
                "total_errors": len(self._errors),
                "error_counts": dict(self._error_counts),
                "recent_errors": recent_errors
            }
    
    def get_errors_by_type(self, error_type: str) -> List[ErrorRecord]:
        """Get all errors of a specific type.
        
        Args:
            error_type: Error type to filter by
            
        Returns:
            List of error records
        """
        with self._lock:
            return [e for e in self._errors if e.error_type == error_type]


# Global error tracker
_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get global error tracker instance.
    
    Returns:
        Global ErrorTracker instance
    """
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


# ============================================================================
# Distributed Tracing
# ============================================================================

@dataclass
class Span:
    """Tracing span."""
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
        """Get span duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "span_id": self.span_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "request_id": self.request_id,
            "parent_span_id": self.parent_span_id,
            "tags": self.tags,
            "logs": self.logs
        }


class Tracer:
    """Simple distributed tracer."""
    
    def __init__(self, max_spans: int = 1000, trace_file: Optional[Path] = None):
        """Initialize tracer.
        
        Args:
            max_spans: Maximum spans to keep in memory
            trace_file: Optional path to JSONL file for persistent storage
        """
        self._spans: deque = deque(maxlen=max_spans)
        self._active_spans: Dict[str, Span] = {}
        self._lock = threading.Lock()
        self._trace_file = trace_file
        if self._trace_file:
            # Ensure directory exists
            self._trace_file.parent.mkdir(parents=True, exist_ok=True)
    
    def start_span(
        self,
        name: str,
        request_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Span:
        """Start a new span.
        
        Args:
            name: Span name
            request_id: Optional request ID
            parent_span_id: Optional parent span ID
            tags: Optional tags
            
        Returns:
            Started span
        """
        span = Span(
            name=name,
            start_time=time.time(),
            request_id=request_id or get_request_id(),
            parent_span_id=parent_span_id,
            tags=tags or {}
        )
        
        with self._lock:
            self._active_spans[span.span_id] = span
        
        # Create OpenTelemetry span immediately for parent-child relationships
        # This ensures child spans can find their parent even if export is async
        try:
            from .otel_integration import create_otel_span_for_tracking
            create_otel_span_for_tracking(span)
        except Exception:
            # Don't fail if OpenTelemetry is not available or fails
            pass
        
        return span
    
    def end_span(self, span: Span):
        """End a span.
        
        Args:
            span: Span to end
        """
        span.end_time = time.time()
        
        with self._lock:
            if span.span_id in self._active_spans:
                del self._active_spans[span.span_id]
            self._spans.append(span)
            
            # Auto-persist to disk if trace_file is set
            if hasattr(self, '_trace_file') and self._trace_file:
                try:
                    self._persist_span(span)
                except Exception:
                    # Don't fail if persistence fails
                    pass
            
            # Export to OpenTelemetry if available
            try:
                from .otel_integration import export_span_to_otel
                # Note: create_otel_span_for_tracking already stored the span in _span_contexts
                # when the span started, so we don't need to store it again here
                
                # Pass our internal span_id so OTEL can look up and update the existing span
                export_span_to_otel(
                    span_name=span.name,
                    start_time=span.start_time,
                    end_time=span.end_time,
                    request_id=span.request_id,
                    parent_span_id=span.parent_span_id,
                    span_id=span.span_id,  # Pass our span_id for context tracking
                    tags=span.tags,
                    logs=span.logs
                )
            except ImportError:
                # OpenTelemetry not available, skip
                pass
            except Exception:
                # Don't fail if OpenTelemetry export fails
                pass
    
    def get_trace(self, request_id: str) -> List[Span]:
        """Get all spans for a request ID.
        
        Args:
            request_id: Request ID to filter by
            
        Returns:
            List of spans for the request
        """
        with self._lock:
            return [s for s in self._spans if s.request_id == request_id]
    
    def get_recent_spans(self, limit: int = 100) -> List[Span]:
        """Get recent spans.
        
        Args:
            limit: Maximum number of spans to return
            
        Returns:
            List of recent spans
        """
        with self._lock:
            return list(self._spans)[-limit:]
    
    def _persist_span(self, span: Span):
        """Persist a span to disk (JSONL format).
        
        Args:
            span: Span to persist
        """
        if not self._trace_file:
            return
        
        try:
            with open(self._trace_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(span.to_dict(), default=str) + '\n')
        except Exception as e:
            logger.debug(f"Failed to persist span: {e}")
    
    def load_from_file(self, trace_file: Optional[Path] = None) -> int:
        """Load spans from persistent storage file.
        
        Args:
            trace_file: Path to JSONL file (uses self._trace_file if None)
            
        Returns:
            Number of spans loaded
        """
        file_path = trace_file or self._trace_file
        if not file_path or not file_path.exists():
            return 0
        
        loaded = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            span_dict = json.loads(line)
                            # Reconstruct Span object
                            span = Span(
                                name=span_dict['name'],
                                start_time=span_dict['start_time'],
                                end_time=span_dict.get('end_time'),
                                request_id=span_dict.get('request_id'),
                                parent_span_id=span_dict.get('parent_span_id'),
                                span_id=span_dict['span_id'],
                                tags=span_dict.get('tags', {}),
                                logs=span_dict.get('logs', [])
                            )
                            with self._lock:
                                self._spans.append(span)
                            loaded += 1
                        except Exception as e:
                            logger.debug(f"Failed to load span from line: {e}")
                            continue
        except Exception as e:
            logger.warning(f"Failed to load traces from file: {e}")
        
        return loaded


# Global tracer
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get global tracer instance.
    
    Returns:
        Global Tracer instance
    """
    global _tracer
    if _tracer is None:
        # Default trace file in taskpilot directory
        # __file__ is src/core/observability.py, so:
        # parent = src/core, parent.parent = src, parent.parent.parent = taskpilot
        # Use configured path from PathConfig
        try:
            from taskpilot.core.config import get_paths
            paths = get_paths()
            trace_file = paths.traces_file
        except Exception:
            # Fallback to old behavior if config not available
            trace_file = Path(__file__).parent.parent.parent / "traces.jsonl"
        _tracer = Tracer(trace_file=trace_file)
        # Load existing traces
        _tracer.load_from_file()
    return _tracer


class TraceContext:
    """Context manager for tracing spans."""
    
    def __init__(
        self,
        name: str,
        request_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Initialize trace context.
        
        Args:
            name: Span name
            request_id: Optional request ID
            parent_span_id: Optional parent span ID
            tags: Optional tags
        """
        self.name = name
        self.request_id = request_id
        self.parent_span_id = parent_span_id
        self.tags = tags
        self.span: Optional[Span] = None
    
    def __enter__(self) -> Span:
        """Enter context - start span."""
        self.span = get_tracer().start_span(
            self.name,
            request_id=self.request_id,
            parent_span_id=self.parent_span_id,
            tags=self.tags
        )
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - end span."""
        if self.span:
            get_tracer().end_span(self.span)


# ============================================================================
# Health Checks
# ============================================================================

@dataclass
class HealthStatus:
    """Health check status."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: float
    checks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "checks": self.checks,
            "message": self.message
        }


class HealthChecker:
    """Health check system."""
    
    def __init__(self):
        """Initialize health checker."""
        self._checks: Dict[str, callable] = {}
    
    def register_check(self, name: str, check_func: callable):
        """Register a health check.
        
        Args:
            name: Check name
            check_func: Function that returns (status: bool, message: str, details: dict)
        """
        self._checks[name] = check_func
    
    def check_health(self) -> HealthStatus:
        """Run all health checks.
        
        Returns:
            HealthStatus with overall status and individual check results
        """
        checks = {}
        all_healthy = True
        any_degraded = False
        
        for name, check_func in self._checks.items():
            try:
                status, message, details = check_func()
                checks[name] = {
                    "status": "healthy" if status else "unhealthy",
                    "message": message,
                    "details": details
                }
                if not status:
                    all_healthy = False
            except Exception as e:
                checks[name] = {
                    "status": "unhealthy",
                    "message": f"Check failed: {str(e)}",
                    "details": {}
                }
                all_healthy = False
                logger.error(f"Health check '{name}' failed: {e}", exc_info=True)
        
        overall_status = "healthy" if all_healthy else "unhealthy"
        
        return HealthStatus(
            status=overall_status,
            timestamp=time.time(),
            checks=checks
        )


# Global health checker
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get global health checker instance.
    
    Returns:
        Global HealthChecker instance
    """
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


# ============================================================================
# Convenience Functions
# ============================================================================

def record_metric(name: str, value: float, metric_type: str = "histogram"):
    """Record a metric (convenience function).
    
    Args:
        name: Metric name
        value: Metric value
        metric_type: "counter", "gauge", or "histogram"
    """
    collector = get_metrics_collector()
    if metric_type == "counter":
        collector.increment_counter(name, value)
    elif metric_type == "gauge":
        collector.set_gauge(name, value)
    elif metric_type == "histogram":
        collector.record_histogram(name, value)


def record_error(error: Exception, **context):
    """Record an error (convenience function).
    
    Args:
        error: Exception to record
        **context: Additional context
    """
    get_error_tracker().record_error(
        error,
        request_id=get_request_id(),
        context=context
    )
