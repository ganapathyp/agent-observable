"""OPA-based tool call validator with embedded OPA support."""
import logging
import time
from typing import Optional, Dict, Any, Tuple
import os

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from taskpilot.core.guardrails.decision_log import (  # type: ignore
    DecisionType,
    DecisionResult,
    PolicyDecision,
)
from taskpilot.core.guardrails.decision_logger import get_decision_logger  # type: ignore
from taskpilot.core.guardrails.opa_embedded import get_embedded_opa  # type: ignore

logger = logging.getLogger(__name__)


class OPAToolValidator:
    """OPA-based tool call validator with embedded OPA support."""

    def __init__(
        self,
        opa_url: Optional[str] = None,
        use_embedded: bool = True,
    ):
        """Initialize OPA tool validator.

        Args:
            opa_url: OPA server URL (defaults to http://localhost:8181)
                     Only used if use_embedded=False
            use_embedded: If True, use embedded OPA (default). If False, use HTTP API.
        """
        self.opa_url = opa_url or os.getenv("OPA_URL", "http://localhost:8181")
        self.package = "taskpilot.tool_calls"
        self.use_embedded = use_embedded

        if use_embedded:
            self.embedded_opa = get_embedded_opa()
            self._enabled = True
            logger.info("Using embedded OPA for policy evaluation")
        else:
            self.embedded_opa = None
            self._enabled = requests is not None
            if not self._enabled:
                logger.warning(
                    "requests library not available. OPA validation will be disabled."
                )

    async def validate_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        agent_type: str,
        agent_id: Optional[str] = None,
    ) -> Tuple[bool, str, bool]:
        """Validate tool call using OPA (embedded or HTTP).

        Args:
            tool_name: Name of the tool being called
            parameters: Tool call parameters
            agent_type: Type of agent making the call
            agent_id: Optional agent ID

        Returns:
            Tuple of (allowed, reason, requires_approval)
        """
        if not self._enabled:
            # Fallback: allow all if OPA not available
            logger.debug("OPA not available, allowing tool call")
            return True, "OPA not available", False

        start_time = time.time()

        try:
            input_data = {
                "tool_name": tool_name,
                "parameters": parameters,
                "agent_type": agent_type,
                "agent_id": agent_id,
            }

            # Use embedded OPA if enabled
            if self.use_embedded and self.embedded_opa:
                result_data = self.embedded_opa.evaluate(self.package, input_data)
            else:
                # Fallback to HTTP API
                response = requests.post(
                    f"{self.opa_url}/v1/data/{self.package.replace('.', '/')}",
                    json={"input": input_data},
                    timeout=2.0,
                )

                if response.status_code != 200:
                    logger.warning(
                        f"OPA returned status {response.status_code}, allowing tool call"
                    )
                    return True, f"OPA error: {response.status_code}", False

                result = response.json()
                result_data = result.get("result", {})

            allowed = result_data.get("allow", False)
            deny_reasons = result_data.get("deny", [])
            requires_approval = result_data.get("require_approval", False)

            reason = (
                deny_reasons[0] if deny_reasons else ("Allowed" if allowed else "Denied")
            )

            latency_ms = (time.time() - start_time) * 1000

            # Log decision
            decision = PolicyDecision.create(
                decision_type=DecisionType.TOOL_CALL,
                result=DecisionResult.REQUIRE_APPROVAL
                if requires_approval
                else (DecisionResult.ALLOW if allowed else DecisionResult.DENY),
                reason=reason,
                context={
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "agent_type": agent_type,
                },
                agent_id=agent_id,
                tool_name=tool_name,
                latency_ms=latency_ms,
            )

            decision_logger = get_decision_logger()
            await decision_logger.log_decision(decision)

            return allowed, reason, requires_approval

        except requests.exceptions.RequestException as e:
            logger.warning(f"OPA request failed: {e}, allowing tool call")
            return True, f"OPA unavailable: {str(e)}", False
        except Exception as e:
            logger.error(f"Error validating tool call with OPA: {e}", exc_info=True)
            # On error, allow but log
            return True, f"Validation error: {str(e)}", False
