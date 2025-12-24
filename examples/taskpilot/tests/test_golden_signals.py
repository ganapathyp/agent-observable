"""Unit tests for Golden Signals calculation."""
import pytest
from agent_observable_core.observability import MetricsCollector


class TestGoldenSignals:
    """Test Golden Signals calculation."""
    
    def test_golden_signals_empty_metrics(self):
        """Test Golden Signals with no metrics (all zeros)."""
        metrics = MetricsCollector()  # In-memory only
        
        signals = metrics.get_golden_signals()
        
        assert signals["success_rate"] == 100.0  # Default when no runs
        assert signals["p95_latency"] == 0.0
        assert signals["cost_per_successful_task"] == 0.0
        assert signals["user_confirmed_correctness"] == 0.0  # Returns 0.0 when no feedback
        assert signals["policy_violation_rate"] == 0.0
    
    def test_golden_signals_success_rate(self):
        """Test success rate calculation."""
        metrics = MetricsCollector()
        
        # Set up metrics
        metrics.increment_counter("workflow.runs", value=100)
        metrics.increment_counter("workflow.success", value=95)
        
        signals = metrics.get_golden_signals()
        
        assert signals["success_rate"] == 95.0
        # Note: get_golden_signals doesn't return metadata anymore
    
    def test_golden_signals_p95_latency(self):
        """Test p95 latency calculation."""
        metrics = MetricsCollector()
        
        # Record latency samples
        for i in range(100):
            metrics.record_histogram("workflow.latency_ms", float(i * 10))
        
        signals = metrics.get_golden_signals()
        
        # p95 should be around 95th value (950ms)
        assert signals["p95_latency"] > 900
        assert signals["p95_latency"] < 1000
    
    def test_golden_signals_cost_per_successful_task(self):
        """Test cost per successful task calculation."""
        metrics = MetricsCollector()
        
        # Set up metrics
        metrics.increment_counter("workflow.runs", value=10)
        metrics.increment_counter("workflow.success", value=8)
        metrics.increment_counter("llm.cost.total", value=0.50)
        
        signals = metrics.get_golden_signals()
        
        # Cost per successful task = 0.50 / 8 = 0.0625
        assert signals["cost_per_successful_task"] == 0.0625
    
    def test_golden_signals_user_confirmed_correctness(self):
        """Test user-confirmed correctness calculation."""
        metrics = MetricsCollector()
        
        # Set up metrics
        metrics.increment_counter("llm.quality.user_confirmed_correct", value=80)
        metrics.increment_counter("llm.quality.user_confirmed_incorrect", value=20)
        
        signals = metrics.get_golden_signals()
        
        # Correctness = 80 / 100 * 100 = 80%
        assert signals["user_confirmed_correctness"] == 80.0
    
    def test_golden_signals_user_confirmed_correctness_no_feedback(self):
        """Test user-confirmed correctness with no feedback."""
        metrics = MetricsCollector()
        
        signals = metrics.get_golden_signals()
        
        assert signals["user_confirmed_correctness"] == 0.0  # Returns 0.0 when no feedback
    
    def test_golden_signals_policy_violation_rate(self):
        """Test policy violation rate calculation."""
        metrics = MetricsCollector()
        
        # Set up metrics
        metrics.increment_counter("workflow.runs", value=100)
        metrics.increment_counter("agent.planner.policy.violations", value=2)
        metrics.increment_counter("agent.executor.policy.violations", value=1)
        metrics.increment_counter("policy.violations.total", value=1)
        
        signals = metrics.get_golden_signals()
        
        # Violation rate = 1 / 100 * 100 = 1% (only policy.violations.total is used)
        assert signals["policy_violation_rate"] == 1.0
    
    def test_golden_signals_all_signals(self):
        """Test all Golden Signals together."""
        metrics = MetricsCollector()
        
        # Set up comprehensive metrics
        metrics.increment_counter("workflow.runs", value=100)
        metrics.increment_counter("workflow.success", value=90)
        metrics.increment_counter("llm.cost.total", value=5.0)
        metrics.increment_counter("llm.quality.user_confirmed_correct", value=85)
        metrics.increment_counter("llm.quality.user_confirmed_incorrect", value=5)
        metrics.increment_counter("policy.violations.total", value=2)
        
        # Record latency samples
        for i in range(100):
            metrics.record_histogram("workflow.latency_ms", float(i * 10))
        
        signals = metrics.get_golden_signals()
        
        # Verify all signals
        assert signals["success_rate"] == 90.0
        assert signals["p95_latency"] > 900
        assert abs(signals["cost_per_successful_task"] - 0.0556) < 0.01  # 5.0 / 90
        assert abs(signals["user_confirmed_correctness"] - 94.44) < 0.1  # 85 / 90 * 100
        assert signals["policy_violation_rate"] == 2.0
    
    def test_golden_signals_zero_workflow_runs(self):
        """Test Golden Signals with zero workflow runs."""
        metrics = MetricsCollector()
        
        # Set up metrics but no workflow runs
        metrics.increment_counter("llm.cost.total", value=10.0)
        
        signals = metrics.get_golden_signals()
        
        # Should handle division by zero gracefully
        assert signals["success_rate"] == 100.0  # Default when no runs
        assert signals["cost_per_successful_task"] == 0.0
        assert signals["policy_violation_rate"] == 0.0
    
    def test_golden_signals_zero_successful_tasks(self):
        """Test Golden Signals with zero successful tasks."""
        metrics = MetricsCollector()
        
        # Set up metrics with runs but no success
        metrics.increment_counter("workflow.runs", value=10)
        metrics.increment_counter("workflow.success", value=0)
        metrics.increment_counter("llm.cost.total", value=5.0)
        
        signals = metrics.get_golden_signals()
        
        # Should handle division by zero gracefully
        assert signals["success_rate"] == 0.0
        assert signals["cost_per_successful_task"] == 0.0
    
    def test_golden_signals_rounding(self):
        """Test that Golden Signals are properly rounded."""
        metrics = MetricsCollector()
        
        # Set up metrics that will produce non-integer results
        metrics.increment_counter("workflow.runs", value=3)
        metrics.increment_counter("workflow.success", value=1)
        metrics.increment_counter("llm.cost.total", value=0.123456)
        
        signals = metrics.get_golden_signals()
        
        # Verify rounding
        assert signals["success_rate"] == 33.33  # 1/3 * 100 = 33.333...
        assert signals["cost_per_successful_task"] == 0.1235  # Rounded to 4 decimals
        assert isinstance(signals["success_rate"], float)
        assert isinstance(signals["cost_per_successful_task"], float)
