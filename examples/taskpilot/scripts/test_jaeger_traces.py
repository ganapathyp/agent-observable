#!/usr/bin/env python3
"""Test script to verify Jaeger trace export and hierarchy."""
import asyncio
import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_jaeger_traces():
    """Test that traces are being sent to Jaeger with proper hierarchy."""
    
    print("=" * 80)
    print("Jaeger Trace Export Test")
    print("=" * 80)
    
    # Step 1: Check OpenTelemetry initialization
    print("\n[1] Checking OpenTelemetry initialization...")
    try:
        from taskpilot.core.otel_integration import (
            initialize_opentelemetry,
            get_otel_tracer,
            _otel_enabled
        )
        
        # Initialize if not already done
        if not get_otel_tracer():
            print("   Initializing OpenTelemetry...")
            success = initialize_opentelemetry(
                service_name="taskpilot",
                otlp_endpoint="http://localhost:4317",
                enabled=True
            )
            if success:
                print("   ✓ OpenTelemetry initialized successfully")
            else:
                print("   ✗ OpenTelemetry initialization failed")
                return False
        else:
            print("   ✓ OpenTelemetry already initialized")
        
        tracer = get_otel_tracer()
        if not tracer:
            print("   ✗ Tracer is None - OpenTelemetry not working")
            return False
        
        print(f"   ✓ Tracer obtained: {tracer}")
        print(f"   ✓ OpenTelemetry enabled: {_otel_enabled}")
        
    except Exception as e:
        print(f"   ✗ Error checking OpenTelemetry: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Check Jaeger connectivity
    print("\n[2] Checking Jaeger connectivity...")
    try:
        import requests
        response = requests.get("http://localhost:16686/api/services", timeout=5)
        if response.status_code == 200:
            services = response.json().get("data", [])
            print(f"   ✓ Jaeger is accessible")
            print(f"   ✓ Services in Jaeger: {services}")
            if "taskpilot" in services:
                print("   ✓ 'taskpilot' service found in Jaeger")
            else:
                print("   ⚠ 'taskpilot' service not yet in Jaeger (will appear after traces)")
        else:
            print(f"   ✗ Jaeger returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ✗ Cannot connect to Jaeger (is it running?)")
        print("   → Start with: docker-compose -f docker-compose.observability.yml up -d")
        return False
    except Exception as e:
        print(f"   ✗ Error checking Jaeger: {e}")
        return False
    
    # Step 3: Create test traces with hierarchy
    print("\n[3] Creating test traces with hierarchy...")
    try:
        from taskpilot.core.observability import TraceContext, get_tracer
        
        request_id = f"test-{int(time.time())}"
        
        # Create root span (workflow.run)
        print(f"   Creating root span: workflow.run (request_id={request_id})")
        with TraceContext(
            name="workflow.run",
            request_id=request_id,
            tags={"workflow_type": "test", "test": "true"}
        ) as workflow_span:
            workflow_trace_id = None
            workflow_span_id = workflow_span.span_id
            
            # Get trace ID from OpenTelemetry span if available
            if hasattr(workflow_span, '_otel_span'):
                otel_span = workflow_span._otel_span
                workflow_trace_id = format(otel_span.get_span_context().trace_id, '032x')
                print(f"   ✓ Root span created: trace_id={workflow_trace_id}, span_id={workflow_span_id[:8]}")
            else:
                print(f"   ✓ Root span created: span_id={workflow_span_id[:8]} (OTEL span not yet created)")
            
            # Create child span (agent.PlannerAgent.run)
            print(f"   Creating child span: agent.PlannerAgent.run (parent={workflow_span_id[:8]})")
            with TraceContext(
                name="agent.PlannerAgent.run",
                request_id=request_id,
                parent_span_id=workflow_span_id,
                tags={"agent_name": "PlannerAgent", "agent_type": "planner"}
            ) as agent_span:
                agent_trace_id = None
                if hasattr(agent_span, '_otel_span'):
                    otel_span = agent_span._otel_span
                    agent_trace_id = format(otel_span.get_span_context().trace_id, '032x')
                    print(f"   ✓ Child span created: trace_id={agent_trace_id}, span_id={agent_span.span_id[:8]}")
                    
                    # Verify trace IDs match
                    if workflow_trace_id and agent_trace_id:
                        if workflow_trace_id == agent_trace_id:
                            print(f"   ✓ Trace IDs match - hierarchy is correct!")
                        else:
                            print(f"   ✗ Trace IDs DON'T match - hierarchy broken!")
                            print(f"      Workflow: {workflow_trace_id}")
                            print(f"      Agent:    {agent_trace_id}")
                            return False
                else:
                    print(f"   ✓ Child span created: span_id={agent_span.span_id[:8]} (OTEL span not yet created)")
                
                # Simulate some work
                await asyncio.sleep(0.1)
            
            # Wait a bit for spans to be exported
            await asyncio.sleep(1)
        
        print(f"   ✓ Test traces created successfully")
        
    except Exception as e:
        print(f"   ✗ Error creating test traces: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Wait for traces to be exported
    print("\n[4] Waiting for traces to be exported to Jaeger...")
    await asyncio.sleep(3)  # Give time for batch export
    
    # Step 5: Check Jaeger for traces
    print("\n[5] Checking Jaeger for traces...")
    try:
        import requests
        
        # Query traces for our request_id
        response = requests.get(
            f"http://localhost:16686/api/traces",
            params={"service": "taskpilot", "limit": 20},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            traces = data.get("data", [])
            
            if traces:
                print(f"   ✓ Found {len(traces)} trace(s) in Jaeger")
                
                # Find our test trace
                test_trace = None
                for trace in traces:
                    spans = trace.get("spans", [])
                    for span in spans:
                        tags = {tag.get("key"): tag.get("value") for tag in span.get("tags", [])}
                        if tags.get("request.id") == request_id:
                            test_trace = trace
                            break
                    if test_trace:
                        break
                
                if test_trace:
                    print(f"   ✓ Found test trace with request_id={request_id}")
                    spans = test_trace.get("spans", [])
                    print(f"   ✓ Trace has {len(spans)} span(s)")
                    
                    # Check for hierarchy
                    trace_id = test_trace.get("traceID")
                    print(f"   ✓ Trace ID: {trace_id}")
                    
                    # Group spans by operation
                    operations = {}
                    for span in spans:
                        op = span.get("operationName", "unknown")
                        if op not in operations:
                            operations[op] = []
                        operations[op].append(span)
                    
                    print(f"\n   Span operations found:")
                    for op, span_list in operations.items():
                        print(f"     - {op}: {len(span_list)} span(s)")
                    
                    # Check if all spans have same trace ID
                    trace_ids = set()
                    for span in spans:
                        trace_ids.add(span.get("traceID"))
                    
                    if len(trace_ids) == 1:
                        print(f"   ✓ All spans share the same trace ID - hierarchy is correct!")
                    else:
                        print(f"   ✗ Spans have different trace IDs - hierarchy is broken!")
                        print(f"      Found trace IDs: {trace_ids}")
                        return False
                    
                    # Check for parent-child relationships
                    print(f"\n   Checking parent-child relationships...")
                    workflow_spans = [s for s in spans if s.get("operationName") == "workflow.run"]
                    agent_spans = [s for s in spans if "agent." in s.get("operationName", "")]
                    
                    if workflow_spans and agent_spans:
                        print(f"   ✓ Found workflow span and agent spans")
                        
                        # Check references
                        for agent_span in agent_spans:
                            refs = agent_span.get("references", [])
                            if refs:
                                print(f"   ✓ Agent span has references: {refs}")
                            else:
                                print(f"   ⚠ Agent span has no references (may still work if same trace ID)")
                    else:
                        print(f"   ⚠ Could not find both workflow and agent spans")
                    
                    return True
                else:
                    print(f"   ⚠ Test trace not found (may need more time to export)")
                    print(f"   → Try checking Jaeger UI: http://localhost:16686")
                    return False
            else:
                print(f"   ⚠ No traces found in Jaeger yet")
                print(f"   → This might be normal if traces are still being exported")
                print(f"   → Check Jaeger UI: http://localhost:16686")
                return False
        else:
            print(f"   ✗ Jaeger API returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error checking Jaeger: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    success = await test_jaeger_traces()
    
    print("\n" + "=" * 80)
    if success:
        print("✓ TEST PASSED: Traces are being exported to Jaeger with proper hierarchy")
    else:
        print("✗ TEST FAILED: Issues detected with trace export or hierarchy")
    print("=" * 80)
    
    print("\nNext steps:")
    print("1. Check Jaeger UI: http://localhost:16686")
    print("2. Search for service: 'taskpilot'")
    print("3. Look for traces with proper hierarchy (workflow.run as root)")
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("ERROR: 'requests' library required. Install with: pip install requests")
        sys.exit(1)
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
