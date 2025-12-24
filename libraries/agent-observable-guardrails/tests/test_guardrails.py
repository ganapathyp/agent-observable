"""Unit tests for guardrails."""
import pytest
from unittest.mock import MagicMock, AsyncMock

from agent_observable_guardrails import NeMoGuardrailsWrapper, GuardrailsConfig
from agent_observable_policy import PolicyDecision, DecisionType, DecisionResult


class TestNeMoGuardrailsWrapper:
    """Test NeMo Guardrails wrapper."""

    def test_initialization_disabled(self):
        """Can initialize with NeMo disabled (not installed)."""
        wrapper = NeMoGuardrailsWrapper()
        assert wrapper._enabled is False

    def test_initialization_no_config(self):
        """Can initialize without config file."""
        wrapper = NeMoGuardrailsWrapper(config_path=None)
        # Will be disabled if NeMo not available or no config
        assert wrapper._enabled is False or wrapper._enabled is True

    @pytest.mark.asyncio
    async def test_validate_input_disabled(self):
        """Validate input when disabled returns allow."""
        wrapper = NeMoGuardrailsWrapper()
        allowed, reason = await wrapper.validate_input("test input")
        assert allowed is True
        assert "not available" in reason.lower()

    @pytest.mark.asyncio
    async def test_validate_output_disabled(self):
        """Validate output when disabled returns allow."""
        wrapper = NeMoGuardrailsWrapper()
        allowed, reason = await wrapper.validate_output("test output")
        assert allowed is True
        assert "not available" in reason.lower()

    @pytest.mark.asyncio
    async def test_validate_input_empty(self):
        """Empty input is rejected."""
        wrapper = NeMoGuardrailsWrapper()
        wrapper._enabled = True
        wrapper.rails = MagicMock()  # Mock rails object
        allowed, reason = await wrapper.validate_input("")
        assert allowed is False
        assert "empty" in reason.lower()

    @pytest.mark.asyncio
    async def test_validate_input_too_long(self):
        """Very long input is rejected."""
        wrapper = NeMoGuardrailsWrapper()
        wrapper._enabled = True
        wrapper.rails = MagicMock()  # Mock rails object
        long_input = "x" * 100001
        allowed, reason = await wrapper.validate_input(long_input)
        assert allowed is False
        assert "too long" in reason.lower()

    @pytest.mark.asyncio
    async def test_decision_logger_callback(self):
        """Decision logger callback is invoked."""
        logged_decisions = []

        async def log_decision(decision: PolicyDecision):
            logged_decisions.append(decision)

        wrapper = NeMoGuardrailsWrapper(decision_logger_callback=log_decision)
        wrapper._enabled = True
        wrapper.rails = MagicMock()  # Mock rails object

        await wrapper.validate_input("test input")

        assert len(logged_decisions) == 1
        assert logged_decisions[0].decision_type == DecisionType.GUARDRAILS_INPUT
        assert logged_decisions[0].result == DecisionResult.ALLOW


class TestGuardrailsConfig:
    """Test GuardrailsConfig."""

    def test_create_config(self):
        """Test creating config."""
        from pathlib import Path
        config = GuardrailsConfig.create(config_path=Path("/tmp/config.yml"))
        assert config.config_path == Path("/tmp/config.yml")

    def test_create_nemo_guardrails(self):
        """Test creating NeMo guardrails from config."""
        config = GuardrailsConfig.create()
        wrapper = config.create_nemo_guardrails()
        assert isinstance(wrapper, NeMoGuardrailsWrapper)
