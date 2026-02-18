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
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from ..core.logging_utils import get_logger

logger = get_logger(__name__)


class APIBackend(str, Enum):
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
    """Configuration for Anthropic API backend."""

    model: str = "claude-sonnet-4-20250514"


@dataclass
class APIProviderConfig:
    """API provider configuration for Claude Code.

    Manages backend selection and credentials for Claude sessions.

    Attributes:
        backend: Selected API backend (bedrock or anthropic)
        bedrock: Bedrock-specific configuration
        anthropic: Anthropic-specific configuration
    """

    backend: APIBackend = APIBackend.ANTHROPIC
    bedrock: BedrockConfig = field(default_factory=BedrockConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "APIProviderConfig":
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
            return config

        try:
            with open(config_path) as f:
                yaml_content = yaml.safe_load(f) or {}

            api_provider = yaml_content.get("api_provider", {})
            if not api_provider:
                logger.debug("No api_provider section found, using defaults")
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

            logger.debug(f"Loaded API provider config: backend={config.backend.value}")
            return config

        except Exception as e:
            logger.warning(f"Failed to load API provider config: {e}, using defaults")
            return cls()

    def apply_environment(self) -> Dict[str, str]:
        """Apply environment variables for the selected backend.

        Sets appropriate environment variables based on the configured backend.
        For Bedrock: sets CLAUDE_CODE_USE_BEDROCK=1, ANTHROPIC_MODEL, AWS_REGION
        For Anthropic: unsets CLAUDE_CODE_USE_BEDROCK, ensures ANTHROPIC_API_KEY available

        Returns:
            Dictionary of environment variables that were set/modified.
        """
        changes: Dict[str, str] = {}

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

            # Set model
            os.environ["ANTHROPIC_MODEL"] = self.anthropic.model
            changes["ANTHROPIC_MODEL"] = self.anthropic.model

            # Verify API key is available
            if "ANTHROPIC_API_KEY" not in os.environ:  # pragma: allowlist secret
                logger.warning(
                    "ANTHROPIC_API_KEY not found in environment. "  # pragma: allowlist secret
                    "Anthropic backend requires this variable to be set."
                )

            logger.debug(f"Configured Anthropic backend: model={self.anthropic.model}")

        return changes

    def save(self, config_path: Optional[Path] = None) -> None:
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
        existing_config: Dict[str, Any] = {}
        if config_path.exists():
            try:
                with open(config_path) as f:
                    existing_config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to read existing config: {e}")

        # Update api_provider section
        existing_config["api_provider"] = {
            "backend": self.backend.value,
            "bedrock": {
                "region": self.bedrock.region,
                "model": self.bedrock.model,
            },
            "anthropic": {
                "model": self.anthropic.model,
            },
        }

        # Write back
        try:
            with open(config_path, "w") as f:
                yaml.dump(existing_config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved API provider config to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save API provider config: {e}")
            raise

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for display.

        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "backend": self.backend.value,
            "bedrock": {
                "region": self.bedrock.region,
                "model": self.bedrock.model,
            },
            "anthropic": {
                "model": self.anthropic.model,
            },
        }


def apply_api_provider_config(config_path: Optional[Path] = None) -> Dict[str, str]:
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
