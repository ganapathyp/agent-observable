"""NeMo Guardrails wrapper for LLM I/O validation."""
from __future__ import annotations

import logging
import time
from typing import Optional, Tuple, Dict, Any, Callable
from pathlib import Path

try:
    from nemoguardrails import LLMRails, RailsConfig  # type: ignore
    NEMO_AVAILABLE = True
except ImportError:
    LLMRails = None  # type: ignore
    RailsConfig = None  # type: ignore
    NEMO_AVAILABLE = False

from agent_observable_policy import (
    DecisionType,
    DecisionResult,
    PolicyDecision,
)

logger = logging.getLogger(__name__)


class NeMoGuardrailsWrapper:
    """Wrapper for NeMo Guardrails integration."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        decision_logger_callback: Optional[Callable[[PolicyDecision], Any]] = None,
    ):
        """Initialize NeMo Guardrails wrapper.

        Args:
            config_path: Optional path to guardrails config file
            decision_logger_callback: Optional callback for logging decisions
                                      (receives PolicyDecision, returns awaitable or None)
        """
        self._enabled = NEMO_AVAILABLE
        self.rails: Optional[Any] = None
        self._decision_logger_callback = decision_logger_callback

        if not self._enabled:
            logger.warning(
                "NeMo Guardrails not available. Install with: pip install nemoguardrails"
            )
            return

        if config_path and config_path.exists():
            try:
                self.config = RailsConfig.from_path(str(config_path))
                self.rails = LLMRails(config=self.config)
                logger.info(f"NeMo Guardrails initialized from {config_path}")
            except Exception as e:
                logger.debug(f"NeMo Guardrails config file failed: {e}")
                self._enabled = False
        else:
            # No config file provided - disable NeMo Guardrails gracefully
            logger.debug("NeMo Guardrails not configured (no config.yml found)")
            logger.info("NeMo Guardrails disabled - provide guardrails/config.yml to enable")
            self._enabled = False

    async def validate_input(
        self, input_text: str, user_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Validate LLM input.

        Args:
            input_text: Input text to validate
            user_id: Optional user ID

        Returns:
            Tuple of (allowed, reason)
        """
        if not self._enabled or not self.rails:
            # Fallback: allow all if guardrails not available
            return True, "Guardrails not available"

        start_time = time.time()

        try:
            # Simple validation: check for obvious issues
            # In production, this would use NeMo Guardrails' full validation
            if not input_text or not input_text.strip():
                reason = "Empty input"
                allowed = False
            else:
                # Basic checks (can be enhanced with full NeMo Guardrails)
                # For now, just check length and basic patterns
                if len(input_text) > 100000:  # Very long input
                    reason = "Input too long"
                    allowed = False
                else:
                    allowed = True
                    reason = "Input validated"

            latency_ms = (time.time() - start_time) * 1000

            # Log decision via callback
            decision = PolicyDecision.create(
                decision_type=DecisionType.GUARDRAILS_INPUT,
                result=DecisionResult.ALLOW if allowed else DecisionResult.DENY,
                reason=reason,
                context={"input_length": len(input_text), "input_preview": input_text[:100]},
                user_id=user_id,
                latency_ms=latency_ms,
            )

            if self._decision_logger_callback:
                try:
                    result = self._decision_logger_callback(decision)
                    if result and hasattr(result, "__await__"):
                        await result
                except Exception as e:
                    logger.debug(f"Failed to log decision: {e}")

            return allowed, reason

        except Exception as e:
            logger.error(f"Error validating input with NeMo Guardrails: {e}", exc_info=True)
            # On error, allow but log
            return True, f"Validation error: {str(e)}"

    async def validate_output(
        self, output_text: str, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Validate LLM output.

        Args:
            output_text: Output text to validate
            context: Optional context dictionary

        Returns:
            Tuple of (allowed, reason)
        """
        if not self._enabled or not self.rails:
            # Fallback: allow all if guardrails not available
            return True, "Guardrails not available"

        start_time = time.time()

        try:
            # Simple validation: check for obvious issues
            # In production, this would use NeMo Guardrails' full validation
            if not output_text or not output_text.strip():
                reason = "Empty output"
                allowed = False
            else:
                # Basic checks (can be enhanced with full NeMo Guardrails)
                if len(output_text) > 100000:  # Very long output
                    reason = "Output too long"
                    allowed = False
                else:
                    allowed = True
                    reason = "Output validated"

            latency_ms = (time.time() - start_time) * 1000

            # Log decision via callback
            decision = PolicyDecision.create(
                decision_type=DecisionType.GUARDRAILS_OUTPUT,
                result=DecisionResult.ALLOW if allowed else DecisionResult.DENY,
                reason=reason,
                context={
                    "output_length": len(output_text),
                    "output_preview": output_text[:100],
                    **(context or {}),
                },
                latency_ms=latency_ms,
            )

            if self._decision_logger_callback:
                try:
                    result = self._decision_logger_callback(decision)
                    if result and hasattr(result, "__await__"):
                        await result
                except Exception as e:
                    logger.debug(f"Failed to log decision: {e}")

            return allowed, reason

        except Exception as e:
            logger.error(f"Error validating output with NeMo Guardrails: {e}", exc_info=True)
            # On error, allow but log
            return True, f"Validation error: {str(e)}"
