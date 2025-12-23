"""View and analyze decision logs from OPA policy enforcement."""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict

def load_decision_logs(log_file: Optional[Path] = None) -> List[Dict]:
    """Load decision logs from JSONL file.
    
    Args:
        log_file: Path to decision log file (defaults to decision_logs.jsonl)
        
    Returns:
        List of decision log entries
    """
    if log_file is None:
        # Use the same path resolution as the decision logger
        try:
            import sys
            from pathlib import Path
            # Add project root to path if needed
            script_dir = Path(__file__).parent.parent.parent
            if str(script_dir) not in sys.path:
                sys.path.insert(0, str(script_dir))
            
            from taskpilot.core.config import get_paths
            paths = get_paths()
            log_file = paths.decision_logs_file
        except Exception as e:
            # Fallback: look in taskpilot root directory
            # __file__ is scripts/utils/view_decision_logs.py
            # parent.parent = scripts, parent.parent.parent = taskpilot
            taskpilot_dir = Path(__file__).parent.parent.parent
            log_file = taskpilot_dir / "decision_logs.jsonl"
    
    if not log_file.exists():
        return []
    
    decisions = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        decision = json.loads(line)
                        decision['_line_number'] = line_num
                        decisions.append(decision)
                    except json.JSONDecodeError as e:
                        print(f"Warning: Failed to parse line {line_num}: {e}", file=sys.stderr)
                        continue
    except Exception as e:
        print(f"Error reading decision log file: {e}", file=sys.stderr)
        return []
    
    return decisions


def format_decision(decision: Dict, detailed: bool = False) -> str:
    """Format a decision log entry for display.
    
    Args:
        decision: Decision log entry
        detailed: Whether to show detailed information
        
    Returns:
        Formatted string
    """
    decision_type = decision.get('decision_type', 'UNKNOWN')
    result = decision.get('result', 'UNKNOWN')
    timestamp = decision.get('timestamp')
    reason = decision.get('reason', '')
    context = decision.get('context', {})
    latency_ms = decision.get('latency_ms')
    tool_name = decision.get('tool_name') or context.get('tool_name', '')
    agent_id = decision.get('agent_id') or context.get('agent_type', '')
    
    # Format timestamp
    if timestamp:
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = datetime.fromtimestamp(timestamp)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            time_str = str(timestamp)
    else:
        time_str = 'N/A'
    
    # Result emoji
    result_emoji = "✅" if result.lower() == "allow" else "❌" if result.lower() == "deny" else "⚠️"
    
    # Build decision description
    decision_desc = decision_type
    if tool_name:
        decision_desc = f"{decision_type}: {tool_name}"
    if agent_id:
        decision_desc += f" (agent: {agent_id})"
    
    output = []
    output.append(f"{result_emoji} [{time_str}] {decision_desc}: {result}")
    
    if reason and reason not in ["Allowed", "Test"]:  # Skip generic reasons
        output.append(f"   Reason: {reason}")
    
    if latency_ms is not None:
        output.append(f"   Latency: {latency_ms:.2f}ms")
    
    # Always show tool name and agent if available (even if not detailed)
    if tool_name and not detailed:
        output.append(f"   Tool: {tool_name}")
    if agent_id and not detailed:
        output.append(f"   Agent: {agent_id}")
    
    if detailed and context:
        output.append(f"   Context:")
        for key, value in context.items():
            if key in ['tool_name', 'agent_type']:  # Already shown above
                continue
            if isinstance(value, dict):
                output.append(f"     {key}:")
                for k, v in value.items():
                    output.append(f"       {k}: {v}")
            else:
                output.append(f"     {key}: {value}")
    
    return "\n".join(output)


def view_recent_decisions(limit: int = 20, detailed: bool = False):
    """View recent decision log entries.
    
    Args:
        limit: Maximum number of entries to show
        detailed: Whether to show detailed information
    """
    decisions = load_decision_logs()
    
    if not decisions:
        print("No decision logs found")
        print(f"Expected location: {Path(__file__).parent / 'decision_logs.jsonl'}")
        return
    
    # Sort by timestamp (most recent first)
    decisions.sort(key=lambda d: d.get('timestamp', ''), reverse=True)
    
    print(f"Recent Decision Logs (showing {min(limit, len(decisions))} of {len(decisions)})\n")
    print("=" * 60)
    
    for decision in decisions[:limit]:
        print(format_decision(decision, detailed))
        print()


