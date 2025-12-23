"""Centralized metric name constants for consistent naming and easy discovery.

All metric names follow the pattern: {category}.{entity}.{metric}
- Use dots (.) as separators
- Use lowercase with underscores for multi-word names
- Group related metrics by category prefix

Categories:
- workflow.* - Workflow-level metrics
- agent.* - Agent-specific metrics
- llm.* - LLM-related metrics (cost, tokens)
- task.* - Task lifecycle metrics
- policy.* - Policy enforcement metrics
- guardrails.* - Guardrails validation metrics
- observability.* - Observability system performance metrics
- health.* - Health check metrics
"""

# ============================================================================
# Workflow Metrics
# ============================================================================

WORKFLOW_RUNS = "workflow.runs"
WORKFLOW_SUCCESS = "workflow.success"
WORKFLOW_ERRORS = "workflow.errors"
WORKFLOW_LATENCY_MS = "workflow.latency_ms"

# ============================================================================
# Agent Metrics
# ============================================================================

def agent_invocations(agent_name: str) -> str:
    """Agent invocation counter: agent.{agent_name}.invocations"""
    return f"agent.{agent_name}.invocations"

def agent_success(agent_name: str) -> str:
    """Agent success counter: agent.{agent_name}.success"""
    return f"agent.{agent_name}.success"

def agent_errors(agent_name: str) -> str:
    """Agent error counter: agent.{agent_name}.errors"""
    return f"agent.{agent_name}.errors"

def agent_latency_ms(agent_name: str) -> str:
    """Agent latency histogram: agent.{agent_name}.latency_ms"""
    return f"agent.{agent_name}.latency_ms"

def agent_guardrails_blocked(agent_name: str) -> str:
    """Guardrails blocked counter: agent.{agent_name}.guardrails.blocked"""
    return f"agent.{agent_name}.guardrails.blocked"

def agent_guardrails_output_blocked(agent_name: str) -> str:
    """Guardrails output blocked counter: agent.{agent_name}.guardrails.output_blocked"""
    return f"agent.{agent_name}.guardrails.output_blocked"

def agent_policy_violations(agent_name: str) -> str:
    """Agent policy violations counter: agent.{agent_name}.policy.violations"""
    return f"agent.{agent_name}.policy.violations"

# ============================================================================
# LLM Metrics
# ============================================================================

# Cost metrics
LLM_COST_TOTAL = "llm.cost.total"

def llm_cost_agent(agent_name: str) -> str:
    """LLM cost per agent: llm.cost.agent.{agent_name}"""
    return f"llm.cost.agent.{agent_name}"

def llm_cost_model(model: str) -> str:
    """LLM cost per model: llm.cost.model.{model}"""
    return f"llm.cost.model.{model}"

# Token metrics
LLM_TOKENS_INPUT_TOTAL = "llm.tokens.input.total"
LLM_TOKENS_OUTPUT_TOTAL = "llm.tokens.output.total"
LLM_TOKENS_TOTAL_ALL = "llm.tokens.total.all"

def llm_tokens_input_model(model: str) -> str:
    """LLM input tokens per model: llm.tokens.input.{model}"""
    return f"llm.tokens.input.{model}"

def llm_tokens_output_model(model: str) -> str:
    """LLM output tokens per model: llm.tokens.output.{model}"""
    return f"llm.tokens.output.{model}"

def llm_tokens_total_model(model: str) -> str:
    """LLM total tokens per model: llm.tokens.total.{model}"""
    return f"llm.tokens.total.{model}"

# Quality metrics
LLM_QUALITY_USER_CONFIRMED_CORRECT = "llm.quality.user_confirmed_correct"
LLM_QUALITY_USER_CONFIRMED_INCORRECT = "llm.quality.user_confirmed_incorrect"

# ============================================================================
# Task Metrics
# ============================================================================

TASKS_CREATED = "tasks.created"
TASKS_APPROVED = "tasks.approved"
TASKS_REJECTED = "tasks.rejected"
TASKS_REVIEW = "tasks.review"
TASKS_EXECUTED = "tasks.executed"
TASKS_REVIEWER_OUTPUT_EMPTY = "tasks.reviewer_output_empty"
TASKS_NO_PENDING_FOR_REVIEWER = "tasks.no_pending_for_reviewer"

# ============================================================================
# Policy Metrics
# ============================================================================

POLICY_VIOLATIONS_TOTAL = "policy.violations.total"

# ============================================================================
# Guardrails Metrics
# ============================================================================

# Guardrails metrics are agent-specific (use agent_guardrails_blocked above)

# ============================================================================
# Observability Performance Metrics
# ============================================================================

OBSERVABILITY_METRICS_COLLECTION_LATENCY_MS = "observability.metrics_collection_latency_ms"
OBSERVABILITY_TRACE_EXPORT_LATENCY_MS = "observability.trace_export_latency_ms"
OBSERVABILITY_DECISION_LOG_FLUSH_LATENCY_MS = "observability.decision_log_flush_latency_ms"
OBSERVABILITY_TRACE_EXPORT_QUEUE_SIZE = "observability.trace_export_queue_size"
OBSERVABILITY_TRACE_EXPORT_FAILURES = "observability.trace_export_failures"
OBSERVABILITY_OTEL_COLLECTOR_HEALTH = "observability.otel_collector_health"

# ============================================================================
# Health Check Metrics
# ============================================================================

HEALTH_STATUS = "health.status"
HEALTH_CHECK_TASK_STORE = "health.check.task_store"
HEALTH_CHECK_GUARDRAILS = "health.check.guardrails"

def health_check(check_name: str) -> str:
    """Health check gauge: health.check.{check_name}"""
    return f"health.check.{check_name}"
