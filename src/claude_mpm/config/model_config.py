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
    model: sonnet
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
from typing import Any

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
    models: dict[str, str] = Field(
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
        default="sonnet",
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
    api_key: str | None = Field(
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

    # Configuration paths in priority order: LOWEST priority first,
    # HIGHEST priority last. When merging, later entries override earlier
    # entries, so project-level configs (earlier in this list) are overlaid
    # onto user-level configs (later in this list).
    #
    # WHY (layered deep-merge): Previously this list was used with a
    # "first file wins" strategy where the first matching file fully
    # replaced all others. That meant a project-level config had to
    # replicate the entire user-level config to override even a single
    # key. With layered deep-merge, project configs can selectively
    # override individual keys (including nested keys like
    # ``models.planning``) without wiping unrelated user-level settings.
    DEFAULT_CONFIG_PATHS = [
        # User-level (lowest priority - loaded first, overridden by others)
        str(Path("~/.claude-mpm/configuration.yaml").expanduser()),
        # Project-level fallbacks
        ".claude-mpm/configuration.yaml",
        "configuration.yaml",
        # Project-level (highest priority - loaded last, overrides user)
        ".claude/configuration.yaml",
    ]

    @staticmethod
    def load_config(
        config_path: str | None = None,
    ) -> ModelProviderConfig:
        """
        Load model configuration from file(s) and environment.

        WHY: Supports multiple configuration sources with priority:
        1. Explicit config_path parameter (replaces all file layers)
        2. Environment variables (override file layers)
        3. Layered deep-merge of default config files (project overlays user)
        4. Default values

        LAYERED DEEP-MERGE BEHAVIOR:
        When ``config_path`` is not provided, ALL files in
        :data:`DEFAULT_CONFIG_PATHS` that exist are loaded and deep-merged
        in priority order. Higher-priority files override individual keys
        in lower-priority files without wiping sibling keys. Nested dicts
        merge recursively; lists are replaced (not concatenated).

        Args:
            config_path: Optional explicit path to a single configuration
                file. When provided, only this file is loaded (no layering).

        Returns:
            ModelProviderConfig with merged settings
        """
        config_data: dict[str, Any] = {}

        # Try to load from file
        if config_path and Path(config_path).exists():
            # Explicit path: single-file load, no layering.
            config_data = ModelConfigManager._load_yaml_file(config_path)
        else:
            # Layered deep-merge: iterate from lowest to highest priority,
            # merging each existing file on top of the accumulated result.
            for default_path in ModelConfigManager.DEFAULT_CONFIG_PATHS:
                if Path(default_path).exists():
                    layer = ModelConfigManager._load_yaml_file(default_path)
                    config_data = ModelConfigManager._deep_merge(config_data, layer)

        # Extract content_agent section if present
        if "content_agent" in config_data:
            content_agent = config_data["content_agent"]
            if isinstance(content_agent, dict):
                config_data = content_agent

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
    def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively deep-merge ``overlay`` onto ``base``.

        WHY: Enables layered configuration where higher-priority configs
        override individual keys in lower-priority configs without
        replacing entire nested structures. For example, a project-level
        config can override ``models.planning`` while preserving all
        other keys under ``models`` defined at the user level.

        MERGE RULES:
        - Scalar values (str, int, float, bool, None): overlay wins
        - Dicts: recurse - merge keys, overlay wins on conflict
        - Lists: overlay replaces base (no concatenation)
        - Type mismatch (e.g. dict vs scalar): overlay wins

        Args:
            base: Lower-priority dict (will not be mutated)
            overlay: Higher-priority dict (will not be mutated)

        Returns:
            New dict containing the merged result. Inputs are not modified.
        """
        result: dict[str, Any] = dict(base)

        for key, overlay_value in overlay.items():
            base_value = result.get(key)
            if isinstance(base_value, dict) and isinstance(overlay_value, dict):
                # Both dicts: recurse for nested merge.
                result[key] = ModelConfigManager._deep_merge(base_value, overlay_value)
            else:
                # Scalar, list, or type mismatch: overlay wins as-is.
                # Lists are intentionally replaced (not concatenated) to
                # avoid surprising behavior with ordered/unique lists.
                result[key] = overlay_value

        return result

    @staticmethod
    def _load_yaml_file(path: str) -> dict[str, Any]:
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
    def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
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
    def get_router_config(config: ModelProviderConfig) -> dict[str, Any]:
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
    def get_ollama_config(config: ModelProviderConfig) -> dict[str, Any]:
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
    def get_claude_config(config: ModelProviderConfig) -> dict[str, Any]:
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
    model: sonnet
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
