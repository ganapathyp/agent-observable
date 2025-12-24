#!/usr/bin/env python3
"""Verify that traces show proper hierarchy in Jaeger.

This script creates a test trace with proper hierarchy:
- taskpilot.workflow.run (root)
  - taskpilot.agent.PlannerAgent.run (child)
    - taskpilot.tool.create_task.call (grandchild)

Run this and then check Jaeger UI to verify the hierarchy.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from taskpilot.core.observable import TraceContext, get_tracer
from taskpilot.core.trace_names import WORKFLOW_RUN, agent_run, tool_call


def test_trace_hierarchy():
    """Create a test trace with proper hierarchy."""
    print("=" * 60)
    print("Creating Test Trace with Hierarchy")
    print("=" * 60)
    print()
    
    request_id = "test-hierarchy-123"
    tracer = get_tracer()
    
    # Root span: workflow.run
    print(f"1. Creating root span: {WORKFLOW_RUN}")
    with TraceContext(
        name=WORKFLOW_RUN,
        request_id=request_id,
        tags={"workflow_type": "test"}
    ) as workflow_span:
        print(f"   ✅ Root span created: {workflow_span.span_id}")
        
        # Child span: agent.run
        agent_name = "PlannerAgent"
        agent_span_name = agent_run(agent_name)
        print(f"2. Creating child span: {agent_span_name}")
        with TraceContext(
            name=agent_span_name,
            request_id=request_id,
            parent_span_id=workflow_span.span_id,
            tags={"agent_name": agent_name}
        ) as agent_span:
            print(f"   ✅ Child span created: {agent_span.span_id}")
            print(f"   ✅ Parent span ID: {agent_span.parent_span_id}")
            
            # Grandchild span: tool.call
            tool_name = "create_task"
            tool_span_name = tool_call(tool_name)
            print(f"3. Creating grandchild span: {tool_span_name}")
            with TraceContext(
                name=tool_span_name,
                request_id=request_id,
                parent_span_id=agent_span.span_id,
                tags={"tool_name": tool_name}
            ) as tool_span:
                print(f"   ✅ Grandchild span created: {tool_span.span_id}")
                print(f"   ✅ Parent span ID: {tool_span.parent_span_id}")
                
                # Simulate work
                time.sleep(0.1)
                print(f"   ✅ Tool execution completed")
        
        print(f"   ✅ Agent execution completed")
    
    print(f"✅ Workflow execution completed")
    print()
    
    # Verify trace structure
    print("=" * 60)
    print("Verifying Trace Structure")
    print("=" * 60)
    
    trace = tracer.get_trace(request_id)
    print(f"Total spans: {len(trace)}")
    print()
    
    for span in trace:
        indent = "  " * (2 if span.parent_span_id else 0)
        print(f"{indent}- {span.name}")
        print(f"{indent}  Span ID: {span.span_id}")
        if span.parent_span_id:
            print(f"{indent}  Parent: {span.parent_span_id}")
        print()
    
    print("=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Check Jaeger UI: http://localhost:16686")
    print("2. Search for service: taskpilot")
    print("3. Search for request_id: test-hierarchy-123")
    print("4. Verify hierarchy shows:")
    print("   - taskpilot.workflow.run (root)")
    print("     - taskpilot.agent.PlannerAgent.run (child)")
    print("       - taskpilot.tool.create_task.call (grandchild)")
    print()


if __name__ == "__main__":
    test_trace_hierarchy()
