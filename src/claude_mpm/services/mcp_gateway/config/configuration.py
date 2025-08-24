from pathlib import Path

"""
MCP Gateway Configuration Implementation
========================================

Manages configuration for the MCP Gateway service.

Part of ISS-0034: Infrastructure Setup - MCP Gateway Project Foundation
"""

import os
from typing import Any, Dict, Optional

import yaml

from claude_mpm.services.mcp_gateway.core.base import BaseMCPService
from claude_mpm.services.mcp_gateway.core.exceptions import MCPConfigurationError
from claude_mpm.services.mcp_gateway.core.interfaces import IMCPConfiguration
from claude_mpm.services.shared import ConfigServiceBase


class MCPConfiguration(BaseMCPService, IMCPConfiguration):
    """
    MCP Gateway configuration management service.

    This service handles loading, validation, and access to MCP Gateway configuration.
    It supports YAML-based configuration files and environment variable overrides.

    WHY: Configuration is centralized in a service to ensure consistent access
    patterns, validation, and the ability to reload configuration at runtime.
    The service pattern also allows for dependency injection of configuration
    into other MCP services.
    """

    DEFAULT_CONFIG = {
        "mcp": {
            "server": {
                "name": "claude-mpm-gateway",
                "version": "1.0.0",
                "description": "Claude MPM MCP Gateway Server",
                "communication": {
                    "type": "stdio",  # stdio, websocket, or http
                    "timeout": 30,  # seconds
                    "buffer_size": 8192,
                },
                "capabilities": {
                    "tools": True,
                    "resources": False,  # Not yet implemented
                    "prompts": False,  # Not yet implemented
                },
            },
            "tools": {
                "enabled": True,
                "auto_discover": True,
                "discovery_paths": [
                    "~/.claude/mcp/tools",
                    "./mcp_tools",
                ],
                "timeout_default": 30,  # seconds
                "max_concurrent": 10,
            },
            "logging": {
                "level": "INFO",
                "file": "~/.claude/logs/mcp_gateway.log",
                "max_size": "10MB",
                "max_files": 5,
                "format": "json",  # json or text
            },
            "security": {
                "validate_schemas": True,
                "sanitize_inputs": True,
                "max_request_size": 1048576,  # 1MB
                "allowed_tools": [],  # Empty means all tools allowed
                "blocked_tools": [],
            },
        }
    }

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize MCP configuration service.

        Args:
            config_path: Optional path to configuration file
        """
        super().__init__("MCPConfiguration")
        self._config_path = config_path
        self._config_data: Dict[str, Any] = {}
        self._is_loaded = False

        # Initialize shared configuration utilities
        self._config_helper = ConfigServiceBase("mcp_configuration")

        # Merge environment configuration
        self._config_helper.merge_env_config("CLAUDE_MPM_MCP_")

    async def _do_initialize(self) -> bool:
        """
        Initialize the configuration service.

        Returns:
            True if initialization successful
        """
        # Start with default configuration
        self._config_data = self.DEFAULT_CONFIG.copy()

        # Load from file if path provided
        if self._config_path and not self.load_config(self._config_path):
            return False

        # Apply environment variable overrides
        self._apply_env_overrides()

        # Validate configuration
        if not self.validate():
            return False

        self._is_loaded = True
        self.log_info("Configuration initialized successfully")
        return True

    def load_config(self, config_path: Path) -> bool:
        """
        Load configuration from a file.

        Args:
            config_path: Path to configuration file

        Returns:
            True if configuration loaded successfully
        """
        try:
            # Expand user path
            config_path = Path(config_path).expanduser()

            if not config_path.exists():
                self.log_warning(f"Configuration file not found: {config_path}")
                return True  # Not an error, use defaults

            with open(config_path) as f:
                if config_path.suffix in [".yaml", ".yml"]:
                    loaded_config = yaml.safe_load(f) or {}
                else:
                    raise MCPConfigurationError(
                        f"Unsupported configuration file format: {config_path.suffix}"
                    )

            # Merge with existing configuration
            self._merge_config(self._config_data, loaded_config)
            self._config_path = config_path

            self.log_info(f"Configuration loaded from {config_path}")
            return True

        except yaml.YAMLError as e:
            raise MCPConfigurationError(f"Failed to parse YAML configuration: {e}")
        except Exception as e:
            self.log_error(f"Failed to load configuration: {e}")
            return False

    def _merge_config(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> None:
        """
        Recursively merge overlay configuration into base.

        Args:
            base: Base configuration dictionary
            overlay: Configuration to merge in
        """
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _apply_env_overrides(self) -> None:
        """
        Apply environment variable overrides to configuration.

        Environment variables follow the pattern: MCP_GATEWAY_<SECTION>_<KEY>
        For example: MCP_GATEWAY_SERVER_NAME=my-server
        """
        prefix = "MCP_GATEWAY_"

        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue

            # Parse environment variable into configuration path
            config_path = env_key[len(prefix) :].lower().split("_")

            # Navigate to the configuration location
            current = self._config_data
            for i, part in enumerate(config_path[:-1]):
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    self.log_warning(
                        f"Cannot override non-dict config at {'.'.join(config_path[:i+1])}"
                    )
                    break
                current = current[part]
            else:
                # Set the value
                key = config_path[-1]
                # Try to parse as JSON for complex types
                try:
                    import json

                    current[key] = json.loads(env_value)
                except:
                    # Fall back to string value
                    current[key] = env_value

                self.log_debug(f"Applied environment override: {env_key}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key (supports dot notation, e.g., "mcp.server.name")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        parts = key.split(".")
        current = self._config_data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: Configuration value
        """
        parts = key.split(".")
        current = self._config_data

        # Navigate to parent
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                raise MCPConfigurationError(
                    f"Cannot set value at {key}: parent is not a dictionary"
                )
            current = current[part]

        # Set the value
        current[parts[-1]] = value
        self.log_debug(f"Configuration updated: {key} = {value}")

    def validate(self) -> bool:
        """
        Validate the current configuration.

        Returns:
            True if configuration is valid
        """
        try:
            # Check required fields
            required_fields = [
                "mcp.server.name",
                "mcp.server.version",
                "mcp.server.communication.type",
            ]

            for field in required_fields:
                if self.get(field) is None:
                    raise MCPConfigurationError(
                        f"Required configuration field missing: {field}",
                        config_key=field,
                    )

            # Validate communication type
            comm_type = self.get("mcp.server.communication.type")
            if comm_type not in ["stdio", "websocket", "http"]:
                raise MCPConfigurationError(
                    f"Invalid communication type: {comm_type}",
                    config_key="mcp.server.communication.type",
                    expected_type="stdio|websocket|http",
                )

            # Validate numeric fields
            timeout = self.get("mcp.server.communication.timeout")
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise MCPConfigurationError(
                    "Invalid timeout value",
                    config_key="mcp.server.communication.timeout",
                    expected_type="positive number",
                )

            self.log_debug("Configuration validation successful")
            return True

        except MCPConfigurationError:
            raise
        except Exception as e:
            self.log_error(f"Configuration validation failed: {e}")
            return False

    def get_server_config(self) -> Dict[str, Any]:
        """
        Get MCP server configuration.

        Returns:
            Server configuration dictionary
        """
        return self.get("mcp.server", {})

    def get_tools_config(self) -> Dict[str, Any]:
        """
        Get tools configuration.

        Returns:
            Tools configuration dictionary
        """
        return self.get("mcp.tools", {})

    def save_config(self, path: Optional[Path] = None) -> bool:
        """
        Save current configuration to file.

        Args:
            path: Path to save configuration (uses loaded path if not specified)

        Returns:
            True if save successful
        """
        save_path = path or self._config_path
        if not save_path:
            self.log_error("No path specified for saving configuration")
            return False

        try:
            save_path = Path(save_path).expanduser()
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "w") as f:
                yaml.dump(
                    self._config_data, f, default_flow_style=False, sort_keys=True
                )

            self.log_info(f"Configuration saved to {save_path}")
            return True

        except Exception as e:
            self.log_error(f"Failed to save configuration: {e}")
            return False

    def reload(self) -> bool:
        """
        Reload configuration from file.

        Returns:
            True if reload successful
        """
        if not self._config_path:
            self.log_warning("No configuration file to reload")
            return True

        # Reset to defaults
        self._config_data = self.DEFAULT_CONFIG.copy()

        # Reload from file
        if not self.load_config(self._config_path):
            return False

        # Reapply environment overrides
        self._apply_env_overrides()

        # Revalidate
        return self.validate()

    def get_config_with_validation(
        self, key: str, default: Any = None, config_type: Optional[type] = None
    ) -> Any:
        """
        Get configuration value with validation using shared utilities.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if not found
            config_type: Expected type for validation

        Returns:
            Configuration value
        """
        try:
            return self._config_helper.get_config_value(
                key, default, config_type=config_type
            )
        except ValueError:
            # Fall back to standard get method
            return self.get(key, default)

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary using shared utilities."""
        return self._config_helper.get_config_summary()
