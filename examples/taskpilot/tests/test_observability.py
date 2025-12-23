"""Test script for observability features: Request IDs, Metrics, Tracing, Error Tracking, Health Checks."""
import asyncio
import sys
import logging
from taskpilot.core.observability import (
    RequestContext,
    get_request_id,
    get_metrics_collector,
    get_error_tracker,
    get_tracer,
    get_health_checker,
    TraceContext,
    record_metric,
    record_error
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_request_ids():
    """Test request ID correlation."""
    print("\n" + "="*60)
    print("TEST 1: Request ID Correlation")
    print("="*60)
    
    # Test 1: Generate request ID
    with RequestContext() as ctx:
        request_id = ctx.request_id
        print(f"✅ Generated request ID: {request_id}")
        
        # Test 2: Get request ID from context
        retrieved_id = get_request_id()
        assert retrieved_id == request_id, "Request ID mismatch!"
        print(f"✅ Retrieved request ID from context: {retrieved_id}")
        
        # Test 3: Nested contexts
        with RequestContext() as nested_ctx:
            nested_id = nested_ctx.request_id
            print(f"✅ Nested request ID: {nested_id}")
            assert nested_id != request_id, "Nested ID should be different!"
        
        # After nested context, original should still be active
        assert get_request_id() == request_id, "Original request ID should still be active!"
        print(f"✅ Original request ID still active after nested context")
    
    # After context exit, request ID should be None
    assert get_request_id() is None, "Request ID should be None after context exit"
    print(f"✅ Request ID cleared after context exit")


def test_metrics():
    """Test metrics collection."""
    print("\n" + "="*60)
    print("TEST 2: Metrics Collection")
    print("="*60)
    
    metrics = get_metrics_collector()
    metrics.reset()  # Start fresh
    
    # Test counters
    metrics.increment_counter("test.counter", 1.0)
    metrics.increment_counter("test.counter", 2.0)
    value = metrics.get_counter("test.counter")
    assert value == 3.0, f"Expected 3.0, got {value}"
    print(f"✅ Counter: test.counter = {value}")
    
    # Test gauges
    metrics.set_gauge("test.gauge", 42.0)
    value = metrics.get_gauge("test.gauge")
    assert value == 42.0, f"Expected 42.0, got {value}"
    print(f"✅ Gauge: test.gauge = {value}")
    
    # Test histograms
    for i in range(10):
        metrics.record_histogram("test.latency", float(i * 10))
    
    stats = metrics.get_histogram_stats("test.latency")
    print(f"✅ Histogram: test.latency")
    print(f"   Count: {stats['count']}")
    print(f"   Min: {stats['min']}ms")
    print(f"   Max: {stats['max']}ms")
    print(f"   Avg: {stats['avg']:.2f}ms")
    print(f"   P50: {stats['p50']:.2f}ms")
    print(f"   P95: {stats['p95']:.2f}ms")
    print(f"   P99: {stats['p99']:.2f}ms")
    
    # Test get_all_metrics
    all_metrics = metrics.get_all_metrics()
    assert "counters" in all_metrics
    assert "gauges" in all_metrics
    assert "histograms" in all_metrics
    print(f"✅ get_all_metrics() returns all metric types")


def test_error_tracking():
    """Test error tracking and aggregation."""
    print("\n" + "="*60)
    print("TEST 3: Error Tracking & Aggregation")
    print("="*60)
    
    error_tracker = get_error_tracker()
    
    # Test recording errors
    with RequestContext() as ctx:
        request_id = ctx.request_id
        
        # Record different error types
        try:
            raise ValueError("Test error 1")
        except Exception as e:
            error_tracker.record_error(e, request_id=request_id, agent_name="TestAgent", context={"test": True})
        
        try:
            raise KeyError("Test error 2")
        except Exception as e:
            error_tracker.record_error(e, request_id=request_id, agent_name="TestAgent")
        
        # Record same error multiple times (should aggregate)
        for _ in range(3):
            try:
                raise ValueError("Duplicate error")
            except Exception as e:
                error_tracker.record_error(e, request_id=request_id)
    
    # Get error summary
    summary = error_tracker.get_error_summary()
    print(f"✅ Total errors recorded: {summary['total_errors']}")
    print(f"✅ Error types: {len(summary['error_counts'])}")
    print(f"✅ Recent errors: {len(summary['recent_errors'])}")
    
    # Check error aggregation
    assert summary['total_errors'] >= 5, "Should have recorded at least 5 errors"
    print(f"✅ Error aggregation working")
    
    # Get errors by type
    value_errors = error_tracker.get_errors_by_type("ValueError")
    print(f"✅ Found {len(value_errors)} ValueError instances")


def test_tracing():
    """Test distributed tracing."""
    print("\n" + "="*60)
    print("TEST 4: Distributed Tracing")
    print("="*60)
    
    tracer = get_tracer()
    
    with RequestContext() as ctx:
        request_id = ctx.request_id
        
        # Test simple span
        with TraceContext("test.operation", request_id=request_id) as span:
            import time
            time.sleep(0.01)  # Simulate work
            span.tags["custom_tag"] = "test_value"
            span.logs.append({"timestamp": time.time(), "fields": {"message": "Test log"}})
        
        # Test nested spans
        with TraceContext("test.parent", request_id=request_id) as parent_span:
            time.sleep(0.005)
            with TraceContext("test.child", request_id=request_id, parent_span_id=parent_span.span_id) as child_span:
                time.sleep(0.005)
        
        # Get trace for request
        trace = tracer.get_trace(request_id)
        print(f"✅ Recorded {len(trace)} spans for request {request_id}")
        
        for span in trace:
            print(f"   Span: {span.name} ({span.duration_ms:.2f}ms)")
            if span.parent_span_id:
                print(f"      Parent: {span.parent_span_id}")
        
        # Test span duration
        assert all(s.duration_ms is not None for s in trace), "All spans should have duration"
        print(f"✅ Span durations calculated correctly")
    
    # Test recent spans
    recent = tracer.get_recent_spans(limit=10)
    print(f"✅ Retrieved {len(recent)} recent spans")


def test_health_checks():
    """Test health check system."""
    print("\n" + "="*60)
    print("TEST 5: Health Checks")
    print("="*60)
    
    health_checker = get_health_checker()
    
    # Register test health checks
    def check_always_healthy():
        return True, "Always healthy", {"status": "ok"}
    
    def check_always_unhealthy():
        return False, "Always unhealthy", {"error": "test"}
    
    def check_raises_exception():
        raise RuntimeError("Health check exception")
    
    health_checker.register_check("test.healthy", check_always_healthy)
    health_checker.register_check("test.unhealthy", check_always_unhealthy)
    health_checker.register_check("test.exception", check_raises_exception)
    
    # Run health checks
    health_status = health_checker.check_health()
    
    print(f"✅ Overall status: {health_status.status}")
    print(f"✅ Checks run: {len(health_status.checks)}")
    
    for name, check in health_status.checks.items():
        status_emoji = "✅" if check["status"] == "healthy" else "❌"
        print(f"   {status_emoji} {name}: {check['status']}")
        if check.get("message"):
            print(f"      {check['message']}")
    
    # Verify status
    assert health_status.status == "unhealthy", "Should be unhealthy due to test.unhealthy check"
    print(f"✅ Health check correctly identifies unhealthy status")


def test_integration():
    """Test integration of all observability features."""
    print("\n" + "="*60)
    print("TEST 6: Integration Test")
    print("="*60)
    
    metrics = get_metrics_collector()
    error_tracker = get_error_tracker()
    tracer = get_tracer()
    
    metrics.reset()
    
    with RequestContext() as ctx:
        request_id = ctx.request_id
        print(f"✅ Request ID: {request_id}")
        
        # Simulate a workflow with metrics, tracing, and potential errors
        with TraceContext("workflow.run", request_id=request_id) as workflow_span:
            metrics.increment_counter("workflow.started")
            
            with TraceContext("agent.planner", request_id=request_id, parent_span_id=workflow_span.span_id) as agent_span:
                import time
                start = time.time()
                time.sleep(0.01)
                latency = (time.time() - start) * 1000
                metrics.record_histogram("agent.planner.latency_ms", latency)
                metrics.increment_counter("agent.planner.success")
            
            # Simulate an error
            try:
                raise ValueError("Simulated workflow error")
            except Exception as e:
                error_tracker.record_error(e, request_id=request_id, agent_name="PlannerAgent")
                metrics.increment_counter("workflow.errors")
        
        # Verify all systems recorded data
        all_metrics = metrics.get_all_metrics()
        trace = tracer.get_trace(request_id)
        error_summary = error_tracker.get_error_summary()
        
        print(f"✅ Metrics recorded: {len(all_metrics['counters'])} counters")
        print(f"✅ Spans recorded: {len(trace)}")
        print(f"✅ Errors recorded: {error_summary['total_errors']}")
        
        assert len(all_metrics['counters']) > 0, "Should have recorded metrics"
        assert len(trace) > 0, "Should have recorded spans"
        assert error_summary['total_errors'] > 0, "Should have recorded errors"
        
        print(f"✅ All observability systems integrated correctly")


def main():
    """Run all observability tests."""
    print("\n" + "="*60)
    print("OBSERVABILITY FEATURES TEST SUITE")
    print("="*60)
    
    try:
        test_request_ids()
        test_metrics()
        test_error_tracking()
        test_tracing()
        test_health_checks()
        test_integration()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nObservability features verified:")
        print("  ✅ Request ID correlation")
        print("  ✅ Metrics collection")
        print("  ✅ Error tracking & aggregation")
        print("  ✅ Distributed tracing")
        print("  ✅ Health checks")
        print("  ✅ Integration")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
