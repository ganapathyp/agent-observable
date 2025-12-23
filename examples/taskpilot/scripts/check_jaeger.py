#!/usr/bin/env python3
"""Quick check of Jaeger traces with hierarchy verification."""
import requests
import json
from datetime import datetime

print("=" * 80)
print("Jaeger Trace Hierarchy Check")
print("=" * 80)
print(f"Time: {datetime.now().isoformat()}")
print()

try:
    # Query Jaeger
    response = requests.get(
        "http://localhost:16686/api/traces",
        params={"service": "taskpilot", "limit": 5},
        timeout=5
    )
    
    if response.status_code != 200:
        print(f"✗ Jaeger API error: {response.status_code}")
        exit(1)
    
    data = response.json()
    traces = data.get("data", [])
    
    if not traces:
        print("⚠ No traces found in Jaeger")
        print("→ Run: python3 main.py")
        print("→ Wait 5-10 seconds for batch export")
        exit(0)
    
    print(f"✓ Found {len(traces)} trace(s) in Jaeger")
    print()
    
    # Analyze each trace
    for i, trace in enumerate(traces[:3], 1):
        trace_id = trace.get("traceID")
        spans = trace.get("spans", [])
        
        print(f"[Trace {i}]")
        print(f"  Trace ID: {trace_id}")
        print(f"  Spans: {len(spans)}")
        
        # Check trace ID consistency
        trace_ids = set(s.get("traceID") for s in spans)
        if len(trace_ids) == 1:
            print(f"  ✓ Hierarchy: CORRECT (all spans share same trace ID)")
        else:
            print(f"  ✗ Hierarchy: BROKEN ({len(trace_ids)} different trace IDs)")
        
        # Show operations
        ops = {}
        for s in spans:
            op = s.get("operationName", "unknown")
            ops[op] = ops.get(op, 0) + 1
        
        print(f"  Operations: {', '.join(sorted(ops.keys()))}")
        
        # Check for workflow and agents
        workflow = [s for s in spans if "workflow.run" in s.get("operationName", "")]
        agents = [s for s in spans if "agent." in s.get("operationName", "")]
        
        if workflow and agents:
            print(f"  ✓ Has workflow ({len(workflow)}) and agents ({len(agents)})")
        elif workflow:
            print(f"  ⚠ Has workflow but no agents")
        elif agents:
            print(f"  ⚠ Has agents but no workflow")
        
        print()
    
    # Get most recent trace for detailed analysis
    latest = traces[0]
    trace_id = latest.get("traceID")
    spans = latest.get("spans", [])
    
    print("=" * 80)
    print("DETAILED ANALYSIS (Latest Trace)")
    print("=" * 80)
    print(f"Trace ID: {trace_id}")
    print(f"Total Spans: {len(spans)}")
    print()
    
    # Check trace ID consistency
    trace_ids = set(s.get("traceID") for s in spans)
    if len(trace_ids) == 1:
        print("✓ HIERARCHY STATUS: CORRECT")
        print(f"  All {len(spans)} spans share the same trace ID")
    else:
        print("✗ HIERARCHY STATUS: BROKEN")
        print(f"  Found {len(trace_ids)} different trace IDs")
    
    print()
    
    # Show all spans with details
    print("Spans in trace:")
    for i, span in enumerate(spans, 1):
        op = span.get("operationName", "unknown")
        span_id = span.get("spanID", "unknown")
        refs = span.get("references", [])
        tags = {t.get("key"): t.get("value") for t in span.get("tags", [])}
        request_id_tag = tags.get("request.id", "N/A")[:8]
        
        print(f"  [{i}] {op}")
        print(f"      Span ID: {span_id}")
        print(f"      Request ID: {request_id_tag}")
        print(f"      References: {len(refs)}")
        if refs:
            for ref in refs:
                ref_type = ref.get("refType", "unknown")
                ref_span_id = ref.get("spanID", "unknown")
                print(f"        - {ref_type}: {ref_span_id}")
        print()
    
    # Summary JSON for screenshots
    summary = {
        "test_time": datetime.now().isoformat(),
        "total_traces": len(traces),
        "latest_trace": {
            "trace_id": trace_id,
            "total_spans": len(spans),
            "hierarchy_status": "CORRECT" if len(trace_ids) == 1 else "BROKEN",
            "unique_trace_ids": len(trace_ids),
            "operations": [s.get("operationName") for s in spans],
            "has_workflow": len([s for s in spans if "workflow.run" in s.get("operationName", "")]) > 0,
            "has_agents": len([s for s in spans if "agent." in s.get("operationName", "")]) > 0,
            "spans_with_references": len([s for s in spans if s.get("references")]),
        },
        "jaeger_url": f"http://localhost:16686/trace/{trace_id}"
    }
    
    print("=" * 80)
    print("SUMMARY (JSON for screenshots)")
    print("=" * 80)
    print(json.dumps(summary, indent=2))
    print("=" * 80)
    print()
    print(f"Jaeger UI: http://localhost:16686")
    print(f"Direct link: {summary['jaeger_url']}")
    
except requests.exceptions.ConnectionError:
    print("✗ Cannot connect to Jaeger")
    print("→ Start with: docker-compose -f docker-compose.observability.yml up -d")
    exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
