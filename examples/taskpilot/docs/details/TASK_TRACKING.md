# Task Tracking and REVIEW Flow

## What Happens When REVIEW is Triggered?

When the ReviewerAgent returns "REVIEW" (instead of "APPROVE"):

1. **Task is Created**: The PlannerAgent creates a task proposal, which is automatically stored in the task store with status `PENDING`.

2. **Review Decision is Recorded**: The ReviewerAgent's response is captured, and the task status is updated to `REJECTED` with the reviewer's response text.

3. **Workflow Ends**: The conditional branch evaluates to `False`, so the ExecutorAgent does not run, and the workflow ends.

4. **Task Remains in Store**: The task is **not deleted** - it remains in the task store with:
   - Status: `REJECTED`
   - Reviewer response: The full text of the reviewer's decision
   - Review timestamp: When the review was completed

5. **Task is Visible**: You can view rejected tasks using:
   ```bash
   .venv/bin/python list_tasks.py --status rejected
   ```

## How to View Tasks and Status

### View All Tasks

```bash
cd taskpilot
.venv/bin/python list_tasks.py
```

### View Tasks by Status

```bash
# Pending tasks (created but not reviewed)
.venv/bin/python list_tasks.py --status pending

# Approved tasks (reviewed and approved, awaiting execution)
.venv/bin/python list_tasks.py --status approved

# Rejected tasks (reviewed and rejected)
.venv/bin/python list_tasks.py --status rejected

# Executed tasks (successfully completed)
.venv/bin/python list_tasks.py --status executed
```

### View Specific Task

```bash
.venv/bin/python list_tasks.py --id task_20241220_123456_789012
```

### View Statistics

```bash
.venv/bin/python list_tasks.py --stats
```

Output:
```
📊 Task Statistics
========================================
Total tasks: 5
  pending: 1
  approved: 1
  rejected: 2
  executed: 1
```

### JSON Output

```bash
.venv/bin/python list_tasks.py --json
```

## Task Status Lifecycle

```
User Request
    ↓
PlannerAgent → Task created → Status: PENDING
    ↓
ReviewerAgent → Decision made
    ├─ APPROVE → Status: APPROVED
    └─ REVIEW → Status: REJECTED (workflow ends)
    ↓
ExecutorAgent (only if APPROVED) → Status: EXECUTED
```

## Task Storage

Tasks are automatically stored in `.tasks.json` in the `taskpilot/` directory. The file is created and updated by the middleware as tasks flow through the workflow.

**Example Task Structure**:
```json
{
  "task_20241220_123456_789012": {
    "id": "task_20241220_123456_789012",
    "title": "Prepare Board Deck",
    "priority": "high",
    "description": "Create a comprehensive board deck...",
    "status": "rejected",
    "created_at": "2024-12-20T12:34:56.789012",
    "reviewed_at": "2024-12-20T12:35:10.123456",
    "reviewer_response": "REVIEW: This task requires additional approval from the board.",
    "executed_at": null,
    "error": null
  }
}
```

## Example: Complete Flow

### Scenario: Task Gets Rejected

1. **User runs workflow**:
   ```bash
   ./run.sh
   # Input: "Create a task to access sensitive data"
   ```

2. **PlannerAgent creates task**:
   - Task stored with status: `PENDING`
   - Title: "Access Sensitive Data"
   - Priority: "high"

3. **ReviewerAgent reviews**:
   - Returns: "REVIEW: This task requires additional security clearance."
   - Task status updated to: `REJECTED`
   - Reviewer response stored

4. **Workflow ends** (executor doesn't run)

5. **View rejected task**:
   ```bash
   .venv/bin/python list_tasks.py --status rejected
   ```
   
   Output:
   ```
   [1] ID: task_20241220_123456_789012
   Title: Access Sensitive Data
   Priority: high
   Status: ❌ REJECTED
   Created: 2024-12-20T12:34:56.789012
   Reviewed: 2024-12-20T12:35:10.123456
   Reviewer: REVIEW: This task requires additional security clearance.
   ```

## Integration with Workflow

Task tracking is integrated into the middleware, so it happens automatically:

- **PlannerAgent output** → Task created (PENDING)
- **ReviewerAgent output** → Task status updated (APPROVED or REJECTED)
- **ExecutorAgent output** → Task status updated (EXECUTED)

No additional code needed - tasks are tracked automatically!
