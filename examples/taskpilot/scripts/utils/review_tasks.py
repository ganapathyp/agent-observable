"""Human-in-the-loop task review CLI.

Manages tasks in REVIEW state, allowing users to approve or reject them.
"""
import sys
import asyncio
import logging
from pathlib import Path

# Configure logging if not already configured (for CLI context)
# This ensures decision logs are written to taskpilot.log for Filebeat
try:
    from pythonjsonlogger import jsonlogger
    from taskpilot.core.config import get_paths
    
    # Only configure if not already configured
    root_logger = logging.getLogger()
    if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        paths = get_paths()
        log_dir = paths.logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "taskpilot.log"
        
        file_handler = logging.FileHandler(log_file)
        json_formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            timestamp=True
        )
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
except Exception:
    # If logging setup fails, continue without it (decision_logs.jsonl will still work)
    pass

from taskpilot.core.task_store import get_task_store, TaskStatus  # type: ignore
from taskpilot.core.guardrails.decision_log import PolicyDecision, DecisionType, DecisionResult  # type: ignore
from taskpilot.core.guardrails.decision_logger import get_decision_logger  # type: ignore

def format_task_compact(task) -> str:
    """Format task for compact display."""
    return (
        f"  [{task.id[:20]}...] {task.title[:50]:<50} "
        f"Priority: {task.priority:<8} Created: {task.created_at[:19]}"
    )

def format_task_detail(task) -> str:
    """Format task for detailed display."""
    lines = [
        f"ID: {task.id}",
        f"Title: {task.title}",
        f"Priority: {task.priority}",
        f"Status: {task.status.value.upper()}",
        f"Created: {task.created_at}",
    ]
    
    if task.description:
        lines.append(f"\nDescription:\n{task.description}")
    
    if task.reviewer_response:
        lines.append(f"\nReviewer Response:\n{task.reviewer_response}")
    
    return "\n".join(lines)

def list_review_tasks(store):
    """List all tasks in REVIEW state."""
    tasks = store.list_tasks(status=TaskStatus.REVIEW)
    
    if not tasks:
        print("No tasks require review.")
        return []
    
    print(f"\n📋 Tasks Requiring Review ({len(tasks)} tasks)")
    print("=" * 80)
    
    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}] {format_task_compact(task)}")
        if task.reviewer_response:
            print(f"    Reviewer: {task.reviewer_response[:100]}...")
    
    return tasks

def _log_decision_sync(logger, decision):
    """Helper to log decision and flush in sync context."""
    async def _log_and_flush():
        await logger.log_decision(decision)
        await logger.flush()  # Ensure it's written immediately
    
    try:
        asyncio.run(_log_and_flush())
    except Exception as e:
        # If async logging fails, at least the decision is in decision_logs.jsonl
        pass

def review_task(store, task_id: str, decision: str):
    """Approve or reject a task in REVIEW state.
    
    Args:
        store: TaskStore instance
        task_id: Task ID to review
        decision: 'approve' or 'reject'
    """
    task = store.get_task(task_id)
    
    if not task:
        print(f"❌ Task not found: {task_id}", file=sys.stderr)
        return False
    
    if task.status != TaskStatus.REVIEW:
        print(
            f"❌ Task {task_id} is not in REVIEW state (current: {task.status.value})",
            file=sys.stderr
        )
        return False
    
    # Log policy decision for human review actions
    try:
        decision_result = DecisionResult.ALLOW if decision.lower() == "approve" else DecisionResult.DENY
        policy_decision = PolicyDecision.create(
            decision_type=DecisionType.HUMAN_APPROVAL,
            result=decision_result,
            reason=f"Human {decision.lower()}ed task: {task.title[:100] if task.title else 'N/A'}",
            context={
                "task_id": task_id,
                "task_title": task.title or "N/A",
                "task_priority": task.priority or "N/A",
                "reviewer_response": task.reviewer_response or "N/A",
                "human_decision": decision.lower()
            },
            tool_name="review_task",
            agent_id="HumanReviewer"
        )
        
        # Log the decision asynchronously
        decision_logger = get_decision_logger()
        try:
            # Ensure decision logger background task is started
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    # No running loop, create one and run
                    _log_decision_sync(decision_logger, policy_decision)
                else:
                    # Loop is running, schedule the coroutine
                    asyncio.create_task(decision_logger.log_decision(policy_decision))
            except RuntimeError:
                # No event loop exists, create one
                _log_decision_sync(decision_logger, policy_decision)
        except Exception as e:
            # Don't fail the review if logging fails
            print(f"⚠️  Warning: Failed to log policy decision: {e}", file=sys.stderr)
    except Exception as e:
        # Don't fail the review if decision logging setup fails
        print(f"⚠️  Warning: Could not create policy decision log: {e}", file=sys.stderr)
    
    if decision.lower() == "approve":
        store.update_task_status(
            task_id,
            TaskStatus.APPROVED,
            reviewer_response=f"Human approved: {task.reviewer_response or 'N/A'}"
        )
        print(f"✅ Task {task_id} approved")
        return True
    elif decision.lower() == "reject":
        store.update_task_status(
            task_id,
            TaskStatus.REJECTED,
            reviewer_response=f"Human rejected: {task.reviewer_response or 'N/A'}"
        )
        print(f"❌ Task {task_id} rejected")
        return True
    else:
        print(f"❌ Invalid decision: {decision}. Use 'approve' or 'reject'", file=sys.stderr)
        return False

