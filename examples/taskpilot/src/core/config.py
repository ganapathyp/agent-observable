"""Configuration management for TaskPilot."""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback if python-dotenv not installed
    def load_dotenv(*args, **kwargs):
        pass

@dataclass
class PathConfig:
    """File and directory path configuration.
    
    All paths can be configured via environment variables.
    Defaults work out-of-the-box for local development.
    """
    # Base directory (project root)
    base_dir: Path
    
    # Data files (relative to base_dir by default)
    tasks_file: Path
    metrics_file: Path
    traces_file: Path
    decision_logs_file: Path
    
    # Logs directory
    logs_dir: Path
    
    # Configuration directories
    prompts_dir: Path
    policies_dir: Path
    guardrails_config_dir: Optional[Path]
    
    # Observability configs
    observability_dir: Path
    
    @classmethod
    def from_env(cls, base_dir: Optional[Path] = None) -> "PathConfig":
        """Create path configuration from environment variables.
        
        Args:
            base_dir: Base directory (defaults to project root)
            
        Returns:
            PathConfig instance
        """
        if base_dir is None:
            # Default to taskpilot project root
            # This file is in src/core/, so go up 2 levels
            base_dir = Path(__file__).parent.parent.parent
        
        base_dir = Path(base_dir).resolve()
        
        # Data files (can be overridden with absolute paths)
        tasks_file = os.getenv("TASKS_FILE")
        if tasks_file:
            tasks_file = Path(tasks_file).resolve()
        else:
            tasks_file = base_dir / ".tasks.json"
        
        metrics_file = os.getenv("METRICS_FILE")
        if metrics_file:
            metrics_file = Path(metrics_file).resolve()
        else:
            metrics_file = base_dir / "metrics.json"
        
        traces_file = os.getenv("TRACES_FILE")
        if traces_file:
            traces_file = Path(traces_file).resolve()
        else:
            traces_file = base_dir / "traces.jsonl"
        
        decision_logs_file = os.getenv("DECISION_LOGS_FILE")
        if decision_logs_file:
            decision_logs_file = Path(decision_logs_file).resolve()
        else:
            decision_logs_file = base_dir / "decision_logs.jsonl"
        
        # Logs directory (supports Docker volume mounting)
        logs_dir = os.getenv("LOGS_DIR")
        if logs_dir:
            logs_dir = Path(logs_dir).resolve()
        else:
            # Try Docker directory first (for Filebeat), fallback to local
            docker_log_dir = os.getenv("DOCKER_LOGS_DIR")
            if docker_log_dir:
                docker_log_dir = Path(docker_log_dir).resolve()
            else:
                # Default Docker log directory (can be overridden)
                docker_log_dir = Path("/var/log/taskpilot")
            
            local_log_dir = base_dir / "logs"
            
            # Use Docker directory if it exists and is writable, otherwise use local
            if docker_log_dir.exists() and os.access(docker_log_dir, os.W_OK):
                logs_dir = docker_log_dir
            else:
                logs_dir = local_log_dir
        
        # Configuration directories
        prompts_dir = os.getenv("PROMPTS_DIR")
        if prompts_dir:
            prompts_dir = Path(prompts_dir).resolve()
        else:
            prompts_dir = base_dir / "prompts"
        
        policies_dir = os.getenv("POLICIES_DIR")
        if policies_dir:
            policies_dir = Path(policies_dir).resolve()
        else:
            policies_dir = base_dir / "policies"
        
        guardrails_config_dir = os.getenv("GUARDRAILS_CONFIG_DIR")
        if guardrails_config_dir:
            guardrails_config_dir = Path(guardrails_config_dir).resolve()
        elif (base_dir / "guardrails" / "config.yml").exists():
            guardrails_config_dir = base_dir / "guardrails"
        else:
            guardrails_config_dir = None
        
        # Observability configs
        observability_dir = os.getenv("OBSERVABILITY_DIR")
        if observability_dir:
            observability_dir = Path(observability_dir).resolve()
        else:
            observability_dir = base_dir / "observability"
        
        return cls(
            base_dir=base_dir,
            tasks_file=tasks_file,
            metrics_file=metrics_file,
            traces_file=traces_file,
            decision_logs_file=decision_logs_file,
            logs_dir=logs_dir,
            prompts_dir=prompts_dir,
            policies_dir=policies_dir,
            guardrails_config_dir=guardrails_config_dir,
            observability_dir=observability_dir
        )
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.policies_dir.mkdir(parents=True, exist_ok=True)
        if self.guardrails_config_dir:
            self.guardrails_config_dir.mkdir(parents=True, exist_ok=True)

