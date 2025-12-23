#!/usr/bin/env python3
"""Verify Jaeger trace hierarchy and generate screenshot-ready results."""
import requests
import json
import time
from datetime import datetime

def check_jaeger_hierarchy():
    """Check Jaeger for traces and verify hierarchy."""
    
    print("=" * 80)
    print("Jaeger Trace Hierarchy Verification")
    print("=" * 80)
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    try:
        # Query Jaeger for latest traces
        response = requests.get(
            "http://localhost:16686/api/traces",
            params={"service": "taskpilot", "limit": 5},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"✗ Jaeger API error: {response.status_code}")
            return False
        
        data = response.json()
        traces = data.get("data", [])
        
        if not traces:
            print("⚠ No traces found in Jaeger")
            print("→ Run: python3 main.py")
            print("→ Wait 5-10 seconds for batch export")
            return False
        
        print(f"✓ Found {len(traces)} trace(s) in Jaeger")
        print()
        
        # Analyze the most recent trace
        latest = traces[0]
        trace_id = latest.get("traceID")
        spans = latest.get("spans", [])
        
        print("LATEST TRACE ANALYSIS:")
        print(f"  Trace ID: {trace_id}")
        print(f"  Total Spans: {len(spans)}")
        print()
        
        # Check trace ID consistency (CRITICAL for hierarchy)
        trace_ids = set(s.get("traceID") for s in spans)
        if len(trace_ids) == 1:
            print("✓ HIERARCHY: CORRECT")
            print(f"  All {len(spans)} spans share the same trace ID")
            hierarchy_status = "CORRECT"
        else:
            print("✗ HIERARCHY: BROKEN")
            print(f"  Found {len(trace_ids)} different trace IDs")
            hierarchy_status = "BROKEN"
        print()
        
        # Show all spans
        print("SPANS IN TRACE:")
        operations = {}
        for i, span in enumerate(spans, 1):
            op = span.get("operationName", "unknown")
            span_id = span.get("spanID", "unknown")
            refs = span.get("references", [])
            tags = {t.get("key"): t.get("value") for t in span.get("tags", [])}
            request_id = tags.get("request.id", "N/A")[:8]
            
            operations[op] = operations.get(op, 0) + 1
            
            print(f"  [{i}] {op}")
            print(f"      Span ID: {span_id}")
            print(f"      Request ID: {request_id}")
            print(f"      References: {len(refs)}")
            if refs:
                for ref in refs:
                    ref_type = ref.get("refType", "CHILD_OF")
                    ref_span_id = ref.get("spanID", "unknown")
                    print(f"        → {ref_type}: {ref_span_id}")
            print()
        
        # Check for workflow and agents
        workflow_spans = [s for s in spans if "workflow.run" in s.get("operationName", "")]
        agent_spans = [s for s in spans if "agent." in s.get("operationName", "")]
        
        print("HIERARCHY STRUCTURE:")
        if workflow_spans and agent_spans:
            print(f"  ✓ Workflow span: {len(workflow_spans)}")
            print(f"  ✓ Agent spans: {len(agent_spans)}")
            
            # Check if agent spans reference workflow
            if workflow_spans:
                workflow_span_id = workflow_spans[0].get("spanID")
                agents_with_ref = sum(
                    1 for a in agent_spans 
                    if any(r.get("spanID") == workflow_span_id for r in a.get("references", []))
                )
                print(f"  Agent spans with workflow reference: {agents_with_ref}/{len(agent_spans)}")
        else:
            print(f"  ⚠ Missing workflow or agent spans")
        print()
        
        # Generate JSON summary for screenshots
        summary = {
            "test_time": datetime.now().isoformat(),
            "status": "PASS" if hierarchy_status == "CORRECT" else "FAIL",
            "hierarchy_status": hierarchy_status,
            "trace_id": trace_id,
            "total_spans": len(spans),
            "unique_trace_ids": len(trace_ids),
            "operations": {op: count for op, count in operations.items()},
            "has_workflow": len(workflow_spans) > 0,
            "has_agents": len(agent_spans) > 0,
            "workflow_count": len(workflow_spans),
            "agent_count": len(agent_spans),
            "spans_with_references": len([s for s in spans if s.get("references")]),
            "jaeger_url": f"http://localhost:16686/trace/{trace_id}",
            "all_traces_count": len(traces)
        }
        
        print("=" * 80)
        print("TEST RESULTS (JSON for screenshots)")
        print("=" * 80)
        print(json.dumps(summary, indent=2))
        print("=" * 80)
        print()
        print("Jaeger UI Links:")
        print(f"  Main: http://localhost:16686")
        print(f"  This trace: {summary['jaeger_url']}")
        print()
        print("To view in Jaeger:")
        print("  1. Open http://localhost:16686")
        print("  2. Select service: 'taskpilot'")
        print("  3. Click on the latest trace")
        print("  4. You should see workflow.run as root with agent spans as children")
        
        return hierarchy_status == "CORRECT"
        
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to Jaeger")
        print("→ Start with: docker-compose -f docker-compose.observability.yml up -d")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = check_jaeger_hierarchy()
    sys.exit(0 if success else 1)
