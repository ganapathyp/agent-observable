"""Prompt manager for loading and managing prompts."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class PromptInfo:
    """Information about a loaded prompt."""

    source: str  # "file" or "default"
    file: Optional[str] = None
    version: str = "unknown"
    metadata: Dict[str, Any] = None  # type: ignore
    prompt: str = ""

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


class PromptManager:
    """Centralized prompt management with versioning support."""

    def __init__(
        self,
        prompts_dir: Optional[Path] = None,
        default_prompts: Optional[Dict[str, str]] = None,
    ):
        """Initialize prompt manager.

        Args:
            prompts_dir: Directory containing prompt YAML files
            default_prompts: Dictionary of default prompts (agent_key -> prompt)
        """
        self.prompts_dir = prompts_dir
        self.default_prompts = default_prompts or {}
        self._prompts_cache: Dict[str, PromptInfo] = {}

    def normalize_agent_name(self, agent_name: str) -> str:
        """Normalize agent name to key format.

        Args:
            agent_name: Agent name (e.g., "PlannerAgent", "planner")

        Returns:
            Normalized key (e.g., "planner")
        """
        return agent_name.lower().replace("agent", "").strip()

    def load_prompt(
        self,
        agent_name: str,
        version: Optional[str] = None,
        prompts_dir: Optional[Path] = None,
    ) -> str:
        """Load prompt for an agent.

        Args:
            agent_name: Agent name (e.g., "PlannerAgent", "planner")
            version: Optional version to load (defaults to latest)
            prompts_dir: Optional directory override

        Returns:
            Prompt string
        """
        info = self.get_prompt_info(agent_name, version, prompts_dir)
        return info.prompt

    def get_prompt_info(
        self,
        agent_name: str,
        version: Optional[str] = None,
        prompts_dir: Optional[Path] = None,
    ) -> PromptInfo:
        """Get prompt information including metadata.

        Args:
            agent_name: Agent name
            version: Optional version to load
            prompts_dir: Optional directory override

        Returns:
            PromptInfo with prompt and metadata
        """
        agent_key = self.normalize_agent_name(agent_name)
        cache_key = f"{agent_key}:{version or 'latest'}"

        # Check cache
        if cache_key in self._prompts_cache:
            return self._prompts_cache[cache_key]

        # Determine prompts directory
        search_dir = prompts_dir or self.prompts_dir
        if search_dir is None:
            # No directory provided, use default prompts only
            prompt_text = self.default_prompts.get(agent_key, "")
            info = PromptInfo(
                source="default",
                file=None,
                version="default",
                metadata={},
                prompt=prompt_text,
            )
            self._prompts_cache[cache_key] = info
            return info

        # Try to load from YAML file
        prompt_file = search_dir / f"{agent_key}.yaml"

        if prompt_file.exists():
            try:
                if not YAML_AVAILABLE:
                    logger.warning("PyYAML not installed, using default prompts")
                    prompt_text = self.default_prompts.get(agent_key, "")
                    info = PromptInfo(
                        source="default",
                        file=None,
                        version="default",
                        metadata={},
                        prompt=prompt_text,
                    )
                    self._prompts_cache[cache_key] = info
                    return info

                with open(prompt_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                # Handle versioning
                if version and "versions" in data:
                    # Load specific version
                    versions = data.get("versions", {})
                    if version in versions:
                        version_data = versions[version]
                        prompt_text = (
                            version_data.get("system_instruction")
                            or version_data.get("prompt")
                            or version_data.get("instruction")
                            or ""
                        )
                        metadata = version_data.get("metadata", {})
                        info = PromptInfo(
                            source="file",
                            file=str(prompt_file),
                            version=version,
                            metadata=metadata,
                            prompt=prompt_text.strip(),
                        )
                        self._prompts_cache[cache_key] = info
                        return info

                # Load default/current version
                prompt_text = (
                    data.get("system_instruction")
                    or data.get("prompt")
                    or data.get("instruction")
                    or ""
                )
                file_version = data.get("version", "unknown")
                metadata = data.get("metadata", {})

                logger.debug(f"Loaded prompt from {prompt_file} (version: {file_version})")

                info = PromptInfo(
                    source="file",
                    file=str(prompt_file),
                    version=file_version,
                    metadata=metadata,
                    prompt=prompt_text.strip(),
                )
                self._prompts_cache[cache_key] = info
                return info

            except Exception as e:
                logger.warning(f"Failed to load prompt from {prompt_file}: {e}, using default")

        # Fallback to default prompts
        prompt_text = self.default_prompts.get(agent_key, "")
        if prompt_text:
            logger.debug(f"Using default prompt for {agent_name}")
            info = PromptInfo(
                source="default",
                file=None,
                version="default",
                metadata={},
                prompt=prompt_text,
            )
            self._prompts_cache[cache_key] = info
            return info

        # Last resort: return empty string
        logger.warning(f"No prompt found for {agent_name}, using empty prompt")
        info = PromptInfo(
            source="default",
            file=None,
            version="unknown",
            metadata={},
            prompt="",
        )
        self._prompts_cache[cache_key] = info
        return info

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._prompts_cache.clear()

    def list_available_versions(self, agent_name: str) -> list[str]:
        """List available versions for an agent.

        Args:
            agent_name: Agent name

        Returns:
            List of available version strings
        """
        agent_key = self.normalize_agent_name(agent_name)
        prompt_file = (self.prompts_dir or Path()) / f"{agent_key}.yaml"

        if not prompt_file.exists() or not YAML_AVAILABLE:
            return ["default"]

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            versions = []
            if "version" in data:
                versions.append(data["version"])
            if "versions" in data:
                versions.extend(data["versions"].keys())

            return list(set(versions)) if versions else ["default"]
        except Exception as e:
            logger.warning(f"Failed to list versions for {agent_name}: {e}")
            return ["default"]
