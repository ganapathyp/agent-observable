"""Unit tests for core observability primitives."""
import pytest
import time
from agent_observable_core.observability import (
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


class TestRequestContext:
    """Test request ID context management."""

    def test_generate_request_id(self):
        """Request IDs are unique UUIDs."""
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert id1 != id2
        assert len(id1) > 0

    def test_get_set_request_id(self):
        """Can get and set request ID."""
        assert get_request_id() is None
        set_request_id("test-123")
        assert get_request_id() == "test-123"
        set_request_id(None)
        assert get_request_id() is None

    def test_request_context_manager(self):
        """RequestContext sets and restores request ID."""
        assert get_request_id() is None
        with RequestContext("ctx-123"):
            assert get_request_id() == "ctx-123"
        assert get_request_id() is None

    def test_request_context_auto_generate(self):
        """RequestContext generates ID if not provided."""
        with RequestContext() as ctx:
            assert ctx.request_id is not None
            assert get_request_id() == ctx.request_id


class TestMetricsCollector:
    """Test metrics collection."""

    def test_increment_counter(self):
        """Can increment counters."""
        collector = MetricsCollector()
        collector.increment_counter("test.counter")
        assert collector.get_counter("test.counter") == 1.0
        collector.increment_counter("test.counter", 2.5)
        assert collector.get_counter("test.counter") == 3.5

    def test_set_gauge(self):
        """Can set gauges."""
        collector = MetricsCollector()
        collector.set_gauge("test.gauge", 42.0)
        assert collector.get_gauge("test.gauge") == 42.0
        collector.set_gauge("test.gauge", 100.0)
        assert collector.get_gauge("test.gauge") == 100.0

    def test_record_histogram(self):
        """Can record histogram values."""
        collector = MetricsCollector()
        collector.record_histogram("test.hist", 10.0)
        collector.record_histogram("test.hist", 20.0)
        collector.record_histogram("test.hist", 30.0)
        values = collector.get_histogram_values("test.hist")
        assert len(values) == 3
        assert values[0].value == 10.0
        assert values[1].value == 20.0
        assert values[2].value == 30.0

    def test_histogram_max_samples(self):
        """Histogram respects max_samples limit."""
        collector = MetricsCollector(max_samples=2)
        collector.record_histogram("test.hist", 1.0)
        collector.record_histogram("test.hist", 2.0)
        collector.record_histogram("test.hist", 3.0)
        values = collector.get_histogram_values("test.hist")
        assert len(values) == 2  # Only last 2 samples
        assert values[0].value == 2.0
        assert values[1].value == 3.0


class TestErrorTracker:
    """Test error tracking."""

    def test_record_error(self):
        """Can record errors."""
        tracker = ErrorTracker()
        error = ValueError("test error")
        tracker.record_error(error, request_id="req-123", agent_name="test-agent")
        summary = tracker.get_error_summary()
        assert summary["total_errors"] == 1
        assert len(summary["recent_errors"]) == 1
        assert summary["recent_errors"][0]["error_type"] == "ValueError"
        assert summary["recent_errors"][0]["request_id"] == "req-123"

    def test_error_aggregation(self):
        """Errors are aggregated by type and message."""
        tracker = ErrorTracker()
        error1 = ValueError("test error")
        error2 = ValueError("test error")
        tracker.record_error(error1)
        tracker.record_error(error2)
        summary = tracker.get_error_summary()
        assert summary["total_errors"] == 2
        # Check that error counts are tracked
        assert any(count >= 2 for count in summary["error_counts"].values())


class TestTracer:
    """Test distributed tracing."""

    def test_start_end_span(self):
        """Can start and end spans."""
        tracer = Tracer()
        span = tracer.start_span("test.span", request_id="req-123")
        assert span.name == "test.span"
        assert span.request_id == "req-123"
        assert span.start_time > 0
        assert span.end_time is None
        tracer.end_span(span)
        assert span.end_time is not None
        assert span.duration_ms is not None

    def test_get_trace(self):
        """Can retrieve spans by request ID."""
        tracer = Tracer()
        span1 = tracer.start_span("span1", request_id="req-123")
        span2 = tracer.start_span("span2", request_id="req-123")
        span3 = tracer.start_span("span3", request_id="req-456")
        tracer.end_span(span1)
        tracer.end_span(span2)
        tracer.end_span(span3)
        trace = tracer.get_trace("req-123")
        assert len(trace) == 2
        assert all(s.request_id == "req-123" for s in trace)

    def test_trace_context_manager(self):
        """TraceContext manages span lifecycle."""
        with TraceContext("test.span", request_id="req-123") as span:
            assert span.name == "test.span"
            assert span.request_id == "req-123"
            assert span.end_time is None
        # Span should be ended after context exit
        assert span.end_time is not None


class TestHealthChecker:
    """Test health checks."""

    def test_register_and_check(self):
        """Can register and run health checks."""
        checker = HealthChecker()

        def healthy_check():
            return True, "OK", {}

        def unhealthy_check():
            return False, "Failed", {"reason": "test"}

        checker.register_check("test1", healthy_check)
        checker.register_check("test2", unhealthy_check)
        status = checker.check_health()
        assert status.status == "unhealthy"
        assert "test1" in status.checks
        assert "test2" in status.checks
        assert status.checks["test1"]["status"] == "healthy"
        assert status.checks["test2"]["status"] == "unhealthy"

    def test_health_check_exception(self):
        """Exceptions in health checks are handled."""
        checker = HealthChecker()

        def failing_check():
            raise RuntimeError("check failed")

        checker.register_check("failing", failing_check)
        status = checker.check_health()
        assert status.status == "unhealthy"
        assert status.checks["failing"]["status"] == "unhealthy"
        assert "Check failed" in status.checks["failing"]["message"]


class TestObservabilityConfig:
    """Test observability configuration."""

    def test_default_config(self):
        """Default config has sensible defaults."""
        config = ObservabilityConfig()
        assert config.metrics_max_samples == 1000
        assert config.error_tracker_max_errors == 1000
        assert config.tracer_max_spans == 1000

    def test_custom_config(self):
        """Can create config with custom values."""
        config = ObservabilityConfig(
            metrics_max_samples=500,
            error_tracker_max_errors=200,
            tracer_max_spans=300,
        )
        assert config.metrics_max_samples == 500
        assert config.error_tracker_max_errors == 200
        assert config.tracer_max_spans == 300

    def test_create_components(self):
        """Can create components from config."""
        config = ObservabilityConfig(metrics_max_samples=100, error_tracker_max_errors=50, tracer_max_spans=75)
        collector = config.create_metrics_collector()
        assert isinstance(collector, MetricsCollector)
        tracker = config.create_error_tracker()
        assert isinstance(tracker, ErrorTracker)
        tracer = config.create_tracer()
        assert isinstance(tracer, Tracer)
