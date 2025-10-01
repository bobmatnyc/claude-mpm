"""
MCP Configuration Command
=========================

Command for managing MCP service configurations with pipx preference.
"""

import json
from pathlib import Path

from ...services.mcp_config_manager import MCPConfigManager
from ..shared import BaseCommand, CommandResult


class MCPConfigCommand(BaseCommand):
    """Manage MCP service configurations."""

    def __init__(self):
        super().__init__("mcp-config")

    def run(self, args) -> CommandResult:
        """Execute the MCP configuration command."""
        manager = MCPConfigManager()

        # Handle different sub-commands
        if hasattr(args, "mcp_config_command"):
            command = args.mcp_config_command

            if command == "detect":
                return self._detect_services(manager)
            if command == "update":
                return self._update_config(manager, args)
            if command == "validate":
                return self._validate_config(manager)
            if command == "install":
                return self._install_services(manager)
            return self._show_status(manager)
        return self._show_status(manager)

    def _detect_services(self, manager: MCPConfigManager) -> CommandResult:
        """Detect available MCP services."""
        results = {}
        for service in manager.PIPX_SERVICES:
            path = manager.detect_service_path(service)
            results[service] = {
                "found": path is not None,
                "path": path or "Not found",
            }

        return CommandResult(
            success=True,
            message="MCP service detection complete",
            data=results,
        )

    def _update_config(self, manager: MCPConfigManager, args) -> CommandResult:
        """Update MCP configuration."""
        force_pipx = getattr(args, "force_pipx", True)
        success, message = manager.update_mcp_config(force_pipx=force_pipx)

        if success:
            # Show the updated configuration
            config_path = Path.cwd() / ".mcp.json"
            if config_path.exists():
                with config_path.open() as f:
                    config = json.load(f)
                return CommandResult(
                    success=True,
                    message=message,
                    data=config,
                )

        return CommandResult(
            success=success,
            message=message,
        )

    def _validate_config(self, manager: MCPConfigManager) -> CommandResult:
        """Validate current MCP configuration."""
        results = manager.validate_configuration()

        all_valid = all(results.values()) if results else False
        message = (
            "All MCP services are properly configured"
            if all_valid
            else "Some MCP services are not accessible"
        )

        return CommandResult(
            success=all_valid,
            message=message,
            data=results,
        )

    def _install_services(self, manager: MCPConfigManager) -> CommandResult:
        """Install missing MCP services."""
        success, message = manager.install_missing_services()
        return CommandResult(
            success=success,
            message=message,
        )

    def _show_status(self, manager: MCPConfigManager) -> CommandResult:
        """Show current MCP configuration status."""
        # Detect services
        detected = {}
        for service in manager.PIPX_SERVICES:
            path = manager.detect_service_path(service)
            detected[service] = {
                "installed": path is not None,
                "path": path or "Not installed",
                "via_pipx": path and "pipx" in path if path else False,
            }

        # Validate configuration
        config_valid = manager.validate_configuration()

        # Read current config
        config_path = Path.cwd() / ".mcp.json"
        current_config = {}
        if config_path.exists():
            try:
                with config_path.open() as f:
                    current_config = json.load(f)
            except Exception:
                pass

        status_data = {
            "services": detected,
            "configuration_valid": config_valid,
            "config_file_exists": config_path.exists(),
            "configured_services": list(current_config.get("mcpServers", {}).keys()),
        }

        return CommandResult(
            success=True,
            message="MCP configuration status",
            data=status_data,
        )


def manage_mcp_config(args):
    """
    Entry point for MCP configuration command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    command = MCPConfigCommand()
    result = command.execute(args)
    return result.exit_code
