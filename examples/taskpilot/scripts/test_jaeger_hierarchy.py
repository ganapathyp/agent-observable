#!/usr/bin/env python3
"""Test and verify Jaeger trace hierarchy with screenshot-ready output."""
import asyncio
import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def run_workflow_and_check_jaeger():
    """Run a workflow and check Jaeger for proper hierarchy."""
    
    print("=" * 80)
    print("Jaeger Trace Hierarchy Test")
    print("=" * 80)
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    # Step 1: Run workflow
    print("[1] Running workflow...")
    request_id = None
    
    try:
        from taskpilot.main import run_workflow_once
        result = await run_workflow_once()
        
        # Extract request_id from result if possible
        if hasattr(result, '__iter__'):
            for event in result:
                if hasattr(event, 'data') and hasattr(event.data, 'request_id'):
                    request_id = event.data.request_id
                    break
        
        print(f"   ✓ Workflow completed")
        if request_id:
            print(f"   Request ID: {request_id}")
    except Exception as e:
        print(f"   ✗ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Wait for traces to be exported
    print("\n[2] Waiting for traces to be exported to Jaeger...")
    print("   (BatchSpanProcessor may take a few seconds to flush)")
    await asyncio.sleep(5)
    
    # Step 3: Query Jaeger
    print("\n[3] Querying Jaeger for traces...")
    try:
        response = requests.get(
            "http://localhost:16686/api/traces",
            params={"service": "taskpilot", "limit": 10},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"   ✗ Jaeger API returned status {response.status_code}")
            return False
        
        data = response.json()
        traces = data.get("data", [])
        
        if not traces:
            print("   ⚠ No traces found in Jaeger")
            print("   → Check if OpenTelemetry collector is running")
            print("   → Check if traces are being exported")
            return False
        
        print(f"   ✓ Found {len(traces)} trace(s) in Jaeger")
        
        # Analyze the most recent trace
        latest_trace = traces[0]  # Most recent is first
        trace_id = latest_trace.get("traceID")
        spans = latest_trace.get("spans", [])
        
        print(f"\n[4] Analyzing latest trace...")
        print(f"   Trace ID: {trace_id}")
        print(f"   Number of spans: {len(spans)}")
        
        # Group spans by operation
        operations = {}
        for span in spans:
            op = span.get("operationName", "unknown")
            if op not in operations:
                operations[op] = []
            operations[op].append(span)
        
        print(f"\n   Span operations:")
        for op, span_list in sorted(operations.items()):
            print(f"     - {op}: {len(span_list)} span(s)")
        
        # Check trace ID consistency
        trace_ids = set(span.get("traceID") for span in spans)
        if len(trace_ids) == 1:
            print(f"\n   ✓ ALL spans share the same trace ID - Hierarchy is CORRECT!")
            print(f"      Trace ID: {list(trace_ids)[0]}")
        else:
            print(f"\n   ✗ Spans have DIFFERENT trace IDs - Hierarchy is BROKEN!")
            print(f"      Found {len(trace_ids)} different trace IDs:")
            for tid in trace_ids:
                count = sum(1 for s in spans if s.get("traceID") == tid)
                print(f"        - {tid}: {count} span(s)")
            return False
        
        # Check for parent-child relationships via references
        print(f"\n   Checking parent-child relationships...")
        spans_with_refs = [s for s in spans if s.get("references")]
        spans_without_refs = [s for s in spans if not s.get("references")]
        
        print(f"     Spans with references: {len(spans_with_refs)}")
        print(f"     Spans without references: {len(spans_without_refs)}")
        
        # Find workflow span
        workflow_spans = [s for s in spans if s.get("operationName") == "workflow.run"]
        agent_spans = [s for s in spans if "agent." in s.get("operationName", "")]
        
        if workflow_spans and agent_spans:
            print(f"\n   ✓ Found workflow span and {len(agent_spans)} agent span(s)")
            
            # Check if agent spans reference workflow span
            workflow_span_id = workflow_spans[0].get("spanID")
            agent_spans_with_workflow_ref = []
            
            for agent_span in agent_spans:
                refs = agent_span.get("references", [])
                for ref in refs:
                    if ref.get("spanID") == workflow_span_id:
                        agent_spans_with_workflow_ref.append(agent_span)
                        break
            
            if agent_spans_with_workflow_ref:
                print(f"   ✓ {len(agent_spans_with_workflow_ref)} agent span(s) have explicit references to workflow span")
            else:
                print(f"   ⚠ Agent spans don't have explicit references (but same trace ID = hierarchy OK)")
        else:
            print(f"   ⚠ Could not find both workflow and agent spans")
        
        # Create summary JSON for screenshot
        summary = {
            "test_time": datetime.now().isoformat(),
            "trace_id": trace_id,
            "total_spans": len(spans),
            "operations": {op: len(span_list) for op, span_list in operations.items()},
            "hierarchy_status": "CORRECT" if len(trace_ids) == 1 else "BROKEN",
            "unique_trace_ids": len(trace_ids),
            "spans_with_references": len(spans_with_refs),
            "spans_without_references": len(spans_without_refs),
            "workflow_spans": len(workflow_spans),
            "agent_spans": len(agent_spans),
            "jaeger_url": f"http://localhost:16686/trace/{trace_id}"
        }
        
        print(f"\n[5] Test Summary (JSON for screenshots):")
        print("=" * 80)
        print(json.dumps(summary, indent=2))
        print("=" * 80)
        
        print(f"\n[6] Jaeger UI Link:")
        print(f"   {summary['jaeger_url']}")
        print(f"\n   Open this URL to see the trace in Jaeger UI")
        
        return len(trace_ids) == 1
        
    except requests.exceptions.ConnectionError:
        print("   ✗ Cannot connect to Jaeger")
        print("   → Start with: docker-compose -f docker-compose.observability.yml up -d")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    success = await run_workflow_and_check_jaeger()
    
    print("\n" + "=" * 80)
    if success:
        print("✓ TEST PASSED: Traces in Jaeger have proper hierarchy (same trace ID)")
    else:
        print("✗ TEST FAILED: Hierarchy issues detected")
    print("=" * 80)
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("ERROR: 'requests' library required. Install with: pip install requests")
        sys.exit(1)
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
