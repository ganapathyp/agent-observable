from agent_framework.openai import OpenAIChatClient  # type: ignore
from taskpilot.core.config import get_config  # type: ignore
from taskpilot.core.prompt_loader import load_prompt  # type: ignore

def create_executor():
    """Create the executor agent.
    
    The executor receives approved task proposals and prepares them for execution.
    The workflow handles actual tool execution via FunctionExecutor, so the executor
    should just output the task information in a format that can be parsed.
    """
    config = get_config()
    return OpenAIChatClient(
        model_id=config.model_id,
        env_file_path=config.get_env_file_path()
    ).create_agent(
        name="ExecutorAgent",
        instructions=load_prompt("ExecutorAgent")  # Load from prompts/executor.yaml
    )
