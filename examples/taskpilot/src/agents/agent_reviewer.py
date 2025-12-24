from agent_framework.openai import OpenAIChatClient  # type: ignore
from taskpilot.core.config import get_config  # type: ignore
from taskpilot.core.observable import load_prompt  # type: ignore

def create_reviewer():
    """Create the reviewer agent.
    
    The reviewer can return:
    - APPROVE: Task is safe and can proceed automatically
    - REJECTED: Task is unsafe and should be rejected
    - REVIEW: Task requires human review (use sparingly, <5% of cases)
    """
    config = get_config()
    return OpenAIChatClient(
        model_id=config.model_id,
        env_file_path=config.get_env_file_path()
    ).create_agent(
        name="ReviewerAgent",
        instructions=load_prompt("ReviewerAgent")  # Load from prompts/reviewer.yaml
    )
