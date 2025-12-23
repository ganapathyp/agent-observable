"""View agent calls and traces in a readable format."""
import json
import sys
import logging
from datetime import datetime
from typing import List, Dict, Optional
from taskpilot.core.observability import get_tracer, get_request_id  # type: ignore

logging.basicConfig(level=logging.WARNING)  # Only show warnings/errors
logger = logging.getLogger(__name__)

def format_trace_tree(spans: List, request_id: Optional[str] = None):
    """Format spans as a tree structure."""
    if not spans:
        return "No spans found"
    
    # Build parent-child relationships
    span_map = {span.span_id: span for span in spans}
    root_spans = [s for s in spans if s.parent_span_id is None]
    
    def format_span(span, indent=0, prefix=""):
        """Format a single span with indentation."""
        indent_str = "  " * indent
        duration = f"{span.duration_ms:.2f}ms" if span.duration_ms else "ongoing"
        
        # Format tags
        tags_str = ""
        if span.tags:
            tags_str = " " + ", ".join([f"{k}={v}" for k, v in span.tags.items()])
        
        # Format logs
        logs_str = ""
        if span.logs:
            log_count = len(span.logs)
            logs_str = f" ({log_count} log{'s' if log_count > 1 else ''})"
        
        result = f"{indent_str}{prefix}{span.name} [{duration}]{tags_str}{logs_str}\n"
        
        # Add children
        children = [s for s in spans if s.parent_span_id == span.span_id]
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            child_prefix = "└─ " if is_last else "├─ "
            result += format_span(child, indent + 1, child_prefix)
        
        return result
    
    output = []
    if request_id:
        output.append(f"Request ID: {request_id}\n")
    
    output.append(f"Total spans: {len(spans)}\n")
    output.append("=" * 60 + "\n")
    
    for root in root_spans:
        output.append(format_span(root))
    
    return "".join(output)


def view_trace_by_request_id(request_id: str):
    """View trace for a specific request ID."""
    tracer = get_tracer()
    spans = tracer.get_trace(request_id)
    
    if not spans:
        print(f"No spans found for request ID: {request_id}")
        return
    
    print(format_trace_tree(spans, request_id))


def view_recent_traces(limit: int = 10):
    """View recent traces grouped by request ID."""
    tracer = get_tracer()
    recent_spans = tracer.get_recent_spans(limit=limit * 10)  # Get more spans to group
    
    if not recent_spans:
        print("No traces found")
        return
    
    # Group spans by request_id
    traces: Dict[str, List] = {}
    for span in recent_spans:
        if span.request_id:
            if span.request_id not in traces:
                traces[span.request_id] = []
            traces[span.request_id].append(span)
    
    if not traces:
        print("No traces with request IDs found")
        return
    
    # Sort by most recent (by span start_time)
    sorted_traces = sorted(
        traces.items(),
        key=lambda x: max(s.start_time for s in x[1]),
        reverse=True
    )[:limit]
    
    print(f"Recent Traces (showing {len(sorted_traces)} of {len(traces)})\n")
    print("=" * 60)
    
    for i, (request_id, spans) in enumerate(sorted_traces, 1):
        # Sort spans by start_time
        spans.sort(key=lambda s: s.start_time)
        
        # Calculate total duration
        if spans:
            start = min(s.start_time for s in spans)
            end = max(s.end_time for s in spans if s.end_time)
            total_duration = (end - start) * 1000 if end else None
        else:
            total_duration = None
        
        print(f"\n[{i}] Request: {request_id}")
        if total_duration:
            print(f"    Total Duration: {total_duration:.2f}ms")
        print(f"    Spans: {len(spans)}")
        print("-" * 60)
        print(format_trace_tree(spans, request_id=None))


def view_agent_calls(limit: int = 20):
    """View agent calls in chronological order."""
    tracer = get_tracer()
    recent_spans = tracer.get_recent_spans(limit=limit)
    
    if not recent_spans:
        print("No agent calls found")
        return
    
    # Filter for agent spans (those with agent_name tag or matching pattern)
    agent_spans = [
        s for s in recent_spans
        if "agent" in s.name.lower() or s.tags.get("agent_name")
    ]
    
    if not agent_spans:
        print("No agent calls found")
        return
    
    # Sort by start_time
    agent_spans.sort(key=lambda s: s.start_time, reverse=True)
    
    print(f"Agent Calls (showing {len(agent_spans)} recent calls)\n")
    print("=" * 60)
    
    for i, span in enumerate(agent_spans[:limit], 1):
        agent_name = span.tags.get("agent_name", span.name)
        duration = f"{span.duration_ms:.2f}ms" if span.duration_ms else "ongoing"
        timestamp = datetime.fromtimestamp(span.start_time).strftime("%H:%M:%S.%f")[:-3]
        
        # Get latency from logs if available
        latency_info = ""
        for log in span.logs:
            if "latency_ms" in log.get("fields", {}):
                latency_info = f" (latency: {log['fields']['latency_ms']:.2f}ms)"
        
        print(f"\n[{i}] {agent_name}")
        print(f"    Time: {timestamp}")
        print(f"    Duration: {duration}{latency_info}")
        print(f"    Request ID: {span.request_id}")
        
        if span.tags:
            print(f"    Tags: {', '.join([f'{k}={v}' for k, v in span.tags.items()])}")
        
        if span.logs:
            print(f"    Logs: {len(span.logs)} entries")
            for log in span.logs[:2]:  # Show first 2 logs
                fields = log.get("fields", {})
                if fields:
                    print(f"      - {fields}")


