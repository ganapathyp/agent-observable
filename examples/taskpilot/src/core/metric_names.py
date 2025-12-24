"""Project-specific metric name constants for TaskPilot.

This file contains ONLY project-specific metrics (task lifecycle, etc.).
Generic metrics (workflow, agent, LLM, policy) are now standardized
in agent-observable-core and work across all frameworks automatically.

For generic metrics, use:
    from agent_observable_core import get_metric_standardizer
    standardizer = get_metric_standardizer(service_name="taskpilot")
    metric_name = standardizer.workflow_runs()
"""

# ============================================================================
# Task Lifecycle Metrics (Project-Specific)
# ============================================================================
# These are specific to TaskPilot's task management domain

TASKS_CREATED = "tasks.created"
TASKS_APPROVED = "tasks.approved"
TASKS_REJECTED = "tasks.rejected"
TASKS_REVIEW = "tasks.review"
TASKS_EXECUTED = "tasks.executed"
TASKS_REVIEWER_OUTPUT_EMPTY = "tasks.reviewer_output_empty"
TASKS_NO_PENDING_FOR_REVIEWER = "tasks.no_pending_for_reviewer"

# ============================================================================
# Health Check Metrics (Project-Specific)
# ============================================================================
# These are specific to TaskPilot's health checks

HEALTH_CHECK_TASK_STORE = "health.check.task_store"
HEALTH_CHECK_GUARDRAILS = "health.check.guardrails"

def health_check(check_name: str) -> str:
    """Health check gauge: health.check.{check_name}"""
    return f"health.check.{check_name}"

# ============================================================================
# Note: Generic Metrics
# ============================================================================
# For generic metrics (workflow, agent, LLM, policy), use the library standardizer:
#
#     from agent_observable_core import get_metric_standardizer
#     standardizer = get_metric_standardizer(service_name="taskpilot")
#     metric_name = standardizer.workflow_runs()
#     metric_name = standardizer.agent_invocations("PlannerAgent")
#     metric_name = standardizer.policy_violations_total()
#
# This ensures framework-agnostic, standardized metric names across all projects.
