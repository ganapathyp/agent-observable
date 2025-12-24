"""Cost tracking viewer and reporting utilities."""
from __future__ import annotations

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta

from agent_observable_core.observability import MetricsCollector
from agent_observable_core.framework_detector import get_metric_standardizer


class CostViewer:
    """View and analyze LLM cost metrics."""
    
    def __init__(self, metrics_collector: MetricsCollector, service_name: str = "taskpilot"):
        self.metrics = metrics_collector
        self.standardizer = get_metric_standardizer(service_name=service_name)
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get comprehensive cost summary.
        
        Returns:
            Dict with total cost, cost by agent, cost by model, token usage
        """
        all_metrics = self.metrics.get_all_metrics()
        counters = all_metrics.get("counters", {})
        
        # Get cost metrics
        total_cost = counters.get(self.standardizer.llm_cost_total(), 0.0)
        
        # Get cost by agent (find all llm.cost.agent.* metrics)
        cost_by_agent: Dict[str, float] = {}
        agent_prefix = "llm.cost.agent."
        for key, value in counters.items():
            if key.startswith(agent_prefix):
                agent_name = key[len(agent_prefix):]
                cost_by_agent[agent_name] = value
        
        # Get cost by model (find all llm.cost.model.* metrics)
        cost_by_model: Dict[str, float] = {}
        model_prefix = "llm.cost.model."
        for key, value in counters.items():
            if key.startswith(model_prefix):
                model_name = key[len(model_prefix):]
                cost_by_model[model_name] = value
        
        # Get token metrics
        input_tokens_total = counters.get(self.standardizer.llm_tokens_input_total(), 0.0)
        output_tokens_total = counters.get(self.standardizer.llm_tokens_output_total(), 0.0)
        tokens_total_all = counters.get(self.standardizer.llm_tokens_total_all(), 0.0)
        
        # Get tokens by model
        tokens_by_model: Dict[str, Dict[str, float]] = {}
        input_prefix = "llm.tokens.input."
        output_prefix = "llm.tokens.output."
        total_prefix = "llm.tokens.total."
        
        # Find all models (from input tokens)
        models = set()
        for key in counters.keys():
            if key.startswith(input_prefix) and not key.endswith(".total"):
                model = key[len(input_prefix):]
                models.add(model)
        
        for model in models:
            input_key = f"{input_prefix}{model}"
            output_key = f"{output_prefix}{model}"
            total_key = f"{total_prefix}{model}"
            
            tokens_by_model[model] = {
                "input": counters.get(input_key, 0.0),
                "output": counters.get(output_key, 0.0),
                "total": counters.get(total_key, 0.0),
            }
        
        return {
            "total_cost_usd": total_cost,
            "cost_by_agent": cost_by_agent,
            "cost_by_model": cost_by_model,
            "tokens": {
                "input_total": input_tokens_total,
                "output_total": output_tokens_total,
                "total_all": tokens_total_all,
            },
            "tokens_by_model": tokens_by_model,
        }
    
    def get_cost_report(self, format: str = "text") -> str:
        """Get formatted cost report.
        
        Args:
            format: Output format ('text', 'json', 'csv')
            
        Returns:
            Formatted report string
        """
        summary = self.get_cost_summary()
        
        if format == "json":
            return json.dumps(summary, indent=2)
        
        if format == "csv":
            lines = ["Metric,Value"]
            lines.append(f"Total Cost (USD),{summary['total_cost_usd']}")
            for agent, cost in summary['cost_by_agent'].items():
                lines.append(f"Cost by Agent ({agent}),{cost}")
            for model, cost in summary['cost_by_model'].items():
                lines.append(f"Cost by Model ({model}),{cost}")
            return "\n".join(lines)
        
        # Text format
        lines = []
        lines.append("=" * 80)
        lines.append("LLM Cost Report")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append("")
        
        lines.append(f"Total Cost: ${summary['total_cost_usd']:.6f} USD")
        lines.append("")
        
        if summary['cost_by_agent']:
            lines.append("Cost by Agent:")
            for agent, cost in sorted(summary['cost_by_agent'].items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / summary['total_cost_usd'] * 100) if summary['total_cost_usd'] > 0 else 0
                lines.append(f"  {agent}: ${cost:.6f} ({percentage:.1f}%)")
            lines.append("")
        
        if summary['cost_by_model']:
            lines.append("Cost by Model:")
            for model, cost in sorted(summary['cost_by_model'].items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / summary['total_cost_usd'] * 100) if summary['total_cost_usd'] > 0 else 0
                lines.append(f"  {model}: ${cost:.6f} ({percentage:.1f}%)")
            lines.append("")
        
        lines.append("Token Usage:")
        lines.append(f"  Input Tokens: {summary['tokens']['input_total']:,.0f}")
        lines.append(f"  Output Tokens: {summary['tokens']['output_total']:,.0f}")
        lines.append(f"  Total Tokens: {summary['tokens']['total_all']:,.0f}")
        lines.append("")
        
        if summary['tokens_by_model']:
            lines.append("Tokens by Model:")
            for model, tokens in sorted(summary['tokens_by_model'].items()):
                lines.append(f"  {model}:")
                lines.append(f"    Input: {tokens['input']:,.0f}")
                lines.append(f"    Output: {tokens['output']:,.0f}")
                lines.append(f"    Total: {tokens['total']:,.0f}")
            lines.append("")
        
        if summary['total_cost_usd'] > 0 and summary['tokens']['total_all'] > 0:
            cost_per_1k_tokens = (summary['total_cost_usd'] / summary['tokens']['total_all']) * 1000
            lines.append(f"Average Cost per 1K Tokens: ${cost_per_1k_tokens:.6f}")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)


def create_cost_viewer(metrics_collector: Optional[MetricsCollector] = None, service_name: str = "taskpilot") -> CostViewer:
    """Create a CostViewer instance.
    
    Args:
        metrics_collector: MetricsCollector instance (if None, gets from observability)
        service_name: Service name for metric standardization
        
    Returns:
        CostViewer instance
    """
    if metrics_collector is None:
        from taskpilot.core.observable import get_metrics
        metrics_collector = get_metrics()
    
    return CostViewer(metrics_collector, service_name=service_name)


__all__ = ["CostViewer", "create_cost_viewer"]
