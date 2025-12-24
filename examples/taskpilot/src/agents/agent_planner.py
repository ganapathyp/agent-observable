"""Planner agent using function calling for structured output.

This is the production-ready approach using OpenAI's native structured output
features. The agent uses function calling with strict schema enforcement,
guaranteeing valid JSON output without requiring parsing strategies.
"""
from agent_framework.openai import OpenAIChatClient  # type: ignore
from taskpilot.core.config import get_config  # type: ignore
from taskpilot.core.models import TaskInfo  # type: ignore
from taskpilot.core.observable import load_prompt  # type: ignore
from taskpilot.tools import create_task  # type: ignore

def create_planner():
    """Create the planner agent using function calling for structured output.
    
    This uses OpenAI's native structured output features:
    - Function calling with strict schema enforcement
    - Guaranteed valid JSON output
    - Schema validated at LLM level
    - No parsing strategies needed (direct extraction)
    
    Returns:
        Agent configured for structured output via function calling
    """
    config = get_config()
    
    # Get JSON schema from Pydantic model
    task_schema = TaskInfo.get_json_schema()
    
    # Create agent with function calling
    client = OpenAIChatClient(
        model_id=config.model_id,
        env_file_path=config.get_env_file_path()
    )
    
    # Load prompt from external YAML file (falls back to default if not found)
    instructions = load_prompt("PlannerAgent")
    
    # Create agent with function calling for structured output
    # Pass the @ai_function decorated function - it will auto-generate schema
    # But we need to ensure strict mode, so we'll configure it manually
    # The function implementation is automatically registered via @ai_function
    agent = client.create_agent(
        name="PlannerAgent",
        instructions=instructions,
        tools=[create_task]  # @ai_function handles registration
    )
    
    # Override the tool schema to use strict mode with our custom schema
    # This ensures we get the exact schema we want (with description required)
    if hasattr(agent, 'tools') and agent.tools:
        for tool in agent.tools:
            if hasattr(tool, 'function') and tool.function.name == "create_task":
                tool.function.parameters = task_schema
                tool.function.strict = True
                break
    
    return agent