def view_decision_summary():
    """View summary statistics of decision logs."""
    decisions = load_decision_logs()
    
    if not decisions:
        print("No decision logs found")
        return
    
    # Calculate statistics
    total = len(decisions)
    by_type = defaultdict(int)
    by_result = defaultdict(int)
    total_latency = 0
    latency_count = 0
    
    for decision in decisions:
        decision_type = decision.get('decision_type', 'UNKNOWN')
        result = decision.get('result', 'UNKNOWN')
        latency_ms = decision.get('latency_ms')
        
        by_type[decision_type] += 1
        by_result[result] += 1
        
        if latency_ms is not None:
            total_latency += latency_ms
            latency_count += 1
    
    print("Decision Log Summary\n")
    print("=" * 60)
    print(f"Total decisions: {total}")
    
    if by_result:
        print(f"\nBy Result:")
        for result, count in sorted(by_result.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            print(f"  {result}: {count} ({percentage:.1f}%)")
    
    if by_type:
        print(f"\nBy Type:")
        for decision_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            print(f"  {decision_type}: {count} ({percentage:.1f}%)")
    
    if latency_count > 0:
        avg_latency = total_latency / latency_count
        print(f"\nLatency Statistics:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Total samples: {latency_count}")


def view_denied_decisions(limit: int = 20):
    """View denied decisions (policy violations).
    
    Args:
        limit: Maximum number of entries to show
    """
    decisions = load_decision_logs()
    
    if not decisions:
        print("No decision logs found")
        return
    
    # Filter denied decisions
    denied = [d for d in decisions if d.get('result') == 'DENY']
    
    if not denied:
        print("No denied decisions found")
        return
    
    # Sort by timestamp (most recent first)
    denied.sort(key=lambda d: d.get('timestamp', ''), reverse=True)
    
    print(f"Denied Decisions (showing {min(limit, len(denied))} of {len(denied)})\n")
    print("=" * 60)
    
    for decision in denied[:limit]:
        print(format_decision(decision, detailed=True))
        print()


def view_by_tool(tool_name: str, limit: int = 20):
    """View decisions for a specific tool.
    
    Args:
        tool_name: Name of the tool to filter by
        limit: Maximum number of entries to show
    """
    decisions = load_decision_logs()
    
    if not decisions:
        print("No decision logs found")
        return
    
    # Filter by tool name
    tool_decisions = [
        d for d in decisions
        if d.get('context', {}).get('tool_name') == tool_name
    ]
    
    if not tool_decisions:
        print(f"No decisions found for tool: {tool_name}")
        return
    
    # Sort by timestamp (most recent first)
    tool_decisions.sort(key=lambda d: d.get('timestamp', ''), reverse=True)
    
    print(f"Decisions for Tool: {tool_name} (showing {min(limit, len(tool_decisions))} of {len(tool_decisions)})\n")
    print("=" * 60)
    
    for decision in tool_decisions[:limit]:
        print(format_decision(decision, detailed=True))
        print()


def export_decisions(output_file: str, format: str = 'json'):
    """Export decision logs to file.
    
    Args:
        output_file: Output file path
        format: Export format ('json' or 'jsonl')
    """
    decisions = load_decision_logs()
    
    if not decisions:
        print("No decision logs found")
        return
    
    output_path = Path(output_file)
    
    try:
        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(decisions, f, indent=2, default=str)
        else:  # jsonl
            with open(output_path, 'w', encoding='utf-8') as f:
                for decision in decisions:
                    f.write(json.dumps(decision, default=str) + '\n')
        
        print(f"Exported {len(decisions)} decisions to {output_file}")
    except Exception as e:
        print(f"Error exporting decisions: {e}", file=sys.stderr)


def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="View and analyze decision logs")
    parser.add_argument("--recent", type=int, nargs='?', const=20, default=None, help="View N recent decisions (default: 20)")
    parser.add_argument("--summary", action="store_true", help="Show decision summary statistics")
    parser.add_argument("--denied", type=int, nargs='?', const=20, default=None, help="View denied decisions (default: 20)")
    parser.add_argument("--tool", help="View decisions for specific tool")
    parser.add_argument("--detailed", action="store_true", help="Show detailed information")
    parser.add_argument("--export", help="Export decisions to file")
    parser.add_argument("--format", choices=['json', 'jsonl'], default='json', help="Export format (default: json)")
    parser.add_argument("--file", help="Path to decision log file (default: decision_logs.jsonl)")
    
    args = parser.parse_args()
    
    log_file = Path(args.file) if args.file else None
    
    if args.export:
        export_decisions(args.export, args.format)
    elif args.summary:
        view_decision_summary()
    elif args.denied is not None:
        view_denied_decisions(args.denied if args.denied else 20)
    elif args.tool:
        view_by_tool(args.tool, 20)
    elif args.recent is not None:
        view_recent_decisions(args.recent if args.recent else 20, args.detailed)
    else:
        # Default: show recent decisions
        view_recent_decisions(20, args.detailed)


if __name__ == "__main__":
    main()
