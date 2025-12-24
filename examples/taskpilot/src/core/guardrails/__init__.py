"""Guardrails module for production safety."""
from agent_observable_policy import (  # type: ignore
    DecisionType,
    DecisionResult,
    PolicyDecision,
    DecisionLogger,
    EmbeddedOPA,
    OPAToolValidator as PolicyOPAToolValidator,
)
from agent_observable_policy import OPAToolValidator  # type: ignore
from taskpilot.core.observable import get_guardrails, get_decision_logger, get_opa  # type: ignore
from agent_observable_guardrails import NeMoGuardrailsWrapper  # type: ignore


def get_embedded_opa():
    """Get embedded OPA (convenience function)."""
    return get_opa()


__all__ = [
    "DecisionType",
    "DecisionResult",
    "PolicyDecision",
    "DecisionLogger",
    "OPAToolValidator",
    "EmbeddedOPA",
    "get_embedded_opa",
    "get_decision_logger",
    "get_opa",
    "get_guardrails",
    "NeMoGuardrailsWrapper",
]
