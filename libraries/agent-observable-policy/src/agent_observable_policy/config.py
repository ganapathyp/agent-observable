"""Configuration for policy components."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .decision_logger import DecisionLogger
from .opa_embedded import EmbeddedOPA
from .opa_validator import OPAToolValidator


@dataclass
class PolicyConfig:
    """Configuration for policy components."""

    # Decision logger settings
    decision_log_file: Optional[Path] = None
    decision_log_db_url: Optional[str] = None
    decision_log_batch_size: int = 100
    decision_log_flush_interval: float = 5.0

    # OPA settings
    opa_policy_dir: Optional[Path] = None
    opa_url: Optional[str] = None
    opa_use_embedded: bool = True
    opa_package: str = "taskpilot.tool_calls"

    def create_decision_logger(
        self, metrics_callback: Optional[callable] = None
    ) -> DecisionLogger:
        """Create a DecisionLogger with this configuration."""
        return DecisionLogger(
            log_file=self.decision_log_file,
            db_url=self.decision_log_db_url,
            batch_size=self.decision_log_batch_size,
            flush_interval=self.decision_log_flush_interval,
            metrics_callback=metrics_callback,
        )

    def create_embedded_opa(self) -> EmbeddedOPA:
        """Create an EmbeddedOPA with this configuration."""
        return EmbeddedOPA(policy_dir=self.opa_policy_dir)

    def create_opa_validator(
        self,
        embedded_opa: Optional[EmbeddedOPA] = None,
        decision_logger: Optional[DecisionLogger] = None,
    ) -> OPAToolValidator:
        """Create an OPAToolValidator with this configuration."""
        return OPAToolValidator(
            opa_url=self.opa_url,
            use_embedded=self.opa_use_embedded,
            embedded_opa=embedded_opa or self.create_embedded_opa(),
            decision_logger=decision_logger,
            package=self.opa_package,
        )
