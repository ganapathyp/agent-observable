"""Tests for guardrails functionality."""
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from taskpilot.core.guardrails.decision_log import (  # type: ignore
    DecisionType,
    DecisionResult,
    PolicyDecision,
)
from taskpilot.core.guardrails.decision_logger import (  # type: ignore
    DecisionLogger,
    set_decision_logger,
)
from taskpilot.core.guardrails.opa_tool_validator import OPAToolValidator  # type: ignore
from taskpilot.core.guardrails.nemo_rails import NeMoGuardrailsWrapper  # type: ignore


class TestPolicyDecision:
    """Tests for PolicyDecision."""

    def test_create_decision(self):
        """Test creating a policy decision."""
        decision = PolicyDecision.create(
            decision_type=DecisionType.TOOL_CALL,
            result=DecisionResult.ALLOW,
            reason="Test reason",
            context={"tool": "test"},
        )
        
        assert decision.decision_type == DecisionType.TOOL_CALL
        assert decision.result == DecisionResult.ALLOW
        assert decision.reason == "Test reason"
        assert decision.context == {"tool": "test"}
        assert decision.decision_id is not None
        assert isinstance(decision.timestamp, datetime)

    def test_to_dict(self):
        """Test converting decision to dictionary."""
        decision = PolicyDecision.create(
            decision_type=DecisionType.GUARDRAILS_INPUT,
            result=DecisionResult.DENY,
            reason="Blocked",
            context={"input": "test"},
        )
        
        data = decision.to_dict()
        assert data["decision_type"] == "guardrails_input"
        assert data["result"] == "deny"
        assert data["reason"] == "Blocked"
        assert "timestamp" in data


class TestDecisionLogger:
    """Tests for DecisionLogger."""

    @pytest.mark.asyncio
    async def test_log_decision(self):
        """Test logging a decision."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "decisions.jsonl"
            logger = DecisionLogger(log_file=log_file)
            
            decision = PolicyDecision.create(
                decision_type=DecisionType.TOOL_CALL,
                result=DecisionResult.ALLOW,
                reason="Test",
                context={},
            )
            
            await logger.log_decision(decision)
            await logger.flush()
            
            assert log_file.exists()
            with open(log_file) as f:
                lines = f.readlines()
                assert len(lines) == 1
                data = json.loads(lines[0])
                assert data["decision_type"] == "tool_call"
                assert data["result"] == "allow"

    @pytest.mark.asyncio
    async def test_batch_flush(self):
        """Test batching and flushing decisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "decisions.jsonl"
            logger = DecisionLogger(log_file=log_file, batch_size=2)
            
            # Add 3 decisions (should trigger flush at 2)
            for i in range(3):
                decision = PolicyDecision.create(
                    decision_type=DecisionType.TOOL_CALL,
                    result=DecisionResult.ALLOW,
                    reason=f"Test {i}",
                    context={},
                )
                await logger.log_decision(decision)
            
            # Flush remaining
            await logger.flush()
            
            with open(log_file) as f:
                lines = f.readlines()
                assert len(lines) == 3


class TestOPAToolValidator:
    """Tests for OPA tool validator."""

    @pytest.mark.asyncio
    async def test_validate_tool_call_no_opa(self):
        """Test validation when OPA is not available."""
        validator = OPAToolValidator(opa_url="http://localhost:9999")
        
        # Should allow when OPA is unavailable
        allowed, reason, requires_approval = await validator.validate_tool_call(
            tool_name="create_task",
            parameters={"title": "Test", "priority": "high"},
            agent_type="PlannerAgent",
        )
        
        assert allowed is True
        assert "unavailable" in reason.lower() or "not available" in reason.lower()
        assert requires_approval is False

    @pytest.mark.asyncio
    async def test_validate_tool_call_with_mock_opa(self):
        """Test validation with mocked OPA response."""
        validator = OPAToolValidator(opa_url="http://localhost:8181")
        
        with patch("taskpilot.core.guardrails.opa_tool_validator.requests") as mock_requests:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "result": {
                    "allow": True,
                    "deny": [],
                    "require_approval": False,
                }
            }
            mock_requests.post.return_value = mock_response
            
            allowed, reason, requires_approval = await validator.validate_tool_call(
                tool_name="create_task",
                parameters={"title": "Test", "priority": "high"},
                agent_type="PlannerAgent",
            )
            
            assert allowed is True
            assert requires_approval is False


class TestNeMoGuardrailsWrapper:
    """Tests for NeMo Guardrails wrapper."""

    @pytest.mark.asyncio
    async def test_validate_input(self):
        """Test input validation."""
        wrapper = NeMoGuardrailsWrapper()
        
        allowed, reason = await wrapper.validate_input("Test input")
        
        # Should allow if guardrails not available
        assert isinstance(allowed, bool)
        assert isinstance(reason, str)

    @pytest.mark.asyncio
    async def test_validate_output(self):
        """Test output validation."""
        wrapper = NeMoGuardrailsWrapper()
        
        allowed, reason = await wrapper.validate_output("Test output")
        
        # Should allow if guardrails not available
        assert isinstance(allowed, bool)
        assert isinstance(reason, str)

    @pytest.mark.asyncio
    async def test_validate_empty_input(self):
        """Test validation of empty input."""
        wrapper = NeMoGuardrailsWrapper()
        
        allowed, reason = await wrapper.validate_input("")
        
        # Empty input should be blocked
        assert allowed is False
        assert "empty" in reason.lower()

    @pytest.mark.asyncio
    async def test_validate_empty_output(self):
        """Test validation of empty output."""
        wrapper = NeMoGuardrailsWrapper()
        
        allowed, reason = await wrapper.validate_output("")
        
        # Empty output should be blocked
        assert allowed is False
        assert "empty" in reason.lower()
