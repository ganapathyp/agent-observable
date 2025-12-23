"""Embedded OPA policy evaluator."""
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

try:
    from opa import OPAClient
    OPA_AVAILABLE = True
except ImportError:
    OPAClient = None  # type: ignore
    OPA_AVAILABLE = False

logger = logging.getLogger(__name__)


class EmbeddedOPA:
    """Embedded OPA policy evaluator using opa-python library."""

    def __init__(self, policy_dir: Optional[Path] = None):
        """Initialize embedded OPA.

        Args:
            policy_dir: Directory containing .rego policy files
        """
        self.policy_dir = policy_dir or self._find_policy_dir()
        self.policies: Dict[str, str] = {}
        self._initialized = False

        if not OPA_AVAILABLE:
            logger.warning(
                "opa-python not available. Install with: pip install opa-python"
            )
            return

        self._load_policies()

    def _find_policy_dir(self) -> Path:
        """Find the policies directory."""
        # Look for policies directory relative to taskpilot root
        current = Path(__file__)
        # Go up: guardrails -> core -> src -> taskpilot
        taskpilot_dir = current.parent.parent.parent.parent
        policy_dir = taskpilot_dir / "policies"
        return policy_dir

    def _load_policies(self):
        """Load all .rego policy files from policy directory."""
        if not self.policy_dir or not self.policy_dir.exists():
            logger.warning(f"Policy directory not found: {self.policy_dir}")
            return

        for policy_file in self.policy_dir.glob("*.rego"):
            try:
                with open(policy_file, "r", encoding="utf-8") as f:
                    policy_content = f.read()
                    policy_name = policy_file.stem
                    self.policies[policy_name] = policy_content
                    logger.debug(f"Loaded policy: {policy_name}")
            except Exception as e:
                logger.error(f"Error loading policy {policy_file}: {e}")

    def evaluate(
        self, package: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a policy using embedded OPA.

        Args:
            package: Policy package (e.g., "taskpilot.tool_calls")
            input_data: Input data for policy evaluation

        Returns:
            Policy evaluation result
        """
        # Always use simple evaluator (works without opa-python library)
        # This implements the policy logic directly in Python
        try:
            return self._evaluate_simple(package, input_data)
        except Exception as e:
            logger.error(f"Error evaluating policy: {e}", exc_info=True)
            # On error, deny by default (safer than allowing)
            return {"allow": False, "deny": [f"Policy evaluation error: {str(e)}"], "require_approval": False}

    def _evaluate_simple(self, package: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple policy evaluator for tool_calls policy.

        This is a simplified evaluator that implements the logic from tool_calls.rego
        without requiring a full OPA server.
        """
        result = {
            "allow": False,
            "deny": [],
            "require_approval": False,
        }

        if package != "taskpilot.tool_calls":
            return result

        tool_name = input_data.get("tool_name", "")
        agent_type = input_data.get("agent_type", "")
        parameters = input_data.get("parameters", {})

        # Rule 1: Check for deny conditions first (takes precedence)
        if tool_name == "delete_task":
            result["deny"].append("delete_task tool is not authorized")
            return result  # Deny takes precedence

        # Rule 2: Allow create_task for PlannerAgent
        if tool_name == "create_task" and agent_type == "PlannerAgent":
            # Validate parameters
            title = parameters.get("title", "")
            priority = parameters.get("priority", "")
            
            # Check parameter validation
            if title and len(title) <= 500 and priority in ["high", "medium", "low"]:
                result["allow"] = True

                # Check if approval required (high priority + sensitive in title)
                if priority == "high" and "sensitive" in title.lower():
                    result["require_approval"] = True
            # If validation fails, allow remains False

        # Rule 3: Allow notify_external_system for ExecutorAgent/ReviewerAgent
        elif tool_name == "notify_external_system":
            if agent_type in ["ExecutorAgent", "ReviewerAgent"]:
                message = parameters.get("message", "")
                # Check if message contains "delete" (should be denied)
                if "delete" not in message.lower():
                    result["allow"] = True
                # If contains "delete", allow remains False (implicit deny)

        return result


# Global embedded OPA instance
_embedded_opa: Optional[EmbeddedOPA] = None


def get_embedded_opa() -> EmbeddedOPA:
    """Get or create global embedded OPA instance."""
    global _embedded_opa
    if _embedded_opa is None:
        _embedded_opa = EmbeddedOPA()
    return _embedded_opa
