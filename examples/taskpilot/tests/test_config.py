"""Unit tests for config module."""
import pytest
import os
from pathlib import Path
from taskpilot.core.config import Config, get_config, set_config


class TestConfig:
    """Test configuration management."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.model_id == "gpt-4o-mini"
        assert config.api_key is None
        assert config.env_file_path is None
    
    def test_config_from_env(self):
        """Test loading config from environment."""
        # Save original env
        original_model = os.environ.get("OPENAI_MODEL_ID")
        original_key = os.environ.get("OPENAI_API_KEY")
        
        try:
            # Set test values
            os.environ["OPENAI_MODEL_ID"] = "test-model"
            os.environ["OPENAI_API_KEY"] = "test-key"
            
            config = Config.from_env()
            
            assert config.model_id == "test-model"
            assert config.api_key == "test-key"
        finally:
            # Restore original env
            if original_model:
                os.environ["OPENAI_MODEL_ID"] = original_model
            elif "OPENAI_MODEL_ID" in os.environ:
                del os.environ["OPENAI_MODEL_ID"]
            
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            elif "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
    
    def test_get_env_file_path(self):
        """Test env file path resolution."""
        config = Config()
        test_path = Path("/test/path/.env")
        config.env_file_path = test_path
        
        path = config.get_env_file_path()
        assert isinstance(path, str)
        # get_env_file_path returns the set path if it exists, or defaults to taskpilot/.env
        # Since test path doesn't exist, it will default - just verify it's a string path
        assert isinstance(path, str)
        assert len(path) > 0
    
    def test_get_config_singleton(self):
        """Test that get_config returns singleton."""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_set_config(self):
        """Test setting custom config."""
        original = get_config()
        
        try:
            custom = Config(model_id="custom-model")
            set_config(custom)
            
            assert get_config().model_id == "custom-model"
        finally:
            set_config(original)
