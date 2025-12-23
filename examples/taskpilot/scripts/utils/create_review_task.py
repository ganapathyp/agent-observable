#!/usr/bin/env python3
"""Script to create a task that will be flagged for REVIEW status.

This script runs the workflow with a request that is likely to trigger
the ReviewerAgent to return "REVIEW" instead of "APPROVE".
"""
import asyncio
import sys
import logging
from taskpilot.agents import create_planner, create_reviewer, create_executor  # type: ignore
from taskpilot.core import build_workflow, create_audit_and_policy_middleware  # type: ignore
from taskpilot.core.task_store import get_task_store, TaskStatus  # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def create_review_task():
    """Create a task that will be flagged for human review."""
    try:
        logger.info("Creating agents...")
        planner = create_planner()
        reviewer = create_reviewer()
        executor = create_executor()
        logger.info("Agents created successfully")

        # Set middleware
        logger.info("Setting up middleware...")
        planner.middleware = create_audit_and_policy_middleware(planner.name)
        reviewer.middleware = create_audit_and_policy_middleware(reviewer.name)
        executor.middleware = create_audit_and_policy_middleware(executor.name)

        # Build workflow
        logger.info("Building workflow...")
        workflow = build_workflow(planner, reviewer, executor)
        logger.info("Workflow built successfully")

        # Request that might trigger REVIEW (ambiguous or sensitive)
        # The reviewer should flag this for human judgment
        request = "Create a task to access sensitive customer financial data for analysis"
        
        logger.info(f"Running workflow with request: {request}")
        logger.info("(This request is designed to trigger REVIEW status)")
        
        result = await workflow.run(request)
        
        logger.info("Workflow completed")
        
        # Check if a REVIEW task was created
        store = get_task_store()
        review_tasks = store.list_tasks(status=TaskStatus.REVIEW)
        
        if review_tasks:
            task = review_tasks[0]
            logger.info(f"\n✅ REVIEW task created successfully!")
            logger.info(f"   Task ID: {task.id}")
            logger.info(f"   Title: {task.title}")
            logger.info(f"   Status: {task.status.value}")
            logger.info(f"   Reviewer Response: {task.reviewer_response}")
            logger.info(f"\n📋 To review this task:")
            logger.info(f"   .venv/bin/python review_tasks.py")
            logger.info(f"   .venv/bin/python review_tasks.py --approve {task.id}")
            logger.info(f"   .venv/bin/python review_tasks.py --reject {task.id}")
        else:
            # Check other statuses
            pending = store.list_tasks(status=TaskStatus.PENDING)
            approved = store.list_tasks(status=TaskStatus.APPROVED)
            rejected = store.list_tasks(status=TaskStatus.REJECTED)
            
            logger.info(f"\n⚠️  No REVIEW task created. Current tasks:")
            logger.info(f"   PENDING: {len(pending)}")
            logger.info(f"   APPROVED: {len(approved)}")
            logger.info(f"   REJECTED: {len(rejected)}")
            logger.info(f"   REVIEW: {len(review_tasks)}")
            
            if rejected:
                logger.info(f"\n   Latest task was REJECTED (not REVIEW)")
                logger.info(f"   Try a different request that's ambiguous rather than clearly unsafe")
        
        return result

    except KeyboardInterrupt:
        logger.warning("Workflow interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(create_review_task())

