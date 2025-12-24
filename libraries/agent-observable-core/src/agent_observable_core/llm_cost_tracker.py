"""LLM cost tracking utilities (framework-agnostic).

Automatically tracks token usage and costs across different frameworks:
- MS Agent Framework
- LangGraph
- OpenAI custom routing

Uses standardized metric names that work across all frameworks.
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from agent_observable_core.framework_detector import get_metric_standardizer
from agent_observable_core.observability import MetricsCollector

logger = logging.getLogger(__name__)

# Model pricing per 1K tokens (USD)
# Source: https://openai.com/pricing (as of 2024)
# Can be extended for other providers (Anthropic, Google, etc.)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o": {
        "input": 2.50,   # $2.50 per 1M tokens = $0.0025 per 1K
        "output": 10.00  # $10.00 per 1M tokens = $0.01 per 1K
    },
    "gpt-4o-mini": {
        "input": 0.15,   # $0.15 per 1M tokens = $0.00015 per 1K
        "output": 0.60   # $0.60 per 1M tokens = $0.0006 per 1K
    },
    "gpt-4-turbo": {
        "input": 10.00,
        "output": 30.00
    },
    "gpt-4": {
        "input": 30.00,
        "output": 60.00
    },
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50
    },
    # Default fallback
    "default": {
        "input": 0.15,
        "output": 0.60
    }
}


def extract_token_usage(response: Any) -> Optional[Dict[str, Any]]:
    """Extract token usage from LLM response (framework-agnostic).
    
    Works with:
    - MS Agent Framework responses
    - LangGraph responses
    - OpenAI direct responses
    - Custom routing responses
    
    Args:
        response: LLM response object (from any framework)
        
    Returns:
        Dict with 'input_tokens', 'output_tokens', 'total_tokens', 'model' or None
    """
    if not response:
        return None
    
    # Try OpenAI-style response.usage
    if hasattr(response, 'usage'):
        usage = response.usage
        model = getattr(response, 'model', 'unknown')
        
        if hasattr(usage, 'prompt_tokens') and hasattr(usage, 'completion_tokens'):
            return {
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "total_tokens": getattr(usage, 'total_tokens', usage.prompt_tokens + usage.completion_tokens),
                "model": model
            }
    
    # Try MS Agent Framework style: agent_run_response.usage
    if hasattr(response, 'agent_run_response'):
        agent_response = response.agent_run_response
        if hasattr(agent_response, 'usage'):
            usage = agent_response.usage
            model = getattr(agent_response, 'model', 'unknown')
            
            if hasattr(usage, 'prompt_tokens') and hasattr(usage, 'completion_tokens'):
                return {
                    "input_tokens": usage.prompt_tokens,
                    "output_tokens": usage.completion_tokens,
                    "total_tokens": getattr(usage, 'total_tokens', usage.prompt_tokens + usage.completion_tokens),
                    "model": model
                }
    
    # Try LangGraph style (if it uses similar structure)
    # LangGraph typically wraps responses, so we check nested structures
    if hasattr(response, 'messages') and hasattr(response, 'response_metadata'):
        metadata = response.response_metadata
        if hasattr(metadata, 'token_usage'):
            usage = metadata.token_usage
            model = getattr(metadata, 'model_name', 'unknown')
            return {
                "input_tokens": getattr(usage, 'prompt_tokens', 0),
                "output_tokens": getattr(usage, 'completion_tokens', 0),
                "total_tokens": getattr(usage, 'total_tokens', 0),
                "model": model
            }
    
    # Try direct attributes (fallback for custom implementations)
    if hasattr(response, 'prompt_tokens') and hasattr(response, 'completion_tokens'):
        return {
            "input_tokens": response.prompt_tokens,
            "output_tokens": response.completion_tokens,
            "total_tokens": getattr(response, 'total_tokens', response.prompt_tokens + response.completion_tokens),
            "model": getattr(response, 'model', 'unknown')
        }
    
    return None


def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculate cost for token usage.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name
        
    Returns:
        Cost in USD
    """
    # Get pricing for model, fallback to default
    pricing = MODEL_PRICING.get(model, MODEL_PRICING.get("default", MODEL_PRICING["gpt-4o-mini"]))
    
    # Calculate cost (pricing is per 1K tokens)
    input_cost = (input_tokens / 1000.0) * pricing["input"]
    output_cost = (output_tokens / 1000.0) * pricing["output"]
    
    total_cost = input_cost + output_cost
    
    return round(total_cost, 6)  # Round to 6 decimal places


def track_llm_metrics(
    response: Any,
    agent_name: str,
    metrics_collector: MetricsCollector,
    service_name: str = "agent-service"
) -> Optional[float]:
    """Track LLM token usage and cost metrics (framework-agnostic).
    
    Uses standardized metric names that work across all frameworks.
    Automatically detects framework and uses appropriate metric names.
    
    Args:
        response: LLM response object (from any framework)
        agent_name: Name of the agent/node/role
        metrics_collector: MetricsCollector instance
        service_name: Service name for metric standardization
        
    Returns:
        Cost in USD if tracked, None otherwise
    """
    usage_info = extract_token_usage(response)
    
    if not usage_info:
        # Token usage not available in response
        logger.debug(f"Token usage not available for {agent_name}")
        return None
    
    input_tokens = usage_info["input_tokens"]
    output_tokens = usage_info["output_tokens"]
    total_tokens = usage_info["total_tokens"]
    model = usage_info["model"]
    
    # Get standardized metric names
    standardizer = get_metric_standardizer(service_name=service_name)
    
    # Track token metrics (per model)
    metrics_collector.increment_counter(
        standardizer.llm_tokens_input_model(model),
        value=input_tokens
    )
    metrics_collector.increment_counter(
        standardizer.llm_tokens_output_model(model),
        value=output_tokens
    )
    metrics_collector.increment_counter(
        standardizer.llm_tokens_total_model(model),
        value=total_tokens
    )
    
    # Track aggregated tokens
    metrics_collector.increment_counter(
        standardizer.llm_tokens_input_total(),
        value=input_tokens
    )
    metrics_collector.increment_counter(
        standardizer.llm_tokens_output_total(),
        value=output_tokens
    )
    metrics_collector.increment_counter(
        standardizer.llm_tokens_total_all(),
        value=total_tokens
    )
    
    # Calculate and track cost
    cost = calculate_cost(input_tokens, output_tokens, model)
    metrics_collector.increment_counter(standardizer.llm_cost_total(), value=cost)
    metrics_collector.increment_counter(
        standardizer.llm_cost_agent(agent_name),
        value=cost
    )
    metrics_collector.increment_counter(
        standardizer.llm_cost_model(model),
        value=cost
    )
    
    logger.debug(
        f"Tracked LLM usage: {agent_name}, model={model}, "
        f"tokens={total_tokens} (in={input_tokens}, out={output_tokens}), cost=${cost:.6f}"
    )
    
    return cost


__all__ = [
    "extract_token_usage",
    "calculate_cost",
    "track_llm_metrics",
    "MODEL_PRICING",
]
