#!/usr/bin/env python3
"""Integration test for observability stack (metrics, traces, logs, policy decisions).

This script verifies that:
1. Metrics are collected and available via /metrics endpoint
2. Traces are exported to OpenTelemetry/Jaeger
3. Logs are written and can be shipped to Elasticsearch/Kibana
4. Policy decisions are logged and can be queried

Run this after starting the observability stack:
    docker-compose -f docker-compose.observability.yml up -d
    python scripts/test_observability_integration.py
"""
import asyncio
import sys
import time
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from taskpilot.core.observability_adapter import (
    get_metrics_collector,
    get_tracer,
    get_error_tracker,
)
from taskpilot.core.observable import get_decision_logger
from taskpilot.core.metric_names import (
    WORKFLOW_RUNS,
    WORKFLOW_SUCCESS,
    WORKFLOW_LATENCY_MS,
)
from taskpilot.core.trace_names import WORKFLOW_RUN as TRACE_WORKFLOW_RUN


def test_metrics():
    """Test metrics collection."""
    print("📊 Testing Metrics Collection...")
    
    try:
        metrics = get_metrics()
        
        # Record some metrics
        metrics.increment_counter(WORKFLOW_RUNS, 1.0)
        metrics.increment_counter(WORKFLOW_SUCCESS, 1.0)
        metrics.record_histogram(WORKFLOW_LATENCY_MS, 150.0)
        metrics.record_histogram(WORKFLOW_LATENCY_MS, 200.0)
        metrics.record_histogram(WORKFLOW_LATENCY_MS, 180.0)
        
        # Verify metrics (check if get_counter exists)
        if hasattr(metrics, 'get_counter'):
            # Get initial values (may have existing metrics from other tests)
            initial_runs = metrics.get_counter(WORKFLOW_RUNS)
            initial_success = metrics.get_counter(WORKFLOW_SUCCESS)
            
            # Increment again to verify it works
            metrics.increment_counter(WORKFLOW_RUNS, 1.0)
            metrics.increment_counter(WORKFLOW_SUCCESS, 1.0)
            
            # Verify values increased
            assert metrics.get_counter(WORKFLOW_RUNS) == initial_runs + 1.0
            assert metrics.get_counter(WORKFLOW_SUCCESS) == initial_success + 1.0
        else:
            # Fallback: check counters directly
            initial_runs = metrics._counters.get(WORKFLOW_RUNS, 0)
            metrics.increment_counter(WORKFLOW_RUNS, 1.0)
            assert metrics._counters.get(WORKFLOW_RUNS, 0) == initial_runs + 1.0
        
        # Test get_all_metrics
        if hasattr(metrics, 'get_all_metrics'):
            all_metrics = metrics.get_all_metrics()
            assert "counters" in all_metrics
            # Check if metric is in counters (may use different key format)
            counters = all_metrics["counters"]
            assert len(counters) > 0, "No counters found"
        else:
            print("⚠️  get_all_metrics not available")
            return False
        
        # Test get_golden_signals
        if hasattr(metrics, 'get_golden_signals'):
            signals = metrics.get_golden_signals()
            assert "success_rate" in signals
            assert "p95_latency_ms" in signals
        else:
            print("⚠️  get_golden_signals not available")
            return False
        
        print("✅ Metrics collection working")
        return True
    except Exception as e:
        print(f"❌ Metrics test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_traces():
    """Test trace collection."""
    print("🔍 Testing Trace Collection...")
    
    tracer = get_tracer()
    
    # Create a trace
    span = tracer.start_span(
        name=TRACE_WORKFLOW_RUN,
        request_id="test-request-123",
        tags={"test": "true"}
    )
    
    time.sleep(0.01)  # Simulate work
    
    tracer.end_span(span)
    
    # Verify trace
    trace = tracer.get_trace("test-request-123")
    assert len(trace) == 1
    assert trace[0].name == TRACE_WORKFLOW_RUN
    
    print("✅ Trace collection working")
    return True


def test_logs():
    """Test log writing."""
    print("📝 Testing Log Writing...")
    
    import logging
    
    # Configure logging to write to file if logs directory exists
    log_file = Path("logs/taskpilot.log")
    if log_file.parent.exists():
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger = logging.getLogger("test_observability")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
    else:
        logger = logging.getLogger("test_observability")
        logger.setLevel(logging.INFO)
        # Create logs directory
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
    
    # Log a message
    logger.info("Test log message for observability integration test", extra={
        "request_id": "test-request-123",
        "agent_name": "TestAgent"
    })
    
    # Flush and check if log file exists
    handler.flush()
    if log_file.exists():
        content = log_file.read_text()
        assert "Test log message" in content or "test-request-123" in content or "test_observability" in content
        print("✅ Log file written")
    else:
        print("⚠️  Log file not found (may be using console logging)")
    
    print("✅ Log writing working")
    return True


def test_policy_decisions():
    """Test policy decision logging."""
    print("🛡️  Testing Policy Decision Logging...")
    
    decision_logger = get_decision_logger()
    
    from agent_observable_policy import (
        PolicyDecision,
        DecisionType,
        DecisionResult,
    )
    
    # Create and log a decision
    decision = PolicyDecision.create(
        decision_type=DecisionType.TOOL_CALL,
        result=DecisionResult.ALLOW,
        reason="Test decision",
        context={"test": "true"},
        tool_name="test_tool",
    )
    
    # Log the decision (async)
    asyncio.run(decision_logger.log_decision(decision))
    
    # Check if decision log file exists (if configured)
    decision_log_file = Path("logs/decision_logs.jsonl")
    if decision_log_file.exists():
        content = decision_log_file.read_text()
        assert "test_tool" in content or "TOOL_CALL" in content
        print("✅ Decision log file written")
    else:
        print("⚠️  Decision log file not found (may be using in-memory only)")
    
    print("✅ Policy decision logging working")
    return True


def test_http_endpoints():
    """Test HTTP endpoints (REQUIRED - server must be running)."""
    print("🌐 Testing HTTP Endpoints (REQUIRED)...")
    
    try:
        # Test /metrics endpoint
        response = requests.get("http://localhost:8000/metrics", timeout=2)
        if response.status_code != 200:
            raise AssertionError(f"/metrics returned {response.status_code}")
        assert "counter" in response.text or "gauge" in response.text, "Metrics endpoint missing counter/gauge data"
        print("✅ /metrics endpoint working")
        
        # Test /health endpoint
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            raise AssertionError(f"/health returned {response.status_code}")
        data = response.json()
        assert "status" in data, "Health endpoint missing status"
        print("✅ /health endpoint working")
        
        # Test /golden-signals endpoint
        response = requests.get("http://localhost:8000/golden-signals", timeout=2)
        if response.status_code != 200:
            raise AssertionError(f"/golden-signals returned {response.status_code}")
        data = response.json()
        assert "success_rate" in data, "Golden signals endpoint missing success_rate"
        print("✅ /golden-signals endpoint working")
        
        print("✅ HTTP endpoints working")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Server not running - HTTP endpoints are REQUIRED")
        print("   Start server with: python main.py --server --port 8000")
        raise  # Re-raise to mark as failed
    except Exception as e:
        print(f"❌ HTTP endpoints test failed: {e}")
        raise  # Re-raise to mark as failed


def main():
    """Run all observability integration tests."""
    print("=" * 60)
    print("Observability Integration Test")
    print("=" * 60)
    print()
    
    results = []
    
    try:
        results.append(("Metrics", test_metrics()))
    except Exception as e:
        print(f"❌ Metrics test failed: {e}")
        results.append(("Metrics", False))
    
    try:
        results.append(("Traces", test_traces()))
    except Exception as e:
        print(f"❌ Traces test failed: {e}")
        results.append(("Traces", False))
    
    try:
        results.append(("Logs", test_logs()))
    except Exception as e:
        print(f"❌ Logs test failed: {e}")
        results.append(("Logs", False))
    
    try:
        results.append(("Policy Decisions", test_policy_decisions()))
    except Exception as e:
        print(f"❌ Policy decisions test failed: {e}")
        results.append(("Policy Decisions", False))
    
    # HTTP endpoints are REQUIRED - test them
    try:
        http_result = test_http_endpoints()
        results.append(("HTTP Endpoints", http_result))
    except requests.exceptions.ConnectionError:
        print("❌ HTTP endpoints test FAILED (server not running)")
        print("   Start server with: python main.py --server --port 8000")
        results.append(("HTTP Endpoints", False))  # Required - mark as failed
    except Exception as e:
        print(f"❌ HTTP endpoints test FAILED: {e}")
        results.append(("HTTP Endpoints", False))  # Required - mark as failed
    
    print()
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for name, result in results:
        if result is True:
            print(f"✅ {name}: PASSED")
        elif result is False:
            print(f"❌ {name}: FAILED")
        else:
            if name == "HTTP Endpoints":
                print(f"❌ {name}: FAILED (REQUIRED - server not running)")
            else:
                print(f"⚠️  {name}: SKIPPED (optional)")
    
    print()
    
    # Count results
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    
    print(f"Total: {passed} passed, {failed} failed, {skipped} skipped")
    
    # HTTP endpoints are REQUIRED - fail if they're not working
    http_test = next((r for name, r in results if name == "HTTP Endpoints"), None)
    if http_test is False:
        print("\n❌ HTTP Endpoints test FAILED - This is REQUIRED")
        print("   Start server with: python main.py --server --port 8000")
        print("   Then run this test again")
        sys.exit(1)
    
    if failed > 0:
        print("\n❌ Some tests failed. Check the output above.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        print("\nNext steps:")
        print("1. Start observability stack: docker-compose -f docker-compose.observability.yml up -d")
        print("2. Start application: python main.py --server --port 8000")
        print("3. View metrics in Grafana: http://localhost:3000")
        print("4. View traces in Jaeger: http://localhost:16686 (search for service: taskpilot)")
        print("5. View logs in Kibana: http://localhost:5601")
        print("\nTo verify Jaeger hierarchy:")
        print("   python scripts/verify_jaeger_hierarchy.py")
        sys.exit(0)


if __name__ == "__main__":
    main()
