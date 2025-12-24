"""Unit tests for policy components."""
import pytest
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_observable_policy import (
    DecisionType,
    DecisionResult,
    PolicyDecision,
    DecisionLogger,
    EmbeddedOPA,
    OPAToolValidator,
    PolicyConfig,
)


class TestPolicyDecision:
    """Test PolicyDecision model."""

    def test_create_decision(self):
        """Can create policy decisions."""
        decision = PolicyDecision.create(
            decision_type=DecisionType.TOOL_CALL,
            result=DecisionResult.ALLOW,
            reason="Tool is allowed",
            context={"tool_name": "test_tool"},
        )
        assert decision.decision_type == DecisionType.TOOL_CALL
        assert decision.result == DecisionResult.ALLOW
        assert decision.reason == "Tool is allowed"
        assert decision.decision_id is not None

    def test_to_dict(self):
        """Can convert decision to dictionary."""
        decision = PolicyDecision.create(
            decision_type=DecisionType.TOOL_CALL,
            result=DecisionResult.DENY,
            reason="Tool denied",
            context={},
        )
        data = decision.to_dict()
        assert data["decision_type"] == "tool_call"
        assert data["result"] == "deny"
        assert "timestamp" in data


class TestDecisionLogger:
    """Test DecisionLogger."""

    @pytest.mark.asyncio
    async def test_log_decision(self):
        """Can log decisions."""
        with TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "decisions.jsonl"
            logger = DecisionLogger(log_file=log_file)

            decision = PolicyDecision.create(
                decision_type=DecisionType.TOOL_CALL,
                result=DecisionResult.ALLOW,
                reason="Allowed",
                context={},
            )

            await logger.log_decision(decision)
            await logger.flush()

            assert log_file.exists()
            content = log_file.read_text()
            assert "tool_call" in content
            assert "allow" in content

    @pytest.mark.asyncio
    async def test_batch_flush(self):
        """Decisions are batched and flushed."""
        with TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "decisions.jsonl"
            logger = DecisionLogger(log_file=log_file, batch_size=2)

            # Add 3 decisions (should trigger flush at 2, then one more)
            for i in range(3):
                decision = PolicyDecision.create(
                    decision_type=DecisionType.TOOL_CALL,
                    result=DecisionResult.ALLOW,
                    reason=f"Decision {i}",
                    context={},
                )
                await logger.log_decision(decision)

            # Final flush to ensure all are written
            await logger.flush()

            # Verify all 3 decisions were written
            if log_file.exists():
                content = log_file.read_text().strip()
                if content:
                    lines = content.split("\n")
                    assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"
                else:
                    # If file is empty, decisions might still be in batch
                    # Force one more flush
                    await logger.flush()
                    content = log_file.read_text().strip()
                    lines = content.split("\n") if content else []
                    assert len(lines) == 3, f"Expected 3 lines after second flush, got {len(lines)}"
            else:
                # File doesn't exist yet, flush again
                await logger.flush()
                assert log_file.exists()
                content = log_file.read_text().strip()
                lines = content.split("\n") if content else []
                assert len(lines) == 3


class TestEmbeddedOPA:
    """Test EmbeddedOPA."""

    def test_evaluate_allow(self):
        """Can evaluate policies that allow."""
        opa = EmbeddedOPA()
        result = opa.evaluate(
            "taskpilot.tool_calls",
            {
                "tool_name": "create_task",
                "agent_type": "PlannerAgent",
                "parameters": {"title": "Test", "priority": "low"},
            },
        )
        assert result["allow"] is True
        assert result["require_approval"] is False

    def test_evaluate_deny(self):
        """Can evaluate policies that deny."""
        opa = EmbeddedOPA()
        result = opa.evaluate(
            "taskpilot.tool_calls",
            {
                "tool_name": "delete_task",
                "agent_type": "PlannerAgent",
                "parameters": {},
            },
        )
        assert result["allow"] is False
        assert len(result["deny"]) > 0

    def test_evaluate_require_approval(self):
        """Can evaluate policies that require approval."""
        opa = EmbeddedOPA()
        result = opa.evaluate(
            "taskpilot.tool_calls",
            {
                "tool_name": "create_task",
                "agent_type": "PlannerAgent",
                "parameters": {"title": "Sensitive task", "priority": "high"},
            },
        )
        assert result["allow"] is True
        assert result["require_approval"] is True


class TestOPAToolValidator:
    """Test OPAToolValidator."""

    @pytest.mark.asyncio
    async def test_validate_allowed(self):
        """Can validate allowed tool calls."""
        validator = OPAToolValidator(use_embedded=True)
        allowed, reason, requires_approval = await validator.validate_tool_call(
            tool_name="create_task",
            parameters={"title": "Test", "priority": "low"},
            agent_type="PlannerAgent",
        )
        assert allowed is True
        assert requires_approval is False

    @pytest.mark.asyncio
    async def test_validate_denied(self):
        """Can validate denied tool calls."""
        validator = OPAToolValidator(use_embedded=True)
        allowed, reason, requires_approval = await validator.validate_tool_call(
            tool_name="delete_task",
            parameters={},
            agent_type="PlannerAgent",
        )
        assert allowed is False


class TestPolicyConfig:
    """Test PolicyConfig."""

    def test_create_components(self):
        """Can create components from config."""
        with TemporaryDirectory() as tmpdir:
            config = PolicyConfig(
                decision_log_file=Path(tmpdir) / "decisions.jsonl",
                opa_policy_dir=Path(tmpdir) / "policies",
            )

            logger = config.create_decision_logger()
            assert isinstance(logger, DecisionLogger)

            opa = config.create_embedded_opa()
            assert isinstance(opa, EmbeddedOPA)

            validator = config.create_opa_validator(embedded_opa=opa, decision_logger=logger)
            assert isinstance(validator, OPAToolValidator)