def interactive_review(store):
    """Interactive review mode."""
    tasks = list_review_tasks(store)
    
    if not tasks:
        return
    
    print("\n" + "=" * 80)
    print("Interactive Review Mode")
    print("=" * 80)
    
    while True:
        try:
            choice = input(
                "\nEnter task number to review (or 'q' to quit, 'l' to list): "
            ).strip()
            
            if choice.lower() == 'q':
                break
            
            if choice.lower() == 'l':
                tasks = list_review_tasks(store)
                continue
            
            try:
                task_idx = int(choice) - 1
                if 0 <= task_idx < len(tasks):
                    task = tasks[task_idx]
                    print("\n" + "=" * 80)
                    print(format_task_detail(task))
                    print("=" * 80)
                    
                    decision = input("\nApprove or Reject? (a/r/q): ").strip().lower()
                    
                    if decision == 'q':
                        continue
                    elif decision == 'a':
                        review_task(store, task.id, "approve")
                        # Refresh list
                        tasks = store.list_tasks(status=TaskStatus.REVIEW)
                    elif decision == 'r':
                        review_task(store, task.id, "reject")
                        # Refresh list
                        tasks = store.list_tasks(status=TaskStatus.REVIEW)
                    else:
                        print("Invalid choice. Use 'a' (approve), 'r' (reject), or 'q' (quit)")
                else:
                    print(f"Invalid task number. Choose 1-{len(tasks)}")
            except ValueError:
                print("Invalid input. Enter a number, 'q', or 'l'")
        
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break

def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Review tasks requiring human approval",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all tasks requiring review
  %(prog)s --list
  
  # Interactive review mode
  %(prog)s
  
  # Approve a specific task
  %(prog)s --approve task_20241220_123456_789012
  
  # Reject a specific task
  %(prog)s --reject task_20241220_123456_789012
        """
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all tasks requiring review"
    )
    parser.add_argument(
        "--approve", "-a",
        metavar="TASK_ID",
        help="Approve a specific task by ID"
    )
    parser.add_argument(
        "--reject", "-r",
        metavar="TASK_ID",
        help="Reject a specific task by ID"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show review statistics"
    )
    
    args = parser.parse_args()
    
    store = get_task_store()
    
    # Show statistics
    if args.stats:
        stats = store.get_stats()
        total = sum(stats.values())
        review_count = stats.get(TaskStatus.REVIEW.value, 0)
        review_pct = (review_count / total * 100) if total > 0 else 0
        
        print(f"\n📊 Review Statistics")
        print("=" * 40)
        print(f"Total tasks: {total}")
        print(f"Tasks in REVIEW: {review_count} ({review_pct:.1f}%)")
        print(f"Target: <5% in REVIEW state")
        if review_pct > 5:
            print("⚠️  Warning: Review rate exceeds 5% target")
        return
    
    # Approve specific task
    if args.approve:
        review_task(store, args.approve, "approve")
        return
    
    # Reject specific task
    if args.reject:
        review_task(store, args.reject, "reject")
        return
    
    # List tasks
    if args.list:
        list_review_tasks(store)
        return
    
    # Interactive mode (default)
    interactive_review(store)

if __name__ == "__main__":
    main()
