"""Unit tests for LLM cost tracking."""
import pytest
from taskpilot.core.llm_cost_tracker import (
    extract_token_usage,
    calculate_cost,
    track_llm_metrics,
    MODEL_PRICING
)
from taskpilot.core.observability import MetricsCollector


class TestExtractTokenUsage:
    """Test token usage extraction from various response formats."""
    
    def test_extract_token_usage_none(self):
        """Test extraction with None response."""
        assert extract_token_usage(None) is None
    
    def test_extract_token_usage_openai_style(self):
        """Test extraction from OpenAI-style response."""
        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 100
                self.completion_tokens = 50
                self.total_tokens = 150
        
        class MockResponse:
            def __init__(self):
                self.usage = MockUsage()
                self.model = "gpt-4o"
        
        response = MockResponse()
        usage = extract_token_usage(response)
        
        assert usage is not None
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["total_tokens"] == 150
        assert usage["model"] == "gpt-4o"
    
    def test_extract_token_usage_openai_style_no_total(self):
        """Test extraction from OpenAI-style response without total_tokens."""
        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 100
                self.completion_tokens = 50
        
        class MockResponse:
            def __init__(self):
                self.usage = MockUsage()
                self.model = "gpt-4o"
        
        response = MockResponse()
        usage = extract_token_usage(response)
        
        assert usage is not None
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["total_tokens"] == 150  # Calculated
        assert usage["model"] == "gpt-4o"
    
    def test_extract_token_usage_agent_run_response(self):
        """Test extraction from agent_run_response format."""
        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 200
                self.completion_tokens = 100
                self.total_tokens = 300
        
        class MockAgentResponse:
            def __init__(self):
                self.usage = MockUsage()
                self.model = "gpt-4o-mini"
        
        class MockResponse:
            def __init__(self):
                self.agent_run_response = MockAgentResponse()
        
        response = MockResponse()
        usage = extract_token_usage(response)
        
        assert usage is not None
        assert usage["input_tokens"] == 200
        assert usage["output_tokens"] == 100
        assert usage["total_tokens"] == 300
        assert usage["model"] == "gpt-4o-mini"
    
    def test_extract_token_usage_direct_attributes(self):
        """Test extraction from response with direct attributes."""
        class MockResponse:
            def __init__(self):
                self.prompt_tokens = 50
                self.completion_tokens = 25
                self.total_tokens = 75
                self.model = "gpt-3.5-turbo"
        
        response = MockResponse()
        usage = extract_token_usage(response)
        
        assert usage is not None
        assert usage["input_tokens"] == 50
        assert usage["output_tokens"] == 25
        assert usage["total_tokens"] == 75
        assert usage["model"] == "gpt-3.5-turbo"
    
    def test_extract_token_usage_unknown_model(self):
        """Test extraction with unknown model."""
        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 100
                self.completion_tokens = 50
        
        class MockResponse:
            def __init__(self):
                self.usage = MockUsage()
        
        response = MockResponse()
        usage = extract_token_usage(response)
        
        assert usage is not None
        assert usage["model"] == "unknown"
    
    def test_extract_token_usage_no_usage(self):
        """Test extraction from response without usage info."""
        class MockResponse:
            def __init__(self):
                self.model = "gpt-4o"
        
        response = MockResponse()
        usage = extract_token_usage(response)
        
        assert usage is None


