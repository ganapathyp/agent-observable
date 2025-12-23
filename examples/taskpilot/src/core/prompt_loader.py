"""Prompt loader for external prompt files."""
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Default prompts (fallback if files don't exist)
DEFAULT_PROMPTS = {
    "planner": """Interpret the user request and propose a task.

Use the create_task function to return structured task information.

Focus on:
- Creating clear, actionable task titles
- Assigning appropriate priority based on urgency and importance
- Providing detailed descriptions when helpful""",
    
    "reviewer": """Review the proposed task for safety and compliance. 
Reply with exactly one of: APPROVE, REJECTED, or REVIEW.

- APPROVE: Task is safe and can proceed automatically
- REJECTED: Task is unsafe and should be rejected
- REVIEW: Task requires human review (use only for ambiguous cases, <5% of tasks)""",
    
    "executor": """You receive approved task proposals. Your role is to prepare the task 
for execution by outputting the task details clearly. 
The workflow system will handle the actual execution. 
Simply describe the task that needs to be executed."""
}


def load_prompt(agent_name: str, prompts_dir: Optional[Path] = None) -> str:
    """Load prompt for an agent.
    
    Args:
        agent_name: Agent name (e.g., "PlannerAgent", "planner")
        prompts_dir: Optional directory containing prompt files (defaults to prompts/)
        
    Returns:
        Prompt string (from file or default)
    """
    # Normalize agent name
    agent_key = agent_name.lower().replace("agent", "").strip()
    
    # Determine prompts directory
    if prompts_dir is None:
        # Default: taskpilot/prompts/
        taskpilot_dir = Path(__file__).parent.parent.parent
        prompts_dir = taskpilot_dir / "prompts"
    
    # Try to load from YAML file
    prompt_file = prompts_dir / f"{agent_key}.yaml"
    
    if prompt_file.exists():
        try:
            import yaml
            with open(prompt_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                prompt = data.get('system_instruction') or data.get('prompt') or data.get('instruction')
                if prompt:
                    logger.debug(f"Loaded prompt from {prompt_file}")
                    return prompt.strip()
        except ImportError:
            logger.warning("PyYAML not installed, using default prompts")
        except Exception as e:
            logger.warning(f"Failed to load prompt from {prompt_file}: {e}, using default")
    
    # Fallback to default prompts
    default_prompt = DEFAULT_PROMPTS.get(agent_key)
    if default_prompt:
        logger.debug(f"Using default prompt for {agent_name}")
        return default_prompt
    
    # Last resort: return empty string
    logger.warning(f"No prompt found for {agent_name}, using empty prompt")
    return ""


def get_prompt_info(agent_name: str, prompts_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Get prompt metadata.
    
    Args:
        agent_name: Agent name
        prompts_dir: Optional prompts directory
        
    Returns:
        Dict with prompt info (version, metadata, etc.)
    """
    agent_key = agent_name.lower().replace("agent", "").strip()
    
    if prompts_dir is None:
        # Use configured path from PathConfig
        try:
            from taskpilot.core.config import get_paths
            paths = get_paths()
            prompts_dir = paths.prompts_dir
        except Exception:
            # Fallback to old behavior if config not available
            taskpilot_dir = Path(__file__).parent.parent.parent
            prompts_dir = taskpilot_dir / "prompts"
    
    prompt_file = prompts_dir / f"{agent_key}.yaml"
    
    if prompt_file.exists():
        try:
            import yaml
            with open(prompt_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return {
                    "source": "file",
                    "file": str(prompt_file),
                    "version": data.get("version", "unknown"),
                    "metadata": data.get("metadata", {}),
                    "prompt": data.get("system_instruction") or data.get("prompt", "")
                }
        except Exception as e:
            logger.warning(f"Failed to load prompt info: {e}")
    
    return {
        "source": "default",
        "file": None,
        "version": "default",
        "metadata": {},
        "prompt": DEFAULT_PROMPTS.get(agent_key, "")
    }
