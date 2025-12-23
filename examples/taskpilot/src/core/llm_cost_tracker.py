"""LLM cost tracking utilities."""
from taskpilot.core.metric_names import (  # type: ignore
    LLM_COST_TOTAL,
    llm_cost_agent,
    llm_cost_model,
    LLM_TOKENS_INPUT_TOTAL,
    LLM_TOKENS_OUTPUT_TOTAL,
    LLM_TOKENS_TOTAL_ALL,
    llm_tokens_input_model,
    llm_tokens_output_model,
    llm_tokens_total_model
)
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Model pricing per 1K tokens (USD)
# Source: https://openai.com/pricing (as of 2024)
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
    """Extract token usage from LLM response.
    
    Args:
        response: LLM response object (from agent framework or OpenAI)
        
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
    
    # Try agent_run_response.usage
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
    
    # Try direct attributes
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
    metrics_collector: Any
) -> Optional[float]:
    """Track LLM token usage and cost metrics.
    
    Args:
        response: LLM response object
        agent_name: Name of the agent
        metrics_collector: MetricsCollector instance
        
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
    
    # Track token metrics
    metrics_collector.increment_counter(f"llm.tokens.input.{model}", value=input_tokens)
    metrics_collector.increment_counter(f"llm.tokens.output.{model}", value=output_tokens)
    metrics_collector.increment_counter(f"llm.tokens.total.{model}", value=total_tokens)
    
    # Track aggregated tokens
    metrics_collector.increment_counter("llm.tokens.input.total", value=input_tokens)
    metrics_collector.increment_counter("llm.tokens.output.total", value=output_tokens)
    metrics_collector.increment_counter("llm.tokens.total.all", value=total_tokens)
    
    # Calculate and track cost
    cost = calculate_cost(input_tokens, output_tokens, model)
    metrics_collector.increment_counter("llm.cost.total", value=cost)
    metrics_collector.increment_counter(f"llm.cost.agent.{agent_name}", value=cost)
    metrics_collector.increment_counter(f"llm.cost.model.{model}", value=cost)
    
    logger.debug(
        f"Tracked LLM usage: {agent_name}, model={model}, "
        f"tokens={total_tokens} (in={input_tokens}, out={output_tokens}), cost=${cost:.6f}"
    )
    
    return cost
