"""Task list viewer CLI."""
import sys
import json
from pathlib import Path
from taskpilot.core.task_store import get_task_store, TaskStatus  # type: ignore

def format_task(task) -> str:
    """Format a task for display."""
    status_emoji = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.APPROVED: "✅",
        TaskStatus.REJECTED: "❌",
        TaskStatus.REVIEW: "👤",
        TaskStatus.EXECUTED: "✓",
        TaskStatus.FAILED: "⚠️"
    }
    
    emoji = status_emoji.get(task.status, "❓")
    status_str = f"{emoji} {task.status.value.upper()}"
    
    lines = [
        f"ID: {task.id}",
        f"Title: {task.title}",
        f"Priority: {task.priority}",
        f"Status: {status_str}",
        f"Created: {task.created_at}",
    ]
    
    if task.reviewed_at:
        lines.append(f"Reviewed: {task.reviewed_at}")
        if task.reviewer_response:
            lines.append(f"Reviewer: {task.reviewer_response[:100]}")
    
    if task.executed_at:
        lines.append(f"Executed: {task.executed_at}")
    
    if task.description:
        lines.append(f"Description: {task.description[:200]}")
    
    if task.error:
        lines.append(f"Error: {task.error}")
    
    return "\n".join(lines)

def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="View TaskPilot tasks")
    parser.add_argument(
        "--status",
        choices=["pending", "approved", "rejected", "review", "executed", "failed"],
        help="Filter by status"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of tasks"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show task statistics"
    )
    parser.add_argument(
        "--id",
        help="Show specific task by ID"
    )
    
    args = parser.parse_args()
    
    store = get_task_store()
    
    # Show specific task
    if args.id:
        task = store.get_task(args.id)
        if not task:
            print(f"Task not found: {args.id}", file=sys.stderr)
            sys.exit(1)
        
        if args.json:
            print(json.dumps(task.to_dict(), indent=2))
        else:
            print(format_task(task))
        return
    
    # Show statistics
    if args.stats:
        stats = store.get_stats()
        total = sum(stats.values())
        print(f"\n📊 Task Statistics")
        print(f"{'=' * 40}")
        print(f"Total tasks: {total}")
        for status, count in stats.items():
            if count > 0:
                print(f"  {status}: {count}")
        return
    
    # List tasks
    status_filter = None
    if args.status:
        status_filter = TaskStatus(args.status)
    
    tasks = store.list_tasks(status=status_filter, limit=args.limit)
    
    if args.json:
        print(json.dumps([task.to_dict() for task in tasks], indent=2))
    else:
        if not tasks:
            print("No tasks found.")
            return
        
        print(f"\n📋 Task List ({len(tasks)} tasks)")
        print("=" * 60)
        
        for i, task in enumerate(tasks, 1):
            print(f"\n[{i}] {format_task(task)}")
            if i < len(tasks):
                print("-" * 60)

if __name__ == "__main__":
    main()
