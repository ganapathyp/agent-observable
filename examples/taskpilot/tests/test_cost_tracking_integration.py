"""Integration tests for cost tracking in workflows."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from agent_observable_core.observability import MetricsCollector
from agent_observable_core.llm_cost_tracker import track_llm_metrics


class TestCostTrackingIntegration:
    """Integration tests for cost tracking in workflow context."""
    
    @pytest.fixture
    def metrics(self):
        """Create a fresh metrics collector for each test."""
        return MetricsCollector()
    
    def test_cost_tracking_in_middleware_context(self, metrics):
        """Test that cost tracking works in middleware context."""
        # Simulate agent response with usage
        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 1500
                self.completion_tokens = 800
                self.total_tokens = 2300
        
        class MockAgentResponse:
            def __init__(self):
                self.usage = MockUsage()
                self.model = "gpt-4o-mini"
        
        class MockResult:
            def __init__(self):
                self.agent_run_response = MockAgentResponse()
        
        # Track metrics (as middleware would)
        context_result = MockResult()
        cost = track_llm_metrics(
            context_result,
            agent_name="PlannerAgent",
            metrics_collector=metrics,
            service_name="test"
        )
        
        # Verify cost was tracked
        assert cost is not None
        assert cost > 0
        
        # Verify metrics
        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]
        
        assert counters["llm.cost.total"] == cost
        assert counters["llm.cost.agent.PlannerAgent"] == cost
        assert counters["llm.cost.model.gpt-4o-mini"] == cost
        assert counters["llm.tokens.input.total"] == 1500
        assert counters["llm.tokens.output.total"] == 800
        assert counters["llm.tokens.total.all"] == 2300
    
    def test_cost_tracking_multiple_agents(self, metrics):
        """Test cost tracking across multiple agents in a workflow."""
        # Simulate planner agent
        class MockUsage1:
            def __init__(self):
                self.prompt_tokens = 2000
                self.completion_tokens = 1000
                self.total_tokens = 3000
        
        class MockResult1:
            def __init__(self):
                self.usage = MockUsage1()
                self.model = "gpt-4o"
        
        # Simulate executor agent
        class MockUsage2:
            def __init__(self):
                self.prompt_tokens = 1500
                self.completion_tokens = 500
                self.total_tokens = 2000
        
        class MockResult2:
            def __init__(self):
                self.usage = MockUsage2()
                self.model = "gpt-4o-mini"
        
        # Track planner
        result1 = MockResult1()
        cost1 = track_llm_metrics(result1, "PlannerAgent", metrics, service_name="test")
        
        # Track executor
        result2 = MockResult2()
        cost2 = track_llm_metrics(result2, "ExecutorAgent", metrics, service_name="test")
        
        # Verify aggregated metrics
        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]
        
        assert counters["llm.cost.total"] == cost1 + cost2
        assert counters["llm.cost.agent.PlannerAgent"] == cost1
        assert counters["llm.cost.agent.ExecutorAgent"] == cost2
        assert counters["llm.tokens.input.total"] == 3500
        assert counters["llm.tokens.output.total"] == 1500
        assert counters["llm.tokens.total.all"] == 5000
    
    def test_cost_tracking_accuracy(self, metrics):
        """Test that cost calculation is accurate."""
        # Known pricing: gpt-4o-mini
        # Input: $0.15 per 1M = $0.00015 per 1K
        # Output: $0.60 per 1M = $0.0006 per 1K
        
        class MockUsage:
            def __init__(self, input_tokens, output_tokens):
                self.prompt_tokens = input_tokens
                self.completion_tokens = output_tokens
                self.total_tokens = input_tokens + output_tokens
        
        class MockResult:
            def __init__(self, input_tokens, output_tokens):
                self.usage = MockUsage(input_tokens, output_tokens)
                self.model = "gpt-4o-mini"
        
        # Test with known values
        # 1000 input tokens = 1000/1000 * 0.15 = 0.15
        # 500 output tokens = 500/1000 * 0.60 = 0.30
        # Total = 0.45
        
        result = MockResult(1000, 500)
        cost = track_llm_metrics(result, "TestAgent", metrics, service_name="test")
        
        # Allow small floating point differences
        assert abs(cost - 0.45) < 0.0001
        
        # Verify metrics match
        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]
        assert abs(counters["llm.cost.total"] - 0.45) < 0.0001
    
    def test_cost_tracking_no_usage_handles_gracefully(self, metrics):
        """Test that cost tracking handles responses without usage gracefully."""
        class MockResult:
            pass  # No usage attribute
        
        result = MockResult()
        cost = track_llm_metrics(result, "TestAgent", metrics, service_name="test")
        
        # Should return None, not raise exception
        assert cost is None
        
        # Metrics should not be incremented
        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]
        assert counters.get("llm.cost.total", 0) == 0
    
    def test_cost_metrics_exported_to_prometheus(self, metrics):
        """Test that cost metrics are in the format Prometheus expects."""
        # Track some costs
        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 1000
                self.completion_tokens = 500
                self.total_tokens = 1500
        
        class MockResult:
            def __init__(self):
                self.usage = MockUsage()
                self.model = "gpt-4o-mini"
        
        result = MockResult()
        track_llm_metrics(result, "TestAgent", metrics, service_name="test")
        
        # Get all metrics (as /metrics endpoint would)
        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]
        
        # Verify key metrics exist (will be sanitized for Prometheus)
        assert "llm.cost.total" in counters
        assert "llm.cost.agent.TestAgent" in counters
        assert "llm.cost.model.gpt-4o-mini" in counters
        assert "llm.tokens.input.total" in counters
        assert "llm.tokens.output.total" in counters
        assert "llm.tokens.total.all" in counters
        
        # Verify values are numeric
        assert isinstance(counters["llm.cost.total"], (int, float))
        assert counters["llm.cost.total"] > 0
