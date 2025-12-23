"""Centralized trace/span name constants for consistent naming and easy discovery.

All span names follow the pattern: {entity}.{operation}
- Use dots (.) as separators
- Use lowercase with underscores for multi-word names
- Keep names concise but descriptive

Span Hierarchy:
- workflow.run (root span)
  - agent.{agent_name}.run (agent execution)
    - tool.{tool_name}.call (tool invocation, if applicable)
"""

# ============================================================================
# Workflow Spans
# ============================================================================

WORKFLOW_RUN = "workflow.run"

# ============================================================================
# Agent Spans
# ============================================================================

def agent_run(agent_name: str) -> str:
    """Agent execution span: agent.{agent_name}.run"""
    return f"agent.{agent_name}.run"

# ============================================================================
# Tool Spans
# ============================================================================

def tool_call(tool_name: str) -> str:
    """Tool invocation span: tool.{tool_name}.call"""
    return f"tool.{tool_name}.call"
