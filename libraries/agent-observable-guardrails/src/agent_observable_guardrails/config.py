"""Configuration for guardrails components."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable

from agent_observable_policy import PolicyDecision

from .nemo_guardrails import NeMoGuardrailsWrapper


@dataclass
class GuardrailsConfig:
    """Configuration for guardrails components."""

    config_path: Optional[Path] = None
    decision_logger_callback: Optional[Callable[[PolicyDecision], Any]] = None  # type: ignore

    @classmethod
    def create(
        cls,
        config_path: Optional[Path] = None,
        decision_logger_callback: Optional[Callable[[PolicyDecision], Any]] = None,  # type: ignore
    ) -> GuardrailsConfig:
        """Create a GuardrailsConfig instance.

        Args:
            config_path: Path to NeMo Guardrails config file
            decision_logger_callback: Optional callback for logging decisions

        Returns:
            GuardrailsConfig instance
        """
        return cls(
            config_path=config_path,
            decision_logger_callback=decision_logger_callback,
        )

    def create_nemo_guardrails(self) -> NeMoGuardrailsWrapper:
        """Create a NeMoGuardrailsWrapper instance from this config.

        Returns:
            NeMoGuardrailsWrapper instance
        """
        return NeMoGuardrailsWrapper(
            config_path=self.config_path,
            decision_logger_callback=self.decision_logger_callback,
        )
