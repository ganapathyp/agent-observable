"""Unit tests for prompt management."""
import pytest
import tempfile
from pathlib import Path
import yaml

from agent_observable_prompt import PromptManager, PromptInfo, PromptConfig


class TestPromptManager:
    """Test PromptManager."""

    def test_normalize_agent_name(self):
        """Test agent name normalization."""
        manager = PromptManager()
        assert manager.normalize_agent_name("PlannerAgent") == "planner"
        assert manager.normalize_agent_name("planner") == "planner"
        assert manager.normalize_agent_name("ReviewerAgent") == "reviewer"

    def test_load_default_prompt(self):
        """Test loading default prompt."""
        default_prompts = {
            "planner": "Test planner prompt",
            "reviewer": "Test reviewer prompt",
        }
        manager = PromptManager(default_prompts=default_prompts)

        prompt = manager.load_prompt("PlannerAgent")
        assert prompt == "Test planner prompt"

        prompt = manager.load_prompt("reviewer")
        assert prompt == "Test reviewer prompt"  # Will use default

    def test_load_prompt_from_file(self):
        """Test loading prompt from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir)
            prompt_file = prompts_dir / "planner.yaml"

            prompt_data = {
                "version": "1.0",
                "system_instruction": "Test prompt from file",
                "metadata": {"author": "test"},
            }

            with open(prompt_file, "w") as f:
                yaml.dump(prompt_data, f)

            manager = PromptManager(prompts_dir=prompts_dir)
            prompt = manager.load_prompt("PlannerAgent")

            assert prompt == "Test prompt from file"

    def test_get_prompt_info(self):
        """Test getting prompt info."""
        default_prompts = {"planner": "Test prompt"}
        manager = PromptManager(default_prompts=default_prompts)

        info = manager.get_prompt_info("PlannerAgent")
        assert isinstance(info, PromptInfo)
        assert info.source == "default"
        assert info.prompt == "Test prompt"
        assert info.version == "default"

    def test_get_prompt_info_from_file(self):
        """Test getting prompt info from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir)
            prompt_file = prompts_dir / "planner.yaml"

            prompt_data = {
                "version": "1.0",
                "system_instruction": "Test prompt",
                "metadata": {"author": "test"},
            }

            with open(prompt_file, "w") as f:
                yaml.dump(prompt_data, f)

            manager = PromptManager(prompts_dir=prompts_dir)
            info = manager.get_prompt_info("PlannerAgent")

            assert info.source == "file"
            assert info.version == "1.0"
            assert info.prompt == "Test prompt"
            assert info.metadata == {"author": "test"}

    def test_versioning_support(self):
        """Test prompt versioning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir)
            prompt_file = prompts_dir / "planner.yaml"

            prompt_data = {
                "version": "1.0",
                "system_instruction": "Default prompt",
                "versions": {
                    "1.0": {
                        "system_instruction": "Version 1.0 prompt",
                        "metadata": {"author": "v1"},
                    },
                    "1.1": {
                        "system_instruction": "Version 1.1 prompt",
                        "metadata": {"author": "v1.1"},
                    },
                },
            }

            with open(prompt_file, "w") as f:
                yaml.dump(prompt_data, f)

            manager = PromptManager(prompts_dir=prompts_dir)

            # Load default version
            prompt = manager.load_prompt("PlannerAgent")
            assert prompt == "Default prompt"

            # Load specific version
            prompt = manager.load_prompt("PlannerAgent", version="1.1")
            assert prompt == "Version 1.1 prompt"

            info = manager.get_prompt_info("PlannerAgent", version="1.1")
            assert info.version == "1.1"
            assert info.metadata == {"author": "v1.1"}

    def test_list_available_versions(self):
        """Test listing available versions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir)
            prompt_file = prompts_dir / "planner.yaml"

            prompt_data = {
                "version": "1.0",
                "versions": {
                    "1.0": {"system_instruction": "v1.0"},
                    "1.1": {"system_instruction": "v1.1"},
                },
            }

            with open(prompt_file, "w") as f:
                yaml.dump(prompt_data, f)

            manager = PromptManager(prompts_dir=prompts_dir)
            versions = manager.list_available_versions("PlannerAgent")

            assert "1.0" in versions
            assert "1.1" in versions

    def test_cache_clearing(self):
        """Test cache clearing."""
        manager = PromptManager(default_prompts={"planner": "Test"})
        manager.load_prompt("PlannerAgent")
        assert len(manager._prompts_cache) > 0

        manager.clear_cache()
        assert len(manager._prompts_cache) == 0


class TestPromptConfig:
    """Test PromptConfig."""

    def test_create_config(self):
        """Test creating config."""
        config = PromptConfig.create(
            prompts_dir=Path("/tmp/prompts"),
            default_prompts={"planner": "Test"},
        )

        assert config.prompts_dir == Path("/tmp/prompts")
        assert config.default_prompts == {"planner": "Test"}

    def test_create_prompt_manager(self):
        """Test creating prompt manager from config."""
        default_prompts = {"planner": "Test prompt"}
        config = PromptConfig.create(default_prompts=default_prompts)

        manager = config.create_prompt_manager()
        assert isinstance(manager, PromptManager)
        assert manager.default_prompts == default_prompts
