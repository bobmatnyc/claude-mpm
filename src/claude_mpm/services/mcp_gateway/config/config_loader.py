from pathlib import Path

"""
MCP Gateway Configuration Loader
================================

Handles loading and discovery of MCP configuration files.

Part of ISS-0034: Infrastructure Setup - MCP Gateway Project Foundation

UPDATED: Migrated to use shared ConfigLoader pattern (TSK-0141)
"""

import os
from typing import List, Optional

import yaml

from claude_mpm.core.logger import get_logger
from claude_mpm.core.shared.config_loader import ConfigLoader, ConfigPattern


class MCPConfigLoader:
    """
    Configuration loader for MCP Gateway.

    This class handles discovering and loading configuration files from
    standard locations, supporting both user and system configurations.

    WHY: We separate configuration loading from the main configuration
    service to support multiple configuration sources and provide a clean
    abstraction for configuration discovery.

    UPDATED: Now uses shared ConfigLoader pattern for consistency (TSK-0141)
    """

    # MCP Gateway configuration pattern
    MCP_CONFIG_PATTERN = ConfigPattern(
        filenames=[
            "mcp_gateway.yaml",
            "mcp_gateway.yml",
            ".mcp_gateway.yaml",
            ".mcp_gateway.yml",
            "config.yaml",
            "config.yml",
        ],
        search_paths=[
            "~/.claude/mcp",
            "~/.config/claude-mpm",
            ".",
            "./config",
            "./.claude",
            "/etc/claude-mpm",
        ],
        env_prefix="CLAUDE_MPM_MCP_",
        defaults={"host": "localhost", "port": 3000, "debug": False, "timeout": 30},
    )

    def __init__(self):
        """Initialize configuration loader."""
        self.logger = get_logger("MCPConfigLoader")
        self._shared_loader = ConfigLoader()

    def find_config_file(self) -> Optional[Path]:
        """
        Find the first available configuration file.

        Searches through standard locations and returns the first
        existing configuration file.

        Returns:
            Path to configuration file if found, None otherwise
        """
        for config_path in self.CONFIG_SEARCH_PATHS:
            expanded_path = config_path.expanduser()
            if expanded_path.exists() and expanded_path.is_file():
                self.logger.info(f"Found configuration file: {expanded_path}")
                return expanded_path

        self.logger.debug("No configuration file found in standard locations")
        return None

    def load_from_file(self, config_path: Path) -> Optional[dict]:
        """
        Load configuration from a specific file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary if successful, None otherwise
        """
        try:
            expanded_path = config_path.expanduser()

            if not expanded_path.exists():
                self.logger.error(f"Configuration file not found: {expanded_path}")
                return None

            with open(expanded_path) as f:
                config = yaml.safe_load(f)

            self.logger.info(f"Configuration loaded from {expanded_path}")
            return config or {}

        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse YAML configuration: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return None

    def load_from_env(self) -> dict:
        """
        Load configuration from environment variables.

        Environment variables follow the pattern: MCP_GATEWAY_<SECTION>_<KEY>

        Returns:
            Configuration dictionary built from environment variables
        """
        config = {}
        prefix = "MCP_GATEWAY_"

        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue

            # Parse environment variable into configuration path
            config_path = env_key[len(prefix) :].lower().split("_")

            # Build nested configuration structure
            current = config
            for part in config_path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the value
            key = config_path[-1]
            try:
                # Try to parse as JSON for complex types
                import json

                current[key] = json.loads(env_value)
            except:
                # Fall back to string value
                current[key] = env_value

            self.logger.debug(f"Loaded from environment: {env_key}")

        return config

    def load(self, config_path: Optional[Path] = None) -> dict:
        """
        Load configuration from all sources.

        Loads configuration in the following priority order:
        1. Default configuration
        2. File configuration (if found or specified)
        3. Environment variable overrides

        Args:
            config_path: Optional specific configuration file path

        Returns:
            Merged configuration dictionary
        """
        from .configuration import MCPConfiguration

        if config_path:
            # Use specific config file with shared loader
            pattern = ConfigPattern(
                filenames=[config_path.name],
                search_paths=[str(config_path.parent)],
                env_prefix=self.MCP_CONFIG_PATTERN.env_prefix,
                defaults=MCPConfiguration.DEFAULT_CONFIG.copy(),
            )
            config_obj = self._shared_loader.load_config(
                pattern, cache_key=f"mcp_{config_path}"
            )
            return config_obj.to_dict()
        # Use standard MCP pattern with defaults
        pattern = ConfigPattern(
            filenames=self.MCP_CONFIG_PATTERN.filenames,
            search_paths=self.MCP_CONFIG_PATTERN.search_paths,
            env_prefix=self.MCP_CONFIG_PATTERN.env_prefix,
            defaults=MCPConfiguration.DEFAULT_CONFIG.copy(),
        )
        config_obj = self._shared_loader.load_config(pattern, cache_key="mcp_gateway")
        return config_obj.to_dict()

    # Backward compatibility methods (deprecated)
    def find_config_file(self) -> Optional[Path]:
        """Find configuration file using legacy method (deprecated)."""
        import warnings

        warnings.warn(
            "find_config_file is deprecated. Use load() method instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Use shared loader to find config file
        return self._shared_loader._find_config_file(self.MCP_CONFIG_PATTERN)

    def load_from_file(self, config_path: Path) -> Optional[dict]:
        """Load from file using legacy method (deprecated)."""
        import warnings

        warnings.warn(
            "load_from_file is deprecated. Use load() method instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Use shared loader
        return self._shared_loader._load_config_file(config_path)

    def load_from_env(self, prefix: str = "CLAUDE_MPM_MCP_") -> dict:
        """Load from environment using legacy method (deprecated)."""
        import warnings

        warnings.warn(
            "load_from_env is deprecated. Use load() method instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Use shared loader
        return self._shared_loader._load_env_config(prefix)

    def _merge_configs(self, base: dict, overlay: dict) -> dict:
        """
        Recursively merge two configuration dictionaries.

        Args:
            base: Base configuration
            overlay: Configuration to merge in

        Returns:
            Merged configuration
        """
        result = base.copy()

        for key, value in overlay.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def create_default_config(self, path: Path) -> bool:
        """
        Create a default configuration file.

        Args:
            path: Path where to create the configuration file

        Returns:
            True if file created successfully
        """
        from .configuration import MCPConfiguration

        try:
            expanded_path = path.expanduser()
            expanded_path.parent.mkdir(parents=True, exist_ok=True)

            with open(expanded_path, "w") as f:
                yaml.dump(
                    MCPConfiguration.DEFAULT_CONFIG,
                    f,
                    default_flow_style=False,
                    sort_keys=True,
                )

            self.logger.info(f"Created default configuration at {expanded_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create default configuration: {e}")
            return False

    def list_config_locations(self) -> List[str]:
        """
        List all configuration file search locations.

        Returns:
            List of configuration file paths (as strings)
        """
        return [str(path.expanduser()) for path in self.CONFIG_SEARCH_PATHS]
