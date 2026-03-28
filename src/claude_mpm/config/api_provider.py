"""API provider configuration for Claude Code.

This module manages the selection and configuration of API backends
(Bedrock vs Anthropic) for Claude Code sessions.

WHY: Users may want to use Claude through AWS Bedrock (for enterprise/AWS billing)
or directly through Anthropic's API. This configuration allows project-level
switching between these backends.

DESIGN DECISION: Configuration is stored in .claude-mpm/configuration.yaml
under the 'api_provider' section. Environment variables are set early in startup
before Claude Code is launched.
"""

import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from ..core.logging_utils import get_logger

logger = get_logger(__name__)


class APIBackend(StrEnum):
    """API backend options for Claude Code."""

    BEDROCK = "bedrock"
    ANTHROPIC = "anthropic"


@dataclass
class BedrockConfig:
    """Configuration for AWS Bedrock backend."""

    region: str = "us-east-1"
    model: str = "us.anthropic.claude-opus-4-5-20251101-v1:0"


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic API backend.

    WHY: model defaults to empty string so that claude-mpm does NOT override
    Claude Code's own default model when the user hasn't explicitly configured
    one. Only set model to a non-empty value to force a specific model.
    """

    model: str = ""


@dataclass
class APIProviderConfig:
    """API provider configuration for Claude Code.

    Manages backend selection and credentials for Claude sessions.

    Attributes:
        backend: Selected API backend (bedrock or anthropic)
        bedrock: Bedrock-specific configuration
        anthropic: Anthropic-specific configuration
        disable_prompt_caching: When True, sets DISABLE_PROMPT_CACHING=1 env var
            to prevent Claude Code from using prompt caching. Useful when caching
            is broken (e.g. Bedrock with Claude 4 models where cache reads are
            always zero but the 25% cache write surcharge still applies).
    """

    backend: APIBackend = APIBackend.ANTHROPIC
    bedrock: BedrockConfig = field(default_factory=BedrockConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    disable_prompt_caching: bool = False

    @classmethod
    def load(cls, config_path: Path | None = None) -> "APIProviderConfig":
        """Load API provider configuration from configuration.yaml.

        Args:
            config_path: Path to configuration file. If None, uses default
                        .claude-mpm/configuration.yaml in current directory.

        Returns:
            APIProviderConfig instance with loaded or default values.
        """
        if config_path is None:
            config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"

        config = cls()

        if not config_path.exists():
            logger.debug(f"Config file not found: {config_path}, using defaults")
            config._apply_env_overrides()
            return config

        try:
            with open(config_path) as f:
                yaml_content = yaml.safe_load(f) or {}

            api_provider = yaml_content.get("api_provider", {})
            if not api_provider:
                logger.debug("No api_provider section found, using defaults")
                config._apply_env_overrides()
                return config

            # Parse backend
            backend_str = api_provider.get("backend", "anthropic")
            try:
                config.backend = APIBackend(backend_str.lower())
            except ValueError:
                logger.warning(
                    f"Invalid backend '{backend_str}', using default: {config.backend.value}"
                )

            # Parse bedrock config
            bedrock_section = api_provider.get("bedrock", {})
            if bedrock_section:
                config.bedrock = BedrockConfig(
                    region=bedrock_section.get("region", config.bedrock.region),
                    model=bedrock_section.get("model", config.bedrock.model),
                )

            # Parse anthropic config
            anthropic_section = api_provider.get("anthropic", {})
            if anthropic_section:
                config.anthropic = AnthropicConfig(
                    model=anthropic_section.get("model", config.anthropic.model),
                )

            # Parse disable_prompt_caching from YAML
            if "disable_prompt_caching" in api_provider:
                config.disable_prompt_caching = bool(
                    api_provider["disable_prompt_caching"]
                )

            config._apply_env_overrides()

            logger.debug(f"Loaded API provider config: backend={config.backend.value}")
            return config

        except Exception as e:
            logger.warning(f"Failed to load API provider config: {e}, using defaults")
            fallback = cls()
            fallback._apply_env_overrides()
            return fallback

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration.

        Called after YAML parsing to let env vars take precedence.
        Currently handles CLAUDE_MPM_DISABLE_PROMPT_CACHING.
        """
        env_disable_cache = os.environ.get("CLAUDE_MPM_DISABLE_PROMPT_CACHING", "")
        if env_disable_cache.strip().lower() in ("1", "true", "yes"):
            self.disable_prompt_caching = True

    def apply_environment(self) -> dict[str, str]:
        """Apply environment variables for the selected backend.

        Sets appropriate environment variables based on the configured backend.
        For Bedrock: sets CLAUDE_CODE_USE_BEDROCK=1, ANTHROPIC_MODEL, AWS_REGION
        For Anthropic: unsets CLAUDE_CODE_USE_BEDROCK, ensures ANTHROPIC_API_KEY available

        Returns:
            Dictionary of environment variables that were set/modified.
        """
        changes: dict[str, str] = {}

        if self.backend == APIBackend.BEDROCK:
            # Enable Bedrock mode
            os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
            changes["CLAUDE_CODE_USE_BEDROCK"] = "1"

            # Set model
            os.environ["ANTHROPIC_MODEL"] = self.bedrock.model
            changes["ANTHROPIC_MODEL"] = self.bedrock.model

            # Set AWS region if not already set
            if "AWS_REGION" not in os.environ:
                os.environ["AWS_REGION"] = self.bedrock.region
                changes["AWS_REGION"] = self.bedrock.region

            logger.debug(
                f"Configured Bedrock backend: model={self.bedrock.model}, region={self.bedrock.region}"
            )

        elif self.backend == APIBackend.ANTHROPIC:
            # Disable Bedrock mode
            if "CLAUDE_CODE_USE_BEDROCK" in os.environ:
                del os.environ["CLAUDE_CODE_USE_BEDROCK"]
                changes["CLAUDE_CODE_USE_BEDROCK"] = "(unset)"

            # Only set ANTHROPIC_MODEL if explicitly configured by the user.
            # An empty model string means "use Claude Code's own default" —
            # we must NOT set the env var in that case, otherwise we would
            # override Claude Code's current default (e.g. Opus 4.6) with
            # an old hardcoded value.
            if self.anthropic.model:
                os.environ["ANTHROPIC_MODEL"] = self.anthropic.model
                changes["ANTHROPIC_MODEL"] = self.anthropic.model
                logger.debug(
                    f"Configured Anthropic backend: model={self.anthropic.model}"
                )
            else:
                # Clean up any stale ANTHROPIC_MODEL from a previous configuration
                if "ANTHROPIC_MODEL" in os.environ:
                    del os.environ["ANTHROPIC_MODEL"]
                    changes["ANTHROPIC_MODEL"] = "(unset)"
                logger.debug(
                    "Anthropic backend: no model override configured, "
                    "Claude Code will use its own default model"
                )

            # Note: API key is optional when using Claude.ai OAuth login
            if "ANTHROPIC_API_KEY" not in os.environ:  # pragma: allowlist secret
                logger.debug(
                    "ANTHROPIC_API_KEY not found in environment. "  # pragma: allowlist secret
                    "Claude Code will use Claude.ai login or prompt for authentication."
                )

        # Handle prompt caching control
        if self.disable_prompt_caching:
            os.environ["DISABLE_PROMPT_CACHING"] = "1"
            changes["DISABLE_PROMPT_CACHING"] = "1"
            logger.info("Prompt caching disabled via configuration")
        # Clean up env var if it was previously set by us
        elif os.environ.get("DISABLE_PROMPT_CACHING") == "1":
            del os.environ["DISABLE_PROMPT_CACHING"]
            changes["DISABLE_PROMPT_CACHING"] = "(unset)"

        return changes

    def save(self, config_path: Path | None = None) -> None:
        """Save current configuration to configuration.yaml.

        Args:
            config_path: Path to configuration file. If None, uses default
                        .claude-mpm/configuration.yaml in current directory.
        """
        if config_path is None:
            config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config to preserve other sections
        existing_config: dict[str, Any] = {}
        if config_path.exists():
            try:
                with open(config_path) as f:
                    existing_config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to read existing config: {e}")

        # Update api_provider section
        api_provider_data: dict[str, Any] = {
            "backend": self.backend.value,
            "bedrock": {
                "region": self.bedrock.region,
                "model": self.bedrock.model,
            },
            "anthropic": {
                "model": self.anthropic.model,
            },
        }
        if self.disable_prompt_caching:
            api_provider_data["disable_prompt_caching"] = True
        existing_config["api_provider"] = api_provider_data

        # Write back
        try:
            with open(config_path, "w") as f:
                yaml.dump(existing_config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved API provider config to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save API provider config: {e}")
            raise

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary for display.

        Returns:
            Dictionary representation of the configuration.
        """
        result: dict[str, Any] = {
            "backend": self.backend.value,
            "bedrock": {
                "region": self.bedrock.region,
                "model": self.bedrock.model,
            },
            "anthropic": {
                "model": self.anthropic.model,
            },
            "disable_prompt_caching": self.disable_prompt_caching,
        }
        return result


def apply_api_provider_config(config_path: Path | None = None) -> dict[str, str]:
    """Load and apply API provider configuration.

    Convenience function to load config and apply environment variables
    in a single call.

    Args:
        config_path: Path to configuration file (optional).

    Returns:
        Dictionary of environment variables that were set/modified.
    """
    config = APIProviderConfig.load(config_path)
    return config.apply_environment()
