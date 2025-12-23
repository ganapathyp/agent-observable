"""Centralized policy decision type constants for consistent naming.

This module provides constants that match the DecisionType and DecisionResult
enums in decision_log.py. Import from decision_log.py for the actual enums.
"""

# Re-export from decision_log for convenience
from taskpilot.core.guardrails.decision_log import DecisionType, DecisionResult  # type: ignore

# Constants for easy reference (matching enum values)
DECISION_TYPE_TOOL_CALL = "TOOL_CALL"
DECISION_TYPE_INPUT_VALIDATION = "INPUT_VALIDATION"
DECISION_TYPE_OUTPUT_VALIDATION = "OUTPUT_VALIDATION"

DECISION_RESULT_ALLOW = "ALLOW"
DECISION_RESULT_DENY = "DENY"
DECISION_RESULT_REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
