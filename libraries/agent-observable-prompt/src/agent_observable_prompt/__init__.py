"""agent-observable-prompt: prompt management for agent systems."""

from .prompt_manager import PromptManager, PromptInfo
from .config import PromptConfig

__all__ = [
    "PromptManager",
    "PromptInfo",
    "PromptConfig",
]
