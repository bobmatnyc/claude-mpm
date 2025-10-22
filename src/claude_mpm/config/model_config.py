"""
Model Configuration Management for Claude MPM Framework
=======================================================

WHY: Centralizes configuration for model providers, routing strategy, and
model selection. Supports configuration files, environment variables, and
programmatic configuration.

DESIGN DECISION: Uses Pydantic for configuration validation and type safety.
Supports loading from YAML files and environment variables with sensible defaults.

CONFIGURATION STRUCTURE:
```yaml
content_agent:
  model_provider: auto  # auto|ollama|claude|privacy

  ollama:
    enabled: true
    host: http://localhost:11434
    fallback_to_cloud: true
    timeout: 30
    models:
      seo_analysis: llama3.3:70b
      readability: gemma2:9b
      grammar: qwen3:14b
      summarization: mistral:7b
      keyword_extraction: seoassistant

  claude:
    enabled: true
    model: claude-3-5-sonnet-20241022
    max_tokens: 4096
    temperature: 0.7
```

ENVIRONMENT VARIABLES:
- MODEL_PROVIDER: Override provider strategy
- OLLAMA_HOST: Override Ollama endpoint
- OLLAMA_ENABLED: Enable/disable Ollama
- CLAUDE_ENABLED: Enable/disable Claude
- ANTHROPIC_API_KEY: Claude API key
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


class OllamaConfig(BaseModel):
    """
    Configuration for Ollama provider.

    WHY: Separates Ollama-specific settings for better organization
    and validation.
    """

    enabled: bool = Field(default=True, description="Enable Ollama provider")
    host: str = Field(
        default="http://localhost:11434",
        description="Ollama API endpoint",
    )
    fallback_to_cloud: bool = Field(
        default=True,
        description="Allow fallback to cloud on Ollama failure",
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
    models: Dict[str, str] = Field(
        default_factory=dict,
        description="Task-specific model mappings",
    )

    class Config:
        """Pydantic config."""

        extra = "allow"


class ClaudeConfig(BaseModel):
    """
    Configuration for Claude provider.

    WHY: Separates Claude-specific settings for better organization
    and validation.
    """

    enabled: bool = Field(default=True, description="Enable Claude provider")
    model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Default Claude model",
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum response tokens",
    )
    temperature: float = Field(
        default=0.7,
        description="Sampling temperature (0.0-1.0)",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key (can use env var)",
    )

    class Config:
        """Pydantic config."""

        extra = "allow"


class ModelProviderConfig(BaseModel):
    """
    Main model provider configuration.

    WHY: Top-level configuration containing all model-related settings.
    Validates configuration at load time to catch errors early.
    """

    provider: str = Field(
        default="auto",
        description="Provider strategy: auto|ollama|claude|privacy",
    )
    ollama: OllamaConfig = Field(
        default_factory=OllamaConfig,
        description="Ollama provider configuration",
    )
    claude: ClaudeConfig = Field(
        default_factory=ClaudeConfig,
        description="Claude provider configuration",
    )

    class Config:
        """Pydantic config."""

        extra = "allow"


class ModelConfigManager:
    """
    Manager for model configuration.

    WHY: Provides centralized configuration loading with support for
    multiple sources (files, env vars, defaults) and validation.

    Usage:
        manager = ModelConfigManager()
        config = manager.load_config()

        # Get router config
        router_config = manager.get_router_config(config)

        # Get provider configs
        ollama_config = manager.get_ollama_config(config)
        claude_config = manager.get_claude_config(config)
    """

    DEFAULT_CONFIG_PATHS = [
        ".claude/configuration.yaml",
        "configuration.yaml",
        ".claude-mpm/configuration.yaml",
        str(Path("~/.claude-mpm/configuration.yaml").expanduser()),
    ]

    @staticmethod
    def load_config(
        config_path: Optional[str] = None,
    ) -> ModelProviderConfig:
        """
        Load model configuration from file and environment.

        WHY: Supports multiple configuration sources with priority:
        1. Explicit config_path parameter
        2. Environment variables
        3. Configuration file
        4. Default values

        Args:
            config_path: Optional path to configuration file

        Returns:
            ModelProviderConfig with merged settings
        """
        config_data: Dict[str, Any] = {}

        # Try to load from file
        if config_path and Path(config_path).exists():
            config_data = ModelConfigManager._load_yaml_file(config_path)
        else:
            # Try default paths
            for default_path in ModelConfigManager.DEFAULT_CONFIG_PATHS:
                if Path(default_path).exists():
                    config_data = ModelConfigManager._load_yaml_file(default_path)
                    break

        # Extract content_agent section if present
        if "content_agent" in config_data:
            config_data = config_data["content_agent"]

        # Override with environment variables
        config_data = ModelConfigManager._apply_env_overrides(config_data)

        # Create and validate config
        try:
            return ModelProviderConfig(**config_data)
        except Exception as e:
            # If validation fails, return default config
            print(f"Warning: Failed to load config: {e}. Using defaults.")
            return ModelProviderConfig()

    @staticmethod
    def _load_yaml_file(path: str) -> Dict[str, Any]:
        """
        Load YAML configuration file.

        Args:
            path: Path to YAML file

        Returns:
            Dictionary of configuration
        """
        if yaml is None:
            return {}

        try:
            path_obj = Path(path)
            with path_obj.open() as f:
                data = yaml.safe_load(f)
                return data or {}
        except Exception as e:
            print(f"Warning: Failed to load {path}: {e}")
            return {}

    @staticmethod
    def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides.

        WHY: Allows runtime configuration without modifying files.
        Useful for containerized deployments and CI/CD.

        Args:
            config: Base configuration

        Returns:
            Configuration with env overrides applied
        """
        # Provider strategy
        if "MODEL_PROVIDER" in os.environ:
            config["provider"] = os.environ["MODEL_PROVIDER"]

        # Ollama settings
        if "ollama" not in config:
            config["ollama"] = {}

        if "OLLAMA_ENABLED" in os.environ:
            config["ollama"]["enabled"] = os.environ["OLLAMA_ENABLED"].lower() == "true"

        if "OLLAMA_HOST" in os.environ:
            config["ollama"]["host"] = os.environ["OLLAMA_HOST"]

        if "OLLAMA_TIMEOUT" in os.environ:
            try:
                config["ollama"]["timeout"] = int(os.environ["OLLAMA_TIMEOUT"])
            except ValueError:
                pass

        if "OLLAMA_FALLBACK_TO_CLOUD" in os.environ:
            config["ollama"]["fallback_to_cloud"] = (
                os.environ["OLLAMA_FALLBACK_TO_CLOUD"].lower() == "true"
            )

        # Claude settings
        if "claude" not in config:
            config["claude"] = {}

        if "CLAUDE_ENABLED" in os.environ:
            config["claude"]["enabled"] = os.environ["CLAUDE_ENABLED"].lower() == "true"

        if "ANTHROPIC_API_KEY" in os.environ:
            config["claude"]["api_key"] = os.environ["ANTHROPIC_API_KEY"]

        if "CLAUDE_MODEL" in os.environ:
            config["claude"]["model"] = os.environ["CLAUDE_MODEL"]

        if "CLAUDE_MAX_TOKENS" in os.environ:
            try:
                config["claude"]["max_tokens"] = int(os.environ["CLAUDE_MAX_TOKENS"])
            except ValueError:
                pass

        if "CLAUDE_TEMPERATURE" in os.environ:
            try:
                config["claude"]["temperature"] = float(
                    os.environ["CLAUDE_TEMPERATURE"]
                )
            except ValueError:
                pass

        return config

    @staticmethod
    def get_router_config(config: ModelProviderConfig) -> Dict[str, Any]:
        """
        Get router configuration from model config.

        Args:
            config: Model provider configuration

        Returns:
            Dictionary suitable for ModelRouter initialization
        """
        return {
            "strategy": config.provider,
            "fallback_enabled": config.ollama.fallback_to_cloud,
            "ollama_config": ModelConfigManager.get_ollama_config(config),
            "claude_config": ModelConfigManager.get_claude_config(config),
        }

    @staticmethod
    def get_ollama_config(config: ModelProviderConfig) -> Dict[str, Any]:
        """
        Get Ollama provider configuration.

        Args:
            config: Model provider configuration

        Returns:
            Dictionary suitable for OllamaProvider initialization
        """
        return {
            "host": config.ollama.host,
            "timeout": config.ollama.timeout,
            "models": config.ollama.models,
        }

    @staticmethod
    def get_claude_config(config: ModelProviderConfig) -> Dict[str, Any]:
        """
        Get Claude provider configuration.

        Args:
            config: Model provider configuration

        Returns:
            Dictionary suitable for ClaudeProvider initialization
        """
        return {
            "api_key": config.claude.api_key,
            "model": config.claude.model,
            "max_tokens": config.claude.max_tokens,
            "temperature": config.claude.temperature,
        }

    @staticmethod
    def create_sample_config(output_path: str) -> None:
        """
        Create sample configuration file.

        WHY: Helps users get started with proper configuration.

        Args:
            output_path: Path where to write sample config
        """
        sample_config = """# Claude MPM Model Provider Configuration
# ==========================================

content_agent:
  # Provider strategy: auto|ollama|claude|privacy
  # - auto: Try Ollama first, fallback to Claude
  # - ollama: Local-only, fail if unavailable
  # - claude: Cloud-only, always use Claude
  # - privacy: Like ollama but with privacy-focused error messages
  model_provider: auto

  # Ollama Configuration (local models)
  ollama:
    enabled: true
    host: http://localhost:11434
    fallback_to_cloud: true  # Allow fallback to Claude on error
    timeout: 30  # Request timeout in seconds

    # Task-specific model mappings (optional)
    # Defaults are provided if not specified
    models:
      seo_analysis: llama3.3:70b
      readability: gemma2:9b
      grammar: qwen3:14b
      summarization: mistral:7b
      keyword_extraction: seoassistant
      accessibility: gemma2:9b
      sentiment: gemma2:9b
      general: gemma2:9b

  # Claude Configuration (cloud models)
  claude:
    enabled: true
    model: claude-3-5-sonnet-20241022
    max_tokens: 4096
    temperature: 0.7
    # api_key: sk-ant-...  # Or use ANTHROPIC_API_KEY env var

# Environment Variable Overrides:
# - MODEL_PROVIDER: Override provider strategy
# - OLLAMA_HOST: Override Ollama endpoint
# - OLLAMA_ENABLED: Enable/disable Ollama (true/false)
# - CLAUDE_ENABLED: Enable/disable Claude (true/false)
# - ANTHROPIC_API_KEY: Claude API key
# - CLAUDE_MODEL: Override Claude model
"""

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        with output_path_obj.open("w") as f:
            f.write(sample_config)


__all__ = [
    "ClaudeConfig",
    "ModelConfigManager",
    "ModelProviderConfig",
    "OllamaConfig",
]
