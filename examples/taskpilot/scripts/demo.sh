#!/bin/bash
# Quick demo script for TaskPilot workflow states

cd "$(dirname "$0")"

echo "=== TaskPilot Workflow States Demo ==="
echo ""

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    ./run.sh --help > /dev/null 2>&1 || echo "Run ./run.sh first to set up venv"
    exit 1
fi

echo "1. Testing normal flow (APPROVE → EXECUTED)..."
.venv/bin/python -c "
import asyncio
import sys
from taskpilot.agents import create_planner, create_reviewer, create_executor
from taskpilot.core import build_workflow, create_audit_and_policy_middleware

async def demo():
    try:
        planner = create_planner()
        reviewer = create_reviewer()
        executor = create_executor()
        
        planner.middleware = create_audit_and_policy_middleware(planner.name)
        reviewer.middleware = create_audit_and_policy_middleware(reviewer.name)
        executor.middleware = create_audit_and_policy_middleware(executor.name)
        
        workflow = build_workflow(planner, reviewer, executor)
        result = await workflow.run('Create a high priority task to prepare the board deck')
        print('✓ Normal flow completed')
    except Exception as e:
        print(f'✗ Error: {e}')
        sys.exit(1)

asyncio.run(demo())
" || exit 1

echo ""
echo "2. Viewing task statistics..."
.venv/bin/python list_tasks.py --stats

echo ""
echo "3. Recent tasks:"
.venv/bin/python list_tasks.py --limit 3

echo ""
echo "=== Demo Complete ==="
echo ""
echo "To test other states:"
echo "  - Review tasks: .venv/bin/python review_tasks.py"
echo "  - View by status: .venv/bin/python list_tasks.py --status <status>"
echo "  - See docs/TESTING_GUIDE.md for more scenarios"
