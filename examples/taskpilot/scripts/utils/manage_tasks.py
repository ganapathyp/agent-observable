"""Task management CLI - view, delete, and manage tasks."""
import sys
import argparse
from pathlib import Path
from taskpilot.core.task_store import get_task_store, TaskStatus  # type: ignore

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manage TaskPilot tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View all tasks
  python manage_tasks.py list

  # View tasks by status
  python manage_tasks.py list --status rejected

  # View task statistics
  python manage_tasks.py stats

  # View specific task
  python manage_tasks.py show <task_id>

  # Delete specific task
  python manage_tasks.py delete <task_id>

  # Delete all tasks with a status
  python manage_tasks.py delete --status rejected

  # Keep only 200 most recent tasks (delete old ones)
  python manage_tasks.py cleanup --keep 200

  # Delete all tasks (WARNING: destructive!)
  python manage_tasks.py delete --all
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List tasks')
    list_parser.add_argument(
        '--status',
        choices=["pending", "approved", "rejected", "review", "executed", "failed"],
        help="Filter by status"
    )
    list_parser.add_argument(
        '--limit',
        type=int,
        help="Limit number of tasks"
    )
    list_parser.add_argument(
        '--json',
        action='store_true',
        help="Output as JSON"
    )
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show task statistics')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show specific task')
    show_parser.add_argument('task_id', help='Task ID to show')
    show_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete tasks')
    delete_group = delete_parser.add_mutually_exclusive_group(required=True)
    delete_group.add_argument('task_id', nargs='?', help='Task ID to delete')
    delete_group.add_argument('--status', choices=["pending", "approved", "rejected", "review", "executed", "failed"],
                             help='Delete all tasks with this status')
    delete_group.add_argument('--all', action='store_true', help='Delete ALL tasks (WARNING: destructive!)')
    delete_parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old tasks')
    cleanup_parser.add_argument(
        '--keep',
        type=int,
        default=200,
        help='Number of most recent tasks to keep (default: 200)'
    )
    cleanup_parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    store = get_task_store()
    
    # List tasks
    if args.command == 'list':
        status_filter = None
        if args.status:
            status_filter = TaskStatus(args.status)
        
        tasks = store.list_tasks(status=status_filter, limit=args.limit)
        
        if args.json:
            import json
            print(json.dumps([task.to_dict() for task in tasks], indent=2))
        else:
            if not tasks:
                print("No tasks found.")
                return
            
            print(f"\n📋 Task List ({len(tasks)} tasks)")
            print("=" * 60)
            
            for i, task in enumerate(tasks, 1):
                status_emoji = {
                    TaskStatus.PENDING: "⏳",
                    TaskStatus.APPROVED: "✅",
                    TaskStatus.REJECTED: "❌",
                    TaskStatus.REVIEW: "👤",
                    TaskStatus.EXECUTED: "✓",
                    TaskStatus.FAILED: "⚠️"
                }
                emoji = status_emoji.get(task.status, "❓")
                
                print(f"\n[{i}] {emoji} {task.id}")
                print(f"    Title: {task.title[:80]}")
                print(f"    Status: {task.status.value.upper()} | Priority: {task.priority}")
                print(f"    Created: {task.created_at}")
                if i < len(tasks):
                    print("-" * 60)
    
    # Show statistics
    elif args.command == 'stats':
        stats = store.get_stats()
        total = sum(stats.values())
        print(f"\n📊 Task Statistics")
        print(f"{'=' * 40}")
        print(f"Total tasks: {total}")
        print()
        for status, count in sorted(stats.items()):
            if count > 0:
                percentage = (count / total * 100) if total > 0 else 0
                print(f"  {status:15} {count:4} ({percentage:5.1f}%)")
    
    # Show specific task
    elif args.command == 'show':
        task = store.get_task(args.task_id)
        if not task:
            print(f"❌ Task not found: {args.task_id}", file=sys.stderr)
            sys.exit(1)
        
        if args.json:
            import json
            print(json.dumps(task.to_dict(), indent=2))
        else:
            status_emoji = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.APPROVED: "✅",
                TaskStatus.REJECTED: "❌",
                TaskStatus.REVIEW: "👤",
                TaskStatus.EXECUTED: "✓",
                TaskStatus.FAILED: "⚠️"
            }
            emoji = status_emoji.get(task.status, "❓")
            
            print(f"\n{emoji} Task Details")
            print("=" * 60)
            print(f"ID: {task.id}")
            print(f"Title: {task.title}")
            print(f"Priority: {task.priority}")
            print(f"Status: {task.status.value.upper()}")
            print(f"Created: {task.created_at}")
            if task.reviewed_at:
                print(f"Reviewed: {task.reviewed_at}")
            if task.executed_at:
                print(f"Executed: {task.executed_at}")
            if task.description:
                print(f"\nDescription:\n{task.description}")
            if task.reviewer_response:
                print(f"\nReviewer Response:\n{task.reviewer_response}")
            if task.error:
                print(f"\n❌ Error:\n{task.error}")
    
    # Delete tasks
    elif args.command == 'delete':
        if args.all:
            if not args.confirm:
                response = input(f"⚠️  WARNING: This will delete ALL tasks. Are you sure? (yes/no): ")
                if response.lower() != 'yes':
                    print("Cancelled.")
                    return
            count = store.clear_all_tasks()
            print(f"✅ Deleted all {count} tasks")
        
        elif args.status:
            status = TaskStatus(args.status)
            if not args.confirm:
                stats = store.get_stats()
                count = stats.get(status.value, 0)
                response = input(f"⚠️  Delete all {count} tasks with status '{status.value}'? (yes/no): ")
                if response.lower() != 'yes':
                    print("Cancelled.")
                    return
            count = store.delete_tasks_by_status(status)
            print(f"✅ Deleted {count} tasks with status '{status.value}'")
        
        elif args.task_id:
            if store.delete_task(args.task_id):
                print(f"✅ Deleted task: {args.task_id}")
            else:
                print(f"❌ Task not found: {args.task_id}", file=sys.stderr)
                sys.exit(1)
    
    # Cleanup old tasks
    elif args.command == 'cleanup':
        total_before = len(store._tasks)
        if total_before <= args.keep:
            print(f"✅ No cleanup needed. You have {total_before} tasks (keeping {args.keep})")
            return
        
        to_delete = total_before - args.keep
        if not args.confirm:
            response = input(
                f"⚠️  This will delete {to_delete} old tasks, keeping the {args.keep} most recent. "
                f"Continue? (yes/no): "
            )
            if response.lower() != 'yes':
                print("Cancelled.")
                return
        
        deleted = store.delete_old_tasks(keep_count=args.keep)
        total_after = len(store._tasks)
        print(f"✅ Cleanup complete: Deleted {deleted} old tasks, kept {total_after} most recent")

if __name__ == "__main__":
    main()
