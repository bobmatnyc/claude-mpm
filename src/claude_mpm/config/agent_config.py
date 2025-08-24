#!/usr/bin/env python3
"""
Agent Configuration Module

Provides configuration support for agent loading across all tiers,
with special support for PROJECT-level agent directories.

This module handles:
- Agent directory discovery and configuration
- Environment variable support for agent paths
- Project-specific agent overrides
- Tier precedence configuration

UPDATED: Migrated to use shared ConfigLoader pattern (TSK-0141)
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.shared.config_loader import ConfigLoader, ConfigPattern
from claude_mpm.core.unified_paths import get_path_manager

logger = logging.getLogger(__name__)


class AgentPrecedenceMode(Enum):
    """Agent loading precedence modes."""

    STRICT = "strict"  # PROJECT > USER > SYSTEM (no fallback)
    OVERRIDE = "override"  # PROJECT > USER > SYSTEM (with fallback)
    MERGE = "merge"  # Merge agents from all tiers


@dataclass
class AgentConfig:
    """Configuration for agent loading and discovery."""

    # Agent directory paths
    project_agents_dir: Optional[Path] = None
    user_agents_dir: Optional[Path] = None
    system_agents_dir: Optional[Path] = None

    # Additional search paths (from environment or config)
    additional_paths: List[Path] = field(default_factory=list)

    # Precedence configuration
    precedence_mode: AgentPrecedenceMode = AgentPrecedenceMode.OVERRIDE

    # Feature flags
    enable_project_agents: bool = True
    enable_user_agents: bool = True
    enable_system_agents: bool = True
    enable_hot_reload: bool = True

    # Cache configuration
    cache_ttl_seconds: int = 3600
    enable_caching: bool = True

    # Validation settings
    validate_on_load: bool = True
    strict_validation: bool = False

    # ConfigLoader instance for consistent configuration loading
    _config_loader: ConfigLoader = field(default_factory=ConfigLoader, init=False)

    @classmethod
    def from_environment(cls) -> "AgentConfig":
        """
        Create configuration from environment variables.

        Environment variables:
        - CLAUDE_MPM_PROJECT_AGENTS_DIR: Override project agents directory
        - CLAUDE_MPM_USER_AGENTS_DIR: Override user agents directory
        - CLAUDE_MPM_SYSTEM_AGENTS_DIR: Override system agents directory
        - CLAUDE_MPM_AGENT_SEARCH_PATH: Additional paths (colon-separated)
        - CLAUDE_MPM_AGENT_PRECEDENCE: Precedence mode (strict/override/merge)
        - CLAUDE_MPM_DISABLE_PROJECT_AGENTS: Disable project agents
        - CLAUDE_MPM_DISABLE_USER_AGENTS: Disable user agents
        - CLAUDE_MPM_DISABLE_SYSTEM_AGENTS: Disable system agents
        - CLAUDE_MPM_AGENT_HOT_RELOAD: Enable/disable hot reload
        - CLAUDE_MPM_AGENT_CACHE_TTL: Cache TTL in seconds
        """
        config = cls()

        # Directory overrides
        if proj_dir := os.getenv("CLAUDE_MPM_PROJECT_AGENTS_DIR"):
            config.project_agents_dir = Path(proj_dir)
            logger.info(f"Project agents directory override: {proj_dir}")

        if user_dir := os.getenv("CLAUDE_MPM_USER_AGENTS_DIR"):
            config.user_agents_dir = Path(user_dir)
            logger.info(f"User agents directory override: {user_dir}")

        if sys_dir := os.getenv("CLAUDE_MPM_SYSTEM_AGENTS_DIR"):
            config.system_agents_dir = Path(sys_dir)
            logger.info(f"System agents directory override: {sys_dir}")

        # Additional search paths
        if search_path := os.getenv("CLAUDE_MPM_AGENT_SEARCH_PATH"):
            paths = [Path(p.strip()) for p in search_path.split(":") if p.strip()]
            config.additional_paths = [p for p in paths if p.exists()]
            logger.info(f"Additional agent search paths: {config.additional_paths}")

        # Precedence mode
        if precedence := os.getenv("CLAUDE_MPM_AGENT_PRECEDENCE"):
            try:
                config.precedence_mode = AgentPrecedenceMode(precedence.lower())
                logger.info(f"Agent precedence mode: {config.precedence_mode.value}")
            except ValueError:
                logger.warning(f"Invalid precedence mode: {precedence}, using default")

        # Feature flags
        config.enable_project_agents = (
            os.getenv("CLAUDE_MPM_DISABLE_PROJECT_AGENTS", "").lower() != "true"
        )
        config.enable_user_agents = (
            os.getenv("CLAUDE_MPM_DISABLE_USER_AGENTS", "").lower() != "true"
        )
        config.enable_system_agents = (
            os.getenv("CLAUDE_MPM_DISABLE_SYSTEM_AGENTS", "").lower() != "true"
        )
        config.enable_hot_reload = (
            os.getenv("CLAUDE_MPM_AGENT_HOT_RELOAD", "true").lower() == "true"
        )

        # Cache configuration
        if cache_ttl := os.getenv("CLAUDE_MPM_AGENT_CACHE_TTL"):
            try:
                config.cache_ttl_seconds = int(cache_ttl)
            except ValueError:
                logger.warning(f"Invalid cache TTL: {cache_ttl}, using default")

        return config

    @classmethod
    def from_file(cls, config_file: Path) -> "AgentConfig":
        """
        Load configuration from a JSON or YAML file.

        Args:
            config_file: Path to configuration file

        Returns:
            AgentConfig instance
        """
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}")
            return cls()

        try:
            # Use ConfigLoader for consistent file loading
            config_loader = ConfigLoader()

            # Create a pattern for agent configuration
            pattern = ConfigPattern(
                filenames=[config_file.name],
                search_paths=[str(config_file.parent)],
                env_prefix="CLAUDE_MPM_AGENT_",
                defaults={
                    "enable_project_agents": True,
                    "enable_user_agents": True,
                    "enable_system_agents": True,
                    "enable_hot_reload": True,
                    "cache_ttl_seconds": 3600,
                    "enable_caching": True,
                    "validate_on_load": True,
                    "strict_validation": False,
                    "precedence_mode": "override",
                },
            )

            loaded_config = config_loader.load_config(
                pattern, cache_key=f"agent_{config_file}"
            )
            data = loaded_config.to_dict()

            config = cls()

            # Parse directory paths
            if "project_agents_dir" in data:
                config.project_agents_dir = Path(data["project_agents_dir"])
            if "user_agents_dir" in data:
                config.user_agents_dir = Path(data["user_agents_dir"])
            if "system_agents_dir" in data:
                config.system_agents_dir = Path(data["system_agents_dir"])

            # Parse additional paths
            if "additional_paths" in data:
                config.additional_paths = [Path(p) for p in data["additional_paths"]]

            # Parse precedence mode
            if "precedence_mode" in data:
                config.precedence_mode = AgentPrecedenceMode(data["precedence_mode"])

            # Parse feature flags
            for flag in [
                "enable_project_agents",
                "enable_user_agents",
                "enable_system_agents",
                "enable_hot_reload",
                "enable_caching",
                "validate_on_load",
                "strict_validation",
            ]:
                if flag in data:
                    setattr(config, flag, bool(data[flag]))

            # Parse cache TTL
            if "cache_ttl_seconds" in data:
                config.cache_ttl_seconds = int(data["cache_ttl_seconds"])

            return config

        except Exception as e:
            logger.error(f"Error loading config from {config_file}: {e}")
            return cls()

    @classmethod
    def auto_discover(cls) -> "AgentConfig":
        """
        Automatically discover agent directories and create configuration.

        This method:
        1. Checks environment variables first
        2. Looks for config files in standard locations
        3. Auto-discovers agent directories

        Returns:
            AgentConfig with discovered settings
        """
        # Start with environment configuration
        config = cls.from_environment()

        # Look for config file if not already configured
        if not config.project_agents_dir and not config.user_agents_dir:
            # Check for project config file
            project_config = (
                Path.cwd() / get_path_manager().CONFIG_DIR / "agent_config.yaml"
            )
            if project_config.exists():
                logger.info(f"Loading project agent config from {project_config}")
                file_config = cls.from_file(project_config)
                # Merge with environment config (env takes precedence)
                config = cls._merge_configs(config, file_config)

            # Check for user config file
            user_config_dir = get_path_manager().get_user_config_dir()
            if user_config_dir:
                user_config = user_config_dir / "agent_config.yaml"
                if user_config.exists():
                    logger.info(f"Loading user agent config from {user_config}")
                    file_config = cls.from_file(user_config)
                    config = cls._merge_configs(config, file_config)

        # Auto-discover directories if not configured
        if not config.project_agents_dir:
            project_agents = Path.cwd() / get_path_manager().CONFIG_DIR / "agents"
            if project_agents.exists():
                config.project_agents_dir = project_agents
                logger.debug(f"Auto-discovered project agents at {project_agents}")

        if not config.user_agents_dir:
            user_agents = get_path_manager().get_user_agents_dir()
            if user_agents and user_agents.exists():
                config.user_agents_dir = user_agents
                logger.debug(f"Auto-discovered user agents at {user_agents}")

        if not config.system_agents_dir:
            # Default to built-in agents
            system_agents = Path(__file__).parent.parent / "agents"
            if system_agents.exists():
                config.system_agents_dir = system_agents
                logger.debug(f"Auto-discovered system agents at {system_agents}")

        return config

    @staticmethod
    def _merge_configs(
        primary: "AgentConfig", secondary: "AgentConfig"
    ) -> "AgentConfig":
        """
        Merge two configurations, with primary taking precedence.

        Args:
            primary: Primary configuration (higher precedence)
            secondary: Secondary configuration (lower precedence)

        Returns:
            Merged configuration
        """
        result = AgentConfig()

        # Merge directory paths (primary takes precedence)
        result.project_agents_dir = (
            primary.project_agents_dir or secondary.project_agents_dir
        )
        result.user_agents_dir = primary.user_agents_dir or secondary.user_agents_dir
        result.system_agents_dir = (
            primary.system_agents_dir or secondary.system_agents_dir
        )

        # Merge additional paths
        result.additional_paths = list(
            set(primary.additional_paths + secondary.additional_paths)
        )

        # Use primary's settings for other fields
        result.precedence_mode = primary.precedence_mode
        result.enable_project_agents = primary.enable_project_agents
        result.enable_user_agents = primary.enable_user_agents
        result.enable_system_agents = primary.enable_system_agents
        result.enable_hot_reload = primary.enable_hot_reload
        result.cache_ttl_seconds = primary.cache_ttl_seconds
        result.enable_caching = primary.enable_caching
        result.validate_on_load = primary.validate_on_load
        result.strict_validation = primary.strict_validation

        return result

    def get_enabled_tiers(self) -> Dict[str, Optional[Path]]:
        """
        Get enabled agent directories by tier.

        Returns:
            Dictionary mapping tier names to their paths (if enabled)
        """
        tiers = {}

        if self.enable_project_agents and self.project_agents_dir:
            tiers["project"] = self.project_agents_dir

        if self.enable_user_agents and self.user_agents_dir:
            tiers["user"] = self.user_agents_dir

        if self.enable_system_agents and self.system_agents_dir:
            tiers["system"] = self.system_agents_dir

        return tiers

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "project_agents_dir": (
                str(self.project_agents_dir) if self.project_agents_dir else None
            ),
            "user_agents_dir": (
                str(self.user_agents_dir) if self.user_agents_dir else None
            ),
            "system_agents_dir": (
                str(self.system_agents_dir) if self.system_agents_dir else None
            ),
            "additional_paths": [str(p) for p in self.additional_paths],
            "precedence_mode": self.precedence_mode.value,
            "enable_project_agents": self.enable_project_agents,
            "enable_user_agents": self.enable_user_agents,
            "enable_system_agents": self.enable_system_agents,
            "enable_hot_reload": self.enable_hot_reload,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "enable_caching": self.enable_caching,
            "validate_on_load": self.validate_on_load,
            "strict_validation": self.strict_validation,
        }


# Global configuration instance
_global_config: Optional[AgentConfig] = None


def get_agent_config() -> AgentConfig:
    """
    Get the global agent configuration.

    Returns:
        AgentConfig instance (auto-discovered if not set)
    """
    global _global_config
    if _global_config is None:
        _global_config = AgentConfig.auto_discover()
    return _global_config


def set_agent_config(config: AgentConfig) -> None:
    """
    Set the global agent configuration.

    Args:
        config: AgentConfig instance to use globally
    """
    global _global_config
    _global_config = config
    logger.info(f"Agent configuration updated: {config.get_enabled_tiers()}")


def reset_agent_config() -> None:
    """Reset the global agent configuration to auto-discover on next access."""
    global _global_config
    _global_config = None
    logger.info("Agent configuration reset")
