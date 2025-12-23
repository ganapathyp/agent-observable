"""Unit tests for Golden Signals calculation."""
import pytest
from taskpilot.core.observability import MetricsCollector


class TestGoldenSignals:
    """Test Golden Signals calculation."""
    
    def test_golden_signals_empty_metrics(self):
        """Test Golden Signals with no metrics (all zeros)."""
        metrics = MetricsCollector(metrics_file=None)  # In-memory only
        
        signals = metrics.get_golden_signals()
        
        assert signals["success_rate"] == 0.0
        assert signals["p95_latency_ms"] == 0.0
        assert signals["cost_per_successful_task_usd"] == 0.0
        assert signals["user_confirmed_correctness_percent"] is None
        assert signals["policy_violation_rate_percent"] == 0.0
        assert signals["metadata"]["workflow_runs"] == 0
        assert signals["metadata"]["workflow_success"] == 0
        assert signals["metadata"]["total_cost_usd"] == 0.0
        assert signals["metadata"]["total_violations"] == 0
    
    def test_golden_signals_success_rate(self):
        """Test success rate calculation."""
        metrics = MetricsCollector(metrics_file=None)
        
        # Set up metrics
        metrics.increment_counter("workflow.runs", value=100)
        metrics.increment_counter("workflow.success", value=95)
        
        signals = metrics.get_golden_signals()
        
        assert signals["success_rate"] == 95.0
        assert signals["metadata"]["workflow_runs"] == 100
        assert signals["metadata"]["workflow_success"] == 95
    
    def test_golden_signals_p95_latency(self):
        """Test p95 latency calculation."""
        metrics = MetricsCollector(metrics_file=None)
        
        # Record latency samples
        for i in range(100):
            metrics.record_histogram("workflow.latency_ms", float(i * 10))
        
        signals = metrics.get_golden_signals()
        
        # p95 should be around 95th value (950ms)
        assert signals["p95_latency_ms"] > 900
        assert signals["p95_latency_ms"] < 1000
    
    def test_golden_signals_cost_per_successful_task(self):
        """Test cost per successful task calculation."""
        metrics = MetricsCollector(metrics_file=None)
        
        # Set up metrics
        metrics.increment_counter("workflow.runs", value=10)
        metrics.increment_counter("workflow.success", value=8)
        metrics.increment_counter("llm.cost.total", value=0.50)
        
        signals = metrics.get_golden_signals()
        
        # Cost per successful task = 0.50 / 8 = 0.0625
        assert signals["cost_per_successful_task_usd"] == 0.0625
        assert signals["metadata"]["total_cost_usd"] == 0.50
    
    def test_golden_signals_user_confirmed_correctness(self):
        """Test user-confirmed correctness calculation."""
        metrics = MetricsCollector(metrics_file=None)
        
        # Set up metrics
        metrics.increment_counter("llm.quality.user_confirmed_correct", value=80)
        metrics.increment_counter("llm.quality.user_confirmed_incorrect", value=20)
        
        signals = metrics.get_golden_signals()
        
        # Correctness = 80 / 100 * 100 = 80%
        assert signals["user_confirmed_correctness_percent"] == 80.0
        assert signals["metadata"]["total_feedback"] == 100
    
    def test_golden_signals_user_confirmed_correctness_no_feedback(self):
        """Test user-confirmed correctness with no feedback."""
        metrics = MetricsCollector(metrics_file=None)
        
        signals = metrics.get_golden_signals()
        
        assert signals["user_confirmed_correctness_percent"] is None
        assert signals["metadata"]["total_feedback"] is None
    
    def test_golden_signals_policy_violation_rate(self):
        """Test policy violation rate calculation."""
        metrics = MetricsCollector(metrics_file=None)
        
        # Set up metrics
        metrics.increment_counter("workflow.runs", value=100)
        metrics.increment_counter("agent.planner.policy.violations", value=2)
        metrics.increment_counter("agent.executor.policy.violations", value=1)
        metrics.increment_counter("policy.violations.total", value=1)
        
        signals = metrics.get_golden_signals()
        
        # Total violations = 2 + 1 + 1 = 4
        # Violation rate = 4 / 100 * 100 = 4%
        assert signals["policy_violation_rate_percent"] == 4.0
        assert signals["metadata"]["total_violations"] == 4
    
    def test_golden_signals_all_signals(self):
        """Test all Golden Signals together."""
        metrics = MetricsCollector(metrics_file=None)
        
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
        assert signals["p95_latency_ms"] > 900
        assert abs(signals["cost_per_successful_task_usd"] - 0.0556) < 0.01  # 5.0 / 90
        assert signals["user_confirmed_correctness_percent"] == 94.44  # 85 / 90 * 100
        assert signals["policy_violation_rate_percent"] == 2.0
        
        # Verify metadata
        assert signals["metadata"]["workflow_runs"] == 100
        assert signals["metadata"]["workflow_success"] == 90
        assert signals["metadata"]["total_cost_usd"] == 5.0
        assert signals["metadata"]["total_violations"] == 2
        assert signals["metadata"]["total_feedback"] == 90
    
    def test_golden_signals_zero_workflow_runs(self):
        """Test Golden Signals with zero workflow runs."""
        metrics = MetricsCollector(metrics_file=None)
        
        # Set up metrics but no workflow runs
        metrics.increment_counter("llm.cost.total", value=10.0)
        
        signals = metrics.get_golden_signals()
        
        # Should handle division by zero gracefully
        assert signals["success_rate"] == 0.0
        assert signals["cost_per_successful_task_usd"] == 0.0
        assert signals["policy_violation_rate_percent"] == 0.0
    
    def test_golden_signals_zero_successful_tasks(self):
        """Test Golden Signals with zero successful tasks."""
        metrics = MetricsCollector(metrics_file=None)
        
        # Set up metrics with runs but no success
        metrics.increment_counter("workflow.runs", value=10)
        metrics.increment_counter("workflow.success", value=0)
        metrics.increment_counter("llm.cost.total", value=5.0)
        
        signals = metrics.get_golden_signals()
        
        # Should handle division by zero gracefully
        assert signals["success_rate"] == 0.0
        assert signals["cost_per_successful_task_usd"] == 0.0
    
    def test_golden_signals_rounding(self):
        """Test that Golden Signals are properly rounded."""
        metrics = MetricsCollector(metrics_file=None)
        
        # Set up metrics that will produce non-integer results
        metrics.increment_counter("workflow.runs", value=3)
        metrics.increment_counter("workflow.success", value=1)
        metrics.increment_counter("llm.cost.total", value=0.123456)
        
        signals = metrics.get_golden_signals()
        
        # Verify rounding
        assert signals["success_rate"] == 33.33  # 1/3 * 100 = 33.333...
        assert signals["cost_per_successful_task_usd"] == 0.1235  # Rounded to 4 decimals
        assert isinstance(signals["success_rate"], float)
        assert isinstance(signals["cost_per_successful_task_usd"], float)
