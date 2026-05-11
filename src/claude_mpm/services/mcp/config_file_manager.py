"""
MCP Config File Manager
=======================

Reads and writes Claude MCP configuration files (``~/.claude.json``,
``.mcp.json``) and validates configured service availability.

Extracted from MCPConfigManager as part of god-class decomposition (#507).
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from ...core.logger import get_logger

if TYPE_CHECKING:
    from .config_builder import MCPServiceConfigBuilder
    from .service_installer import MCPServiceInstaller


class ConfigLocation(Enum):
    """Enumeration of Claude configuration file locations."""

    CLAUDE_JSON = Path.home() / ".claude.json"  # Primary Claude config
    CLAUDE_DESKTOP = (
        Path.home() / ".claude" / "claude_desktop_config.json"
    )  # Not used by Claude Code
    PROJECT_MCP = ".mcp.json"  # Project-level MCP config (deprecated)


class MCPConfigFileManager:
    """Read/write Claude MCP configuration files and validate availability."""

    def __init__(
        self,
        builder: MCPServiceConfigBuilder,
        installer: MCPServiceInstaller,
        get_filtered_services,
        project_root: Path | None = None,
        claude_config_path: Path | None = None,
    ) -> None:
        """Initialize the config file manager.

        Args:
            builder: Builder used to generate service configs for legacy
                ``.mcp.json`` updates.
            installer: Installer providing the canonical PIPX_SERVICES set.
            get_filtered_services: Callable returning the dict of filtered
                services for availability checks. Wired by the facade to
                avoid duplicating filtering logic here.
            project_root: Project root directory. Defaults to ``Path.cwd()``.
            claude_config_path: Path to ``~/.claude.json``. Defaults to
                :attr:`ConfigLocation.CLAUDE_JSON`.
        """
        self.logger = get_logger(__name__)
        self.builder = builder
        self.installer = installer
        self._get_filtered_services = get_filtered_services
        self.project_root = project_root or Path.cwd()
        self.claude_config_path = claude_config_path or ConfigLocation.CLAUDE_JSON.value

    def check_mcp_services_available(self) -> tuple[bool, str]:
        """Check if required MCP services are available in ~/.claude.json (READ-ONLY).

        This method performs a READ-ONLY check of MCP service availability.
        It does NOT modify ~/.claude.json. Users should install and configure
        MCP services themselves via pip, npx, or Claude Desktop.

        Returns:
            Tuple of (all_available: bool, message: str)
        """
        expected_services = self._get_filtered_services()

        if not expected_services:
            return True, "No MCP services configured in Claude MPM"

        if not self.claude_config_path.exists():
            return False, f"Claude config not found at {self.claude_config_path}"

        try:
            with self.claude_config_path.open() as f:
                claude_config = json.load(f)
        except Exception as e:
            return False, f"Failed to read Claude config: {e}"

        current_project_key = str(self.project_root)
        project_config = claude_config.get("projects", {}).get(current_project_key)

        if not project_config:
            missing = list(expected_services.keys())
            return (
                False,
                f"Current project not configured in Claude. Missing services: {', '.join(missing)}",
            )

        mcp_servers = project_config.get("mcpServers", {})
        missing_services = [
            name for name in expected_services if name not in mcp_servers
        ]

        if missing_services:
            msg = (
                f"Missing MCP services: {', '.join(missing_services)}. "
                f"Install via: pip install {' '.join(missing_services)} "
                f"or configure in Claude Desktop"
            )
            return False, msg

        return (
            True,
            f"All required MCP services available ({len(expected_services)} services)",
        )

    def ensure_mcp_services_configured(self) -> tuple[bool, str]:
        """DEPRECATED: Auto-configuring ~/.claude.json is no longer supported.

        As of v4.15.0+, MCP services are user-controlled. Users should install
        and configure MCP services themselves via:

        - pip install <service-name>
        - npx @modelcontextprotocol/...
        - Claude Desktop UI

        This method now only performs a read-only check and logs a deprecation
        warning. Use :meth:`check_mcp_services_available` for read-only checks.

        Returns:
            Tuple of (success, message)
        """
        import warnings

        warnings.warn(
            "ensure_mcp_services_configured() is deprecated and will be removed in v6.0.0. "
            "MCP services are now user-controlled. Use check_mcp_services_available() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        return self.check_mcp_services_available()

    def update_mcp_config(self, _force_pipx: bool = True) -> tuple[bool, str]:  # pyright: ignore[reportUnusedParameter]
        """DEPRECATED: Check MCP configuration in ~/.claude.json (READ-ONLY).

        This method no longer modifies ~/.claude.json. Users should install
        and configure MCP services themselves.

        Args:
            _force_pipx: Ignored (kept for backward compatibility)

        Returns:
            Tuple of (success, message) from read-only check
        """
        return self.check_mcp_services_available()

    def update_project_mcp_config(self, force_pipx: bool = True) -> tuple[bool, str]:
        """Update the .mcp.json configuration file (legacy method).

        Args:
            force_pipx: If True, only use pipx installations

        Returns:
            Tuple of (success, message)
        """
        mcp_config_path = self.project_root / ConfigLocation.PROJECT_MCP.value

        existing_config: dict = {}
        if mcp_config_path.exists():
            try:
                with mcp_config_path.open() as f:
                    existing_config = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading existing config: {e}")

        new_config: dict = {"mcpServers": {}}
        missing_services: list[str] = []

        for service_name in self.installer.PIPX_SERVICES:
            config = self.builder.generate_service_config(service_name)
            if config:
                new_config["mcpServers"][service_name] = config
            elif force_pipx:
                missing_services.append(service_name)
            elif service_name in existing_config.get("mcpServers", {}):
                new_config["mcpServers"][service_name] = existing_config["mcpServers"][
                    service_name
                ]

        # Add any additional services from existing config
        for service_name, config in existing_config.get("mcpServers", {}).items():
            if service_name not in new_config["mcpServers"]:
                new_config["mcpServers"][service_name] = config

        try:
            with mcp_config_path.open("w") as f:
                json.dump(new_config, f, indent=2)

            if missing_services:
                message = (
                    f"Updated .mcp.json. Missing services (install via pipx): "
                    f"{', '.join(missing_services)}"
                )
                return True, message
            return True, "Successfully updated .mcp.json with pipx paths"
        except Exception as e:
            return False, f"Failed to update .mcp.json: {e}"

    def validate_configuration(self) -> dict[str, bool]:
        """Validate that all configured MCP services are accessible.

        Returns:
            Dict mapping service names to availability status
        """
        project_key = str(self.project_root)

        if not self.claude_config_path.exists():
            # Also check legacy .mcp.json
            mcp_config_path = self.project_root / ConfigLocation.PROJECT_MCP.value
            if mcp_config_path.exists():
                try:
                    with mcp_config_path.open() as f:
                        config = json.load(f)
                        results: dict[str, bool] = {}
                        for service_name, service_config in config.get(
                            "mcpServers", {}
                        ).items():
                            command_path = service_config.get("command", "")
                            results[service_name] = Path(command_path).exists()
                        return results
                except Exception:  # nosec B110 - Graceful fallback to empty dict
                    pass
            return {}

        try:
            with self.claude_config_path.open() as f:
                claude_config = json.load(f)

            if "projects" in claude_config and project_key in claude_config["projects"]:
                mcp_servers = claude_config["projects"][project_key].get(
                    "mcpServers", {}
                )
                results = {}
                for service_name, service_config in mcp_servers.items():
                    command_path = service_config.get("command", "")
                    results[service_name] = Path(command_path).exists()
                return results
        except Exception as e:
            self.logger.error(f"Error reading config: {e}")

        return {}