class TestCalculateCost:
    """Test cost calculation."""
    
    def test_calculate_cost_gpt4o(self):
        """Test cost calculation for gpt-4o."""
        cost = calculate_cost(input_tokens=1000, output_tokens=500, model="gpt-4o")
        
        # Input: 1000 * 0.0025 = 2.5
        # Output: 500 * 0.01 = 5.0
        # Total: 7.5
        assert abs(cost - 7.5) < 0.0001
    
    def test_calculate_cost_gpt4o_mini(self):
        """Test cost calculation for gpt-4o-mini."""
        cost = calculate_cost(input_tokens=1000, output_tokens=500, model="gpt-4o-mini")
        
        # Input: 1000 * 0.00015 = 0.15
        # Output: 500 * 0.0006 = 0.30
        # Total: 0.45
        assert abs(cost - 0.45) < 0.0001
    
    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown model (uses default)."""
        cost = calculate_cost(input_tokens=1000, output_tokens=500, model="unknown-model")
        
        # Should use default pricing (gpt-4o-mini)
        assert abs(cost - 0.45) < 0.0001
    
    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        cost = calculate_cost(input_tokens=0, output_tokens=0, model="gpt-4o")
        
        assert cost == 0.0
    
    def test_calculate_cost_rounding(self):
        """Test that cost is properly rounded."""
        cost = calculate_cost(input_tokens=1, output_tokens=1, model="gpt-4o")
        
        # Should be rounded to 6 decimal places
        assert isinstance(cost, float)
        assert len(str(cost).split('.')[-1]) <= 6
    
    def test_calculate_cost_all_models(self):
        """Test cost calculation for all supported models."""
        models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
        
        for model in models:
            cost = calculate_cost(input_tokens=1000, output_tokens=500, model=model)
            assert cost > 0
            assert isinstance(cost, float)


class TestTrackLLMMetrics:
    """Test LLM metrics tracking."""
    
    def test_track_llm_metrics_no_usage(self):
        """Test tracking with no usage info."""
        metrics = MetricsCollector(metrics_file=None)
        
        class MockResponse:
            pass
        
        response = MockResponse()
        cost = track_llm_metrics(response, "test_agent", metrics)
        
        assert cost is None
    
    def test_track_llm_metrics_with_usage(self):
        """Test tracking with usage info."""
        metrics = MetricsCollector(metrics_file=None)
        
        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 1000
                self.completion_tokens = 500
                self.total_tokens = 1500
        
        class MockResponse:
            def __init__(self):
                self.usage = MockUsage()
                self.model = "gpt-4o"
        
        response = MockResponse()
        cost = track_llm_metrics(response, "planner", metrics)
        
        assert cost is not None
        assert cost > 0
        
        # Verify metrics were recorded
        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]
        
        assert counters["llm.tokens.input.gpt-4o"] == 1000
        assert counters["llm.tokens.output.gpt-4o"] == 500
        assert counters["llm.tokens.total.gpt-4o"] == 1500
        assert counters["llm.tokens.input.total"] == 1000
        assert counters["llm.tokens.output.total"] == 500
        assert counters["llm.tokens.total.all"] == 1500
        assert counters["llm.cost.total"] == cost
        assert counters["llm.cost.agent.planner"] == cost
        assert counters["llm.cost.model.gpt-4o"] == cost
    
    def test_track_llm_metrics_multiple_calls(self):
        """Test tracking multiple LLM calls."""
        metrics = MetricsCollector(metrics_file=None)
        
        class MockUsage:
            def __init__(self, input_tokens, output_tokens):
                self.prompt_tokens = input_tokens
                self.completion_tokens = output_tokens
                self.total_tokens = input_tokens + output_tokens
        
        class MockResponse:
            def __init__(self, input_tokens, output_tokens, model="gpt-4o"):
                self.usage = MockUsage(input_tokens, output_tokens)
                self.model = model
        
        # First call
        response1 = MockResponse(1000, 500)
        cost1 = track_llm_metrics(response1, "planner", metrics)
        
        # Second call
        response2 = MockResponse(2000, 1000)
        cost2 = track_llm_metrics(response2, "executor", metrics)
        
        # Verify aggregated metrics
        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]
        
        assert counters["llm.tokens.input.total"] == 3000
        assert counters["llm.tokens.output.total"] == 1500
        assert counters["llm.tokens.total.all"] == 4500
        assert counters["llm.cost.total"] == cost1 + cost2
        assert counters["llm.cost.agent.planner"] == cost1
        assert counters["llm.cost.agent.executor"] == cost2
    
    def test_track_llm_metrics_different_models(self):
        """Test tracking with different models."""
        metrics = MetricsCollector(metrics_file=None)
        
        class MockUsage:
            def __init__(self, input_tokens, output_tokens):
                self.prompt_tokens = input_tokens
                self.completion_tokens = output_tokens
                self.total_tokens = input_tokens + output_tokens
        
        class MockResponse:
            def __init__(self, input_tokens, output_tokens, model):
                self.usage = MockUsage(input_tokens, output_tokens)
                self.model = model
        
        # Track with different models
        response1 = MockResponse(1000, 500, "gpt-4o")
        cost1 = track_llm_metrics(response1, "planner", metrics)
        
        response2 = MockResponse(1000, 500, "gpt-4o-mini")
        cost2 = track_llm_metrics(response2, "executor", metrics)
        
        # Verify model-specific metrics
        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]
        
        assert counters["llm.tokens.input.gpt-4o"] == 1000
        assert counters["llm.tokens.input.gpt-4o-mini"] == 1000
        assert counters["llm.cost.model.gpt-4o"] == cost1
        assert counters["llm.cost.model.gpt-4o-mini"] == cost2
        
        # Costs should be different (gpt-4o is more expensive)
        assert cost1 > cost2
