"""DEPRECATED: Use agent_observable_policy.OPAToolValidator directly.

This file is kept for backward compatibility only.
All new code should import directly from agent_observable_policy.
"""
import warnings
from agent_observable_policy import OPAToolValidator  # type: ignore

warnings.warn(
    "taskpilot.core.guardrails.opa_tool_validator is deprecated. "
    "Import directly from agent_observable_policy instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["OPAToolValidator"]