def view_trace_summary():
    """View summary of all traces."""
    tracer = get_tracer()
    recent_spans = tracer.get_recent_spans(limit=1000)
    
    if not recent_spans:
        print("No traces found")
        return
    
    # Group by request_id
    traces: Dict[str, List] = {}
    for span in recent_spans:
        if span.request_id:
            if span.request_id not in traces:
                traces[span.request_id] = []
            traces[span.request_id].append(span)
    
    print(f"Trace Summary\n")
    print("=" * 60)
    print(f"Total requests: {len(traces)}")
    print(f"Total spans: {len(recent_spans)}")
    
    if traces:
        # Calculate statistics
        durations = []
        span_counts = []
        
        for request_id, spans in traces.items():
            if spans:
                start = min(s.start_time for s in spans)
                end = max(s.end_time for s in spans if s.end_time)
                if end:
                    durations.append((end - start) * 1000)
                span_counts.append(len(spans))
        
        if durations:
            print(f"\nDuration Statistics:")
            print(f"  Average: {sum(durations) / len(durations):.2f}ms")
            print(f"  Min: {min(durations):.2f}ms")
            print(f"  Max: {max(durations):.2f}ms")
        
        if span_counts:
            print(f"\nSpan Statistics:")
            print(f"  Average per request: {sum(span_counts) / len(span_counts):.2f}")
            print(f"  Min: {min(span_counts)}")
            print(f"  Max: {max(span_counts)}")
        
        # Group by agent name
        agent_counts: Dict[str, int] = {}
        for span in recent_spans:
            agent_name = span.tags.get("agent_name", span.name)
            agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1
        
        if agent_counts:
            print(f"\nAgent Call Counts:")
            for agent, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {agent}: {count}")


def export_trace_json(request_id: Optional[str] = None, output_file: Optional[str] = None):
    """Export trace(s) as JSON."""
    tracer = get_tracer()
    
    if request_id:
        spans = tracer.get_trace(request_id)
        data = {
            "request_id": request_id,
            "spans": [span.to_dict() for span in spans]
        }
    else:
        recent_spans = tracer.get_recent_spans(limit=100)
        traces: Dict[str, List] = {}
        for span in recent_spans:
            if span.request_id:
                if span.request_id not in traces:
                    traces[span.request_id] = []
                traces[span.request_id].append(span)
        
        data = {
            "traces": {
                rid: [span.to_dict() for span in spans]
                for rid, spans in traces.items()
            }
        }
    
    json_str = json.dumps(data, indent=2, default=str)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(json_str)
        print(f"Trace exported to {output_file}")
    else:
        print(json_str)


def main():
    """Main CLI interface."""
    import argparse
    
    # Load traces from persistent storage
    tracer = get_tracer()
    loaded = tracer.load_from_file()
    if loaded > 0:
        logger = logging.getLogger(__name__)
        logger.debug(f"Loaded {loaded} spans from persistent storage")
    
    parser = argparse.ArgumentParser(description="View agent calls and traces")
    parser.add_argument("--request-id", help="View trace for specific request ID")
    parser.add_argument("--recent", type=int, nargs='?', const=10, default=None, help="View N recent traces (default: 10)")
    parser.add_argument("--agents", type=int, nargs='?', const=20, default=None, help="View N recent agent calls (default: 20)")
    parser.add_argument("--summary", action="store_true", help="Show trace summary")
    parser.add_argument("--export", help="Export trace(s) as JSON to file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.json:
        # JSON output
        tracer = get_tracer()
        if args.request_id:
            spans = tracer.get_trace(args.request_id)
            data = {"request_id": args.request_id, "spans": [span.to_dict() for span in spans]}
        else:
            limit = (args.recent if args.recent else 10) * 10
            recent = tracer.get_recent_spans(limit=limit)
            data = {"spans": [span.to_dict() for span in recent]}
        print(json.dumps(data, indent=2, default=str))
    elif args.export:
        export_trace_json(args.request_id, args.export)
    elif args.request_id:
        view_trace_by_request_id(args.request_id)
    elif args.summary:
        view_trace_summary()
    elif args.agents is not None:
        view_agent_calls(args.agents if args.agents else 20)
    elif args.recent is not None:
        view_recent_traces(args.recent if args.recent else 10)
    else:
        # Default: show recent traces
        view_recent_traces(10)


if __name__ == "__main__":
    main()
