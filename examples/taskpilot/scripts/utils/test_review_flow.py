#!/usr/bin/env python3
"""Test script to create a task in REVIEW state for testing."""

import asyncio
import logging
from taskpilot.agents import create_planner, create_reviewer, create_executor
from taskpilot.core import build_workflow, create_audit_and_policy_middleware
from taskpilot.core.task_store import get_task_store, TaskStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_review_task():
    """Create a task that will be flagged for review."""
    print("Creating agents...")
    planner = create_planner()
    reviewer = create_reviewer()
    executor = create_executor()
    
    planner.middleware = create_audit_and_policy_middleware(planner.name)
    reviewer.middleware = create_audit_and_policy_middleware(reviewer.name)
    executor.middleware = create_audit_and_policy_middleware(executor.name)
    
    workflow = build_workflow(planner, reviewer, executor)
    
    # Try multiple requests that might trigger REVIEW
    test_requests = [
        "Create a task to access sensitive customer data",
        "Create a task to modify production database",
        "Create a task to delete user accounts",
    ]
    
    store = get_task_store()
    initial_count = len(store.list_tasks(status=TaskStatus.REVIEW))
    
    for request in test_requests:
        print(f"\n{'='*60}")
        print(f"Testing: {request}")
        print('='*60)
        
        try:
            result = await workflow.run(request)
            print("✓ Workflow completed")
        except Exception as e:
            print(f"✗ Error: {e}")
            continue
        
        # Check for review tasks
        review_tasks = store.list_tasks(status=TaskStatus.REVIEW)
        new_review_tasks = review_tasks[:len(review_tasks) - initial_count]
        
        if new_review_tasks:
            print(f"\n✓ Created {len(new_review_tasks)} task(s) in REVIEW state:")
            for task in new_review_tasks:
                print(f"  - {task.id}: {task.title}")
            break
        else:
            print("  No tasks in REVIEW state (may have been auto-approved/rejected)")
    
    # Final status
    final_review = store.list_tasks(status=TaskStatus.REVIEW)
    print(f"\n{'='*60}")
    print(f"Total tasks in REVIEW: {len(final_review)}")
    if final_review:
        print("\nTasks ready for review:")
        for task in final_review:
            print(f"  [{task.id}] {task.title}")
        print("\nTo review:")
        print("  .venv/bin/python review_tasks.py")
    else:
        print("\nNo tasks in REVIEW. Try running main.py with different requests.")

if __name__ == "__main__":
    asyncio.run(create_review_task())
