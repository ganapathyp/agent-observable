"""Centralized trace/span name constants for consistent naming and easy discovery.

All span names follow the pattern: taskpilot.{entity}.{operation}
- Use dots (.) as separators
- Use lowercase with underscores for multi-word names
- Keep names concise but descriptive
- Prefix with "taskpilot." for proper hierarchy in Jaeger

Span Hierarchy:
- taskpilot.workflow.run (root span)
  - taskpilot.agent.{agent_name}.run (agent execution)
    - taskpilot.tool.{tool_name}.call (tool invocation, if applicable)
"""

# ============================================================================
# Workflow Spans
# ============================================================================

WORKFLOW_RUN = "taskpilot.workflow.run"

# ============================================================================
# Agent Spans
# ============================================================================

def agent_run(agent_name: str) -> str:
    """Agent execution span: taskpilot.agent.{agent_name}.run"""
    return f"taskpilot.agent.{agent_name}.run"

# ============================================================================
# Tool Spans
# ============================================================================

def tool_call(tool_name: str) -> str:
    """Tool invocation span: taskpilot.tool.{tool_name}.call"""
    return f"taskpilot.tool.{tool_name}.call"
