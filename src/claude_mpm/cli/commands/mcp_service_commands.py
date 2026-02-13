"""MCP service management commands for claude-mpm CLI.

This module provides enable, disable, and list operations for MCP services
using the service registry for configuration generation.

WHY: Enables users to easily enable/disable MCP services with proper
credential handling and configuration management.
"""

import getpass
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace
    from logging import Logger


def _normalize_mcp_key(service_name: str) -> str:
    """Normalize service name to canonical MCP key.

    This ensures we always use the canonical package name (gworkspace-mcp)
    rather than the binary command name (google-workspace-mcp) as the key
    in .mcp.json configuration files.

    Args:
        service_name: The service name (possibly from binary command)

    Returns:
        The canonical MCP key name for configuration files
    """
    if service_name in ("google-workspace-mcp", "gworkspace-mcp"):
        return "gworkspace-mcp"
    return service_name


class MCPServiceCommands:
    """Command handlers for MCP service management."""

    # Configuration file paths
    GLOBAL_CONFIG = Path.home() / ".claude.json"
    PROJECT_CONFIG = Path(".mcp.json")

    def __init__(self, logger: "Logger") -> None:
        """Initialize the command handler.

        Args:
            logger: Logger instance for output
        """
        self.logger = logger

    def enable_service(self, args: "Namespace") -> int:
        """Enable an MCP service in configuration.

        Args:
            args: Parsed command arguments with:
                - service_name: Name of service to enable
                - interactive: Whether to prompt for credentials
                - env: List of KEY=VALUE strings
                - use_global: Use global config instead of project

        Returns:
            Exit code (0 for success, 1 for error)
        """
        from ...services.mcp_service_registry import MCPServiceRegistry

        service_name = args.service_name

        # Check if service exists in registry
        service = MCPServiceRegistry.get(service_name)
        if not service:
            available = MCPServiceRegistry.list_names()
            print(f"Error: Unknown service '{service_name}'")
            print(f"Available services: {', '.join(available)}")
            return 1

        # Parse environment variables from --env flags
        env_vars: dict[str, str] = {}
        if args.env:
            for env_str in args.env:
                if "=" not in env_str:
                    print(f"Error: Invalid env format '{env_str}'. Use KEY=VALUE")
                    return 1
                key, value = env_str.split("=", 1)
                env_vars[key] = value

        # Interactive mode: prompt for required env vars
        if args.interactive:
            for var in service.required_env:
                if var not in env_vars:
                    # Use getpass for sensitive values (tokens, keys, etc.)
                    if any(
                        keyword in var.upper()
                        for keyword in [
                            "TOKEN",
                            "KEY",
                            "SECRET",
                            "PASSWORD",
                            "CREDENTIAL",
                        ]
                    ):
                        value = getpass.getpass(f"Enter {var}: ")
                    else:
                        value = input(f"Enter {var}: ")
                    if value:
                        env_vars[var] = value

        # Validate required environment variables
        is_valid, missing = MCPServiceRegistry.validate_env(service, env_vars)
        if not is_valid:
            print(
                f"Error: Missing required environment variables: {', '.join(missing)}"
            )
            print(f"Use --env {missing[0]}=VALUE or --interactive to provide them")
            return 1

        # Generate service configuration
        config = MCPServiceRegistry.generate_config(service, env_vars)

        # Determine config file path
        config_path = self.GLOBAL_CONFIG if args.use_global else self.PROJECT_CONFIG

        # Load existing config or create new
        existing_config = self._load_config(config_path)

        # Add/update service in mcpServers section
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}

        # Use canonical key name for .mcp.json
        mcp_key = _normalize_mcp_key(service_name)
        existing_config["mcpServers"][mcp_key] = config

        # Save configuration
        if self._save_config(config_path, existing_config):
            location = (
                "global (~/.claude.json)" if args.use_global else "project (.mcp.json)"
            )
            print(f"Enabled '{mcp_key}' in {location}")
            print(f"Description: {service.description}")

            if service.optional_env:
                print(
                    f"\nOptional environment variables: {', '.join(service.optional_env)}"
                )
                print("Use --env VAR=VALUE to set them")

            return 0
        print(f"Error: Failed to save configuration to {config_path}")
        return 1

    def disable_service(self, args: "Namespace") -> int:
        """Disable an MCP service from configuration.

        This removes the service from the configuration file but does NOT
        uninstall the underlying package.

        Args:
            args: Parsed command arguments with:
                - service_name: Name of service to disable
                - use_global: Use global config instead of project

        Returns:
            Exit code (0 for success, 1 for error)
        """
        service_name = args.service_name
        config_path = self.GLOBAL_CONFIG if args.use_global else self.PROJECT_CONFIG

        # Load existing config
        existing_config = self._load_config(config_path)

        # Check if service exists in config
        if "mcpServers" not in existing_config:
            print(f"Error: No MCP services configured in {config_path}")
            return 1

        if service_name not in existing_config["mcpServers"]:
            print(f"Error: Service '{service_name}' is not enabled")
            enabled = list(existing_config["mcpServers"].keys())
            if enabled:
                print(f"Enabled services: {', '.join(enabled)}")
            return 1

        # Remove service from config
        del existing_config["mcpServers"][service_name]

        # Save configuration
        if self._save_config(config_path, existing_config):
            location = (
                "global (~/.claude.json)" if args.use_global else "project (.mcp.json)"
            )
            print(f"Disabled '{service_name}' in {location}")
            print(
                "Note: The package is still installed. Use pipx/uvx to uninstall if needed."
            )
            return 0
        print(f"Error: Failed to save configuration to {config_path}")
        return 1

    def list_services(self, args: "Namespace") -> int:
        """List MCP services (available and/or enabled).

        Args:
            args: Parsed command arguments with:
                - available: Show all available services from registry
                - enabled: Show only enabled services
                - use_global: Check global config instead of project
                - verbose: Show detailed information

        Returns:
            Exit code (0 for success)
        """
        from ...services.mcp_service_registry import MCPServiceRegistry

        config_path = self.GLOBAL_CONFIG if args.use_global else self.PROJECT_CONFIG
        existing_config = self._load_config(config_path)
        enabled_services = existing_config.get("mcpServers", {})

        # Default: show both available and enabled
        show_available = args.available or not (args.available or args.enabled)
        show_enabled = args.enabled or not (args.available or args.enabled)

        if show_available:
            print("Available MCP Services:")
            print("-" * 60)
            for service in MCPServiceRegistry.list_all():
                status = "[enabled]" if service.name in enabled_services else ""
                default_marker = " (default)" if service.enabled_by_default else ""
                print(f"  {service.name:<25} {status:>10}{default_marker}")
                if args.verbose:
                    print(f"    Description: {service.description}")
                    print(f"    Package: {service.package}")
                    print(f"    Install: {service.install_method.value}")
                    if service.required_env:
                        print(f"    Required env: {', '.join(service.required_env)}")
                    if service.optional_env:
                        print(f"    Optional env: {', '.join(service.optional_env)}")
                    print()
            print()

        if show_enabled:
            location = (
                "global (~/.claude.json)" if args.use_global else "project (.mcp.json)"
            )
            print(f"Enabled Services ({location}):")
            print("-" * 60)
            if not enabled_services:
                print("  No services enabled")
            else:
                for name, config in enabled_services.items():
                    registry_service = MCPServiceRegistry.get(name)
                    if registry_service:
                        print(f"  {name:<25} [registered]")
                        if args.verbose:
                            print(f"    Description: {registry_service.description}")
                    else:
                        print(f"  {name:<25} [custom]")
                    if args.verbose:
                        print(f"    Command: {config.get('command', 'N/A')}")
                        if "args" in config:
                            print(f"    Args: {config['args']}")
                        if "env" in config:
                            # Mask sensitive values
                            env_display = {}
                            for k, v in config.get("env", {}).items():
                                if any(
                                    keyword in k.upper()
                                    for keyword in [
                                        "TOKEN",
                                        "KEY",
                                        "SECRET",
                                        "PASSWORD",
                                    ]
                                ):
                                    env_display[k] = "***"
                                else:
                                    env_display[k] = v
                            print(f"    Env: {env_display}")
                        print()

        return 0

    def _load_config(self, path: Path) -> dict:
        """Load configuration from a JSON file.

        Args:
            path: Path to the configuration file

        Returns:
            Configuration dictionary (empty if file doesn't exist)
        """
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                data = json.load(f)
                return dict(data) if isinstance(data, dict) else {}
        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON in {path}: {e}")
            return {}
        except OSError as e:
            self.logger.warning(f"Failed to read {path}: {e}")
            return {}

    def _save_config(self, path: Path, config: dict) -> bool:
        """Save configuration to a JSON file.

        Args:
            path: Path to the configuration file
            config: Configuration dictionary to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            return True
        except OSError as e:
            self.logger.error(f"Failed to write {path}: {e}")
            return False
