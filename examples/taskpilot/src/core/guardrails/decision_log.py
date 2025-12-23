"""Decision log data structures."""
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import uuid


class DecisionType(str, Enum):
    """Type of policy decision."""

    GUARDRAILS_INPUT = "guardrails_input"
    GUARDRAILS_OUTPUT = "guardrails_output"
    TOOL_CALL = "tool_call"
    INGRESS = "ingress"
    HUMAN_APPROVAL = "human_approval"


class DecisionResult(str, Enum):
    """Result of policy decision."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class PolicyDecision:
    """Structured policy decision log entry."""

    decision_id: str
    timestamp: datetime
    decision_type: DecisionType
    result: DecisionResult
    reason: str
    context: Dict[str, Any]
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    tool_name: Optional[str] = None
    policy_version: Optional[str] = None
    latency_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["decision_type"] = self.decision_type.value
        data["result"] = self.result.value
        return data

    @classmethod
    def create(
        cls,
        decision_type: DecisionType,
        result: DecisionResult,
        reason: str,
        context: Dict[str, Any],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        policy_version: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ) -> "PolicyDecision":
        """Create a new policy decision."""
        return cls(
            decision_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            decision_type=decision_type,
            result=result,
            reason=reason,
            context=context,
            user_id=user_id,
            agent_id=agent_id,
            tool_name=tool_name,
            policy_version=policy_version,
            latency_ms=latency_ms,
        )
