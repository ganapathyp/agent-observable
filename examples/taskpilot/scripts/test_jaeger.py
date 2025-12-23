#!/usr/bin/env python3
"""Test Jaeger trace hierarchy and generate screenshot-ready results."""
import requests
import json
from datetime import datetime

def test_jaeger():
    """Test Jaeger traces and show hierarchy results."""
    
    print("=" * 80)
    print("JAEGER TRACE HIERARCHY TEST")
    print("=" * 80)
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    try:
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
        
        # Analyze latest trace
        latest = traces[0]
        trace_id = latest.get("traceID")
        spans = latest.get("spans", [])
        
        print("LATEST TRACE ANALYSIS:")
        print(f"  Trace ID: {trace_id}")
        print(f"  Total Spans: {len(spans)}")
        
        # Check hierarchy
        trace_ids = set(s.get("traceID") for s in spans)
        if len(trace_ids) == 1:
            print(f"  ✓ HIERARCHY: CORRECT")
            print(f"    All {len(spans)} spans share the same trace ID")
            hierarchy_ok = True
        else:
            print(f"  ✗ HIERARCHY: BROKEN")
            print(f"    Found {len(trace_ids)} different trace IDs")
            hierarchy_ok = False
        
        print()
        print("SPANS:")
        operations = {}
        for span in spans:
            op = span.get("operationName", "unknown")
            operations[op] = operations.get(op, 0) + 1
            refs = span.get("references", [])
            print(f"  - {op} (references: {len(refs)})")
        
        print()
        
        # Check for workflow and agents
        workflow = [s for s in spans if "workflow.run" in s.get("operationName", "")]
        agents = [s for s in spans if "agent." in s.get("operationName", "")]
        
        if workflow and agents:
            print(f"✓ Structure: {len(workflow)} workflow + {len(agents)} agent spans")
        print()
        
        # Generate JSON for screenshots
        summary = {
            "test_time": datetime.now().isoformat(),
            "status": "PASS" if hierarchy_ok else "FAIL",
            "hierarchy_status": "CORRECT" if hierarchy_ok else "BROKEN",
            "trace_id": trace_id,
            "total_spans": len(spans),
            "unique_trace_ids": len(trace_ids),
            "operations": list(operations.keys()),
            "has_workflow": len(workflow) > 0,
            "has_agents": len(agents) > 0,
            "workflow_count": len(workflow),
            "agent_count": len(agents),
            "jaeger_url": f"http://localhost:16686/trace/{trace_id}"
        }
        
        print("=" * 80)
        print("TEST RESULTS (JSON for screenshots)")
        print("=" * 80)
        print(json.dumps(summary, indent=2))
        print("=" * 80)
        print()
        print(f"Jaeger UI: http://localhost:16686")
        print(f"Direct link: {summary['jaeger_url']}")
        
        return hierarchy_ok
        
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
    success = test_jaeger()
    sys.exit(0 if success else 1)
