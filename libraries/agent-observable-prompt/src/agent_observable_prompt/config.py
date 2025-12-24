"""Configuration for prompt management."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict

from .prompt_manager import PromptManager


@dataclass
class PromptConfig:
    """Configuration for prompt management components."""

    prompts_dir: Optional[Path] = None
    default_prompts: Optional[Dict[str, str]] = None

    @classmethod
    def create(
        cls,
        prompts_dir: Optional[Path] = None,
        default_prompts: Optional[Dict[str, str]] = None,
    ) -> PromptConfig:
        """Create a PromptConfig instance.

        Args:
            prompts_dir: Directory containing prompt YAML files
            default_prompts: Dictionary of default prompts

        Returns:
            PromptConfig instance
        """
        return cls(prompts_dir=prompts_dir, default_prompts=default_prompts)

    def create_prompt_manager(self) -> PromptManager:
        """Create a PromptManager instance from this config.

        Returns:
            PromptManager instance
        """
        return PromptManager(
            prompts_dir=self.prompts_dir,
            default_prompts=self.default_prompts,
        )
