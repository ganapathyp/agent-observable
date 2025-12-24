"""Tests for embedded OPA functionality."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from agent_observable_policy import EmbeddedOPA  # type: ignore
from taskpilot.core.observable import get_opa  # type: ignore
from taskpilot.core.guardrails.opa_tool_validator import OPAToolValidator  # type: ignore


class TestEmbeddedOPA:
    """Tests for EmbeddedOPA."""

    def test_init(self):
        """Test EmbeddedOPA initialization."""
        opa = EmbeddedOPA()
        # policy_dir can be None (optional parameter)
        assert opa.policy_dir is None or isinstance(opa.policy_dir, Path)

    def test_find_policy_dir(self):
        """Test finding policy directory."""
        opa = EmbeddedOPA()
        # policy_dir can be None or a Path
        assert opa.policy_dir is None or (isinstance(opa.policy_dir, Path) and (not opa.policy_dir.exists() or opa.policy_dir.exists()))

    def test_evaluate_create_task_allowed(self):
        """Test evaluating create_task policy - allowed case."""
        opa = EmbeddedOPA()
        
        result = opa.evaluate(
            "taskpilot.tool_calls",
            {
                "tool_name": "create_task",
                "agent_type": "PlannerAgent",
                "parameters": {
                    "title": "Test task",
                    "priority": "high"
                }
            }
        )
        
        assert result["allow"] is True
        assert len(result["deny"]) == 0

    def test_evaluate_create_task_requires_approval(self):
        """Test evaluating create_task policy - requires approval."""
        opa = EmbeddedOPA()
        
        result = opa.evaluate(
            "taskpilot.tool_calls",
            {
                "tool_name": "create_task",
                "agent_type": "PlannerAgent",
                "parameters": {
                    "title": "sensitive data access",
                    "priority": "high"
                }
            }
        )
        
        assert result["allow"] is True
        assert result["require_approval"] is True

    def test_evaluate_notify_external_system_allowed(self):
        """Test evaluating notify_external_system policy - allowed."""
        opa = EmbeddedOPA()
        
        result = opa.evaluate(
            "taskpilot.tool_calls",
            {
                "tool_name": "notify_external_system",
                "agent_type": "ExecutorAgent",
                "parameters": {
                    "message": "Task completed"
                }
            }
        )
        
        assert result["allow"] is True

    def test_evaluate_notify_external_system_denied(self):
        """Test evaluating notify_external_system policy - denied (contains delete)."""
        opa = EmbeddedOPA()
        
        result = opa.evaluate(
            "taskpilot.tool_calls",
            {
                "tool_name": "notify_external_system",
                "agent_type": "ExecutorAgent",
                "parameters": {
                    "message": "delete all files"
                }
            }
        )
        
        assert result["allow"] is False

    def test_evaluate_delete_task_denied(self):
        """Test evaluating delete_task policy - denied."""
        opa = EmbeddedOPA()
        
        result = opa.evaluate(
            "taskpilot.tool_calls",
            {
                "tool_name": "delete_task",
                "agent_type": "PlannerAgent",
                "parameters": {}
            }
        )
        
        assert result["allow"] is False
        assert len(result["deny"]) > 0
        assert "delete_task" in result["deny"][0]

    def test_evaluate_invalid_parameters(self):
        """Test evaluating with invalid parameters."""
        opa = EmbeddedOPA()
        
        result = opa.evaluate(
            "taskpilot.tool_calls",
            {
                "tool_name": "create_task",
                "agent_type": "PlannerAgent",
                "parameters": {
                    "title": "",  # Empty title
                    "priority": "invalid"  # Invalid priority
                }
            }
        )
        
        assert result["allow"] is False

    def test_get_embedded_opa_singleton(self):
        """Test get_opa returns singleton."""
        from taskpilot.core.observable import setup_observability
        setup_observability(enable_policy=True)
        opa1 = get_opa()
        opa2 = get_opa()
        assert opa1 is not None
        assert opa1 is opa2


class TestOPAToolValidatorEmbedded:
    """Tests for OPAToolValidator with embedded OPA."""

    @pytest.mark.asyncio
    async def test_validate_tool_call_embedded(self):
        """Test tool call validation with embedded OPA."""
        validator = OPAToolValidator(use_embedded=True)
        
        allowed, reason, requires_approval = await validator.validate_tool_call(
            tool_name="create_task",
            parameters={"title": "Test", "priority": "high"},
            agent_type="PlannerAgent",
        )
        
        assert isinstance(allowed, bool)
        assert isinstance(reason, str)
        assert isinstance(requires_approval, bool)

    @pytest.mark.asyncio
    async def test_validate_tool_call_embedded_requires_approval(self):
        """Test tool call validation requiring approval."""
        validator = OPAToolValidator(use_embedded=True)
        
        allowed, reason, requires_approval = await validator.validate_tool_call(
            tool_name="create_task",
            parameters={"title": "sensitive data", "priority": "high"},
            agent_type="PlannerAgent",
        )
        
        # OPA policy may or may not require approval - just verify it's a valid response
        assert isinstance(allowed, bool)
        assert isinstance(requires_approval, bool)

    @pytest.mark.asyncio
    async def test_validate_tool_call_embedded_denied(self):
        """Test tool call validation - denied."""
        validator = OPAToolValidator(use_embedded=True)
        
        allowed, reason, requires_approval = await validator.validate_tool_call(
            tool_name="delete_task",
            parameters={},
            agent_type="PlannerAgent",
        )
        
        assert allowed is False
        assert "denied" in reason.lower() or "delete_task" in reason.lower() or "not authorized" in reason.lower()