@dataclass
class AppConfig:
    """Application runtime configuration."""
    # Server settings
    port: int = 8000
    host: str = "0.0.0.0"
    
    # Observability URLs (for API responses)
    grafana_url: str = "http://localhost:3000"
    prometheus_url: str = "http://localhost:9090"
    jaeger_url: str = "http://localhost:16686"
    kibana_url: str = "http://localhost:5601"
    
    # OpenTelemetry
    otel_enabled: bool = True
    otel_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "taskpilot"
    
    # Workflow settings
    workflow_interval_seconds: int = 60
    
    # Tool execution settings
    tool_timeout_seconds: float = 30.0  # Default 30 seconds for tool execution
    
    # Retry settings
    retry_max_attempts: int = 3
    retry_initial_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    retry_max_delay: float = 60.0
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create app configuration from environment variables."""
        port = int(os.getenv("PORT", "8000"))
        host = os.getenv("HOST", "0.0.0.0")
        
        grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
        prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
        jaeger_url = os.getenv("JAEGER_URL", "http://localhost:16686")
        kibana_url = os.getenv("KIBANA_URL", "http://localhost:5601")
        
        otel_enabled = os.getenv("OTEL_ENABLED", "true").lower() == "true"
        otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        otel_service_name = os.getenv("OTEL_SERVICE_NAME", "taskpilot")
        
        workflow_interval = int(os.getenv("WORKFLOW_INTERVAL_SECONDS", "60"))
        
        tool_timeout = float(os.getenv("TOOL_TIMEOUT_SECONDS", "30.0"))
        
        retry_max_attempts = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
        retry_initial_delay = float(os.getenv("RETRY_INITIAL_DELAY", "1.0"))
        retry_backoff_factor = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))
        retry_max_delay = float(os.getenv("RETRY_MAX_DELAY", "60.0"))
        
        return cls(
            port=port,
            host=host,
            grafana_url=grafana_url,
            prometheus_url=prometheus_url,
            jaeger_url=jaeger_url,
            kibana_url=kibana_url,
            otel_enabled=otel_enabled,
            otel_endpoint=otel_endpoint,
            otel_service_name=otel_service_name,
            workflow_interval_seconds=workflow_interval,
            tool_timeout_seconds=tool_timeout,
            retry_max_attempts=retry_max_attempts,
            retry_initial_delay=retry_initial_delay,
            retry_backoff_factor=retry_backoff_factor,
            retry_max_delay=retry_max_delay,
        )

@dataclass
class Config:
    """Application configuration."""
    # OpenAI settings
    model_id: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    
    # Environment file
    env_file_path: Optional[Path] = None
    
    # Path configuration
    paths: Optional[PathConfig] = None
    
    # App configuration
    app: Optional[AppConfig] = None
    
    @classmethod
    def from_env(cls, base_dir: Optional[Path] = None) -> "Config":
        """Create configuration from environment variables.
        
        Priority:
        1. Environment variables
        2. .env file in taskpilot directory (auto-loaded)
        3. Default values
        
        Args:
            base_dir: Base directory for paths (defaults to project root)
        
        Returns:
            Config instance
            
        Raises:
            ValueError: If required configuration is missing
        """
        # Get taskpilot project root directory (go up from core/ to src/ to taskpilot/)
        if base_dir is None:
            taskpilot_dir = Path(__file__).parent.parent.parent
        else:
            taskpilot_dir = Path(base_dir).resolve()
        
        default_env_file = taskpilot_dir / ".env"
        
        # Auto-load .env file if it exists
        if default_env_file.exists():
            load_dotenv(default_env_file)
        
        # Use .env file path if not set
        env_file_path = os.getenv("ENV_FILE_PATH")
        if env_file_path:
            env_file_path = Path(env_file_path)
            # Load custom .env file if specified
            if env_file_path.exists():
                load_dotenv(env_file_path)
        else:
            env_file_path = default_env_file
        
        # Get model ID from env or use default
        model_id = os.getenv("OPENAI_MODEL_ID", "gpt-4o-mini")
        
        # API key can be in env var or .env file
        api_key = os.getenv("OPENAI_API_KEY")
        
        # Create path and app configs
        paths = PathConfig.from_env(base_dir=taskpilot_dir)
        app = AppConfig.from_env()
        
        config = cls(
            model_id=model_id,
            api_key=api_key,
            env_file_path=env_file_path,
            paths=paths,
            app=app
        )
        
        # Validate configuration
        config.validate()
        
        # Ensure directories exist
        config.paths.ensure_directories()
        
        return config
    
    def validate(self) -> None:
        """Validate configuration.
        
        Raises:
            ValueError: If required configuration is missing
        """
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is required. Set it in .env file or environment variable."
            )
        
        if not self.model_id:
            raise ValueError("Model ID cannot be empty")
        
        # Validate model ID format (basic check)
        if len(self.model_id) < 3:
            raise ValueError(f"Invalid model ID: {self.model_id}")
    
    def get_env_file_path(self) -> str:
        """Get .env file path as string for OpenAIChatClient."""
        if self.env_file_path and self.env_file_path.exists():
            return str(self.env_file_path)
        # Default to taskpilot project root directory
        taskpilot_dir = Path(__file__).parent.parent.parent
        return str(taskpilot_dir / ".env")

# Factory function for creating config
def create_config(env_file_path: Optional[Path] = None, base_dir: Optional[Path] = None) -> Config:
    """Create a new Config instance.
    
    Args:
        env_file_path: Optional path to .env file
        base_dir: Optional base directory for paths
        
    Returns:
        New Config instance
    """
    if env_file_path:
        os.environ["ENV_FILE_PATH"] = str(env_file_path)
    return Config.from_env(base_dir=base_dir)


# Global config instance (singleton pattern)
_config: Optional[Config] = None

def get_config() -> Config:
    """Get the global configuration instance.
    
    Returns:
        Global Config instance
    """
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config

def get_paths() -> PathConfig:
    """Get the global path configuration.
    
    Returns:
        PathConfig instance
    """
    return get_config().paths

def get_app_config() -> AppConfig:
    """Get the global app configuration.
    
    Returns:
        AppConfig instance
    """
    return get_config().app

def set_config(config: Config) -> None:
    """Set the global configuration instance (for testing)."""
    global _config
    _config = config
