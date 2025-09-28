"""
MCP Configuration Manager
========================

Manages MCP service configurations, preferring pipx installations
over local virtual environments for better isolation and management.

This module provides utilities to detect, configure, and validate
MCP service installations.
"""

import json
import subprocess
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..core.logger import get_logger


class ConfigLocation(Enum):
    """Enumeration of Claude configuration file locations."""

    CLAUDE_JSON = Path.home() / ".claude.json"  # Primary Claude config
    CLAUDE_DESKTOP = (
        Path.home() / ".claude" / "claude_desktop_config.json"
    )  # Not used by Claude Code
    PROJECT_MCP = ".mcp.json"  # Project-level MCP config (deprecated)


class MCPConfigManager:
    """Manages MCP service configurations with pipx preference."""

    # Standard MCP services that should use pipx
    PIPX_SERVICES = {
        "mcp-vector-search",
        "mcp-browser",
        "mcp-ticketer",
        "kuzu-memory",
    }

    def __init__(self):
        """Initialize the MCP configuration manager."""
        self.logger = get_logger(__name__)
        self.pipx_base = Path.home() / ".local" / "pipx" / "venvs"
        self.project_root = Path.cwd()

        # Use the proper Claude config file location
        self.claude_config_path = ConfigLocation.CLAUDE_JSON.value

    def detect_service_path(self, service_name: str) -> Optional[str]:
        """
        Detect the best path for an MCP service.

        Priority order:
        1. For kuzu-memory: prefer v1.1.0+ with MCP support
        2. Pipx installation (preferred)
        3. System PATH (likely from pipx or homebrew)
        4. Local venv (fallback)

        Args:
            service_name: Name of the MCP service

        Returns:
            Path to the service executable or None if not found
        """
        # Special handling for kuzu-memory - prefer v1.1.0+ with MCP support
        if service_name == "kuzu-memory":
            candidates = []

            # Check pipx installation
            pipx_path = self._check_pipx_installation(service_name)
            if pipx_path:
                candidates.append(pipx_path)

            # Check system PATH (including homebrew)
            import shutil
            system_path = shutil.which(service_name)
            if system_path and system_path not in candidates:
                candidates.append(system_path)

            # Choose the best candidate (prefer v1.1.0+ with MCP support)
            for path in candidates:
                try:
                    result = subprocess.run(
                        [path, "--help"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    # Check if this version has MCP support
                    if "claude" in result.stdout or "mcp" in result.stdout:
                        self.logger.debug(f"Found kuzu-memory with MCP support at {path}")
                        return path
                except:
                    pass

            # If no MCP-capable version found, log warning but return None
            if candidates:
                self.logger.warning(
                    f"Found kuzu-memory at {candidates[0]} but it lacks MCP support. "
                    f"Upgrade to v1.1.0+ for MCP integration: pipx upgrade kuzu-memory"
                )
            return None  # Don't configure MCP for incompatible versions

        # Standard detection for other services
        # Check pipx installation first
        pipx_path = self._check_pipx_installation(service_name)
        if pipx_path:
            self.logger.debug(f"Found {service_name} via pipx: {pipx_path}")
            return pipx_path

        # Check system PATH
        system_path = self._check_system_path(service_name)
        if system_path:
            self.logger.debug(f"Found {service_name} in PATH: {system_path}")
            return system_path

        # Fallback to local venv
        local_path = self._check_local_venv(service_name)
        if local_path:
            self.logger.warning(
                f"Using local venv for {service_name} (consider installing via pipx)"
            )
            return local_path

        self.logger.debug(f"Service {service_name} not found - will auto-install when needed")
        return None

    def _check_pipx_installation(self, service_name: str) -> Optional[str]:
        """Check if service is installed via pipx."""
        pipx_venv = self.pipx_base / service_name

        if not pipx_venv.exists():
            return None

        # Special handling for mcp-vector-search (needs Python interpreter)
        if service_name == "mcp-vector-search":
            python_bin = pipx_venv / "bin" / "python"
            if python_bin.exists() and python_bin.is_file():
                return str(python_bin)
        else:
            # Other services use direct binary
            service_bin = pipx_venv / "bin" / service_name
            if service_bin.exists() and service_bin.is_file():
                return str(service_bin)

        return None

    def _check_system_path(self, service_name: str) -> Optional[str]:
        """Check if service is available in system PATH."""
        try:
            result = subprocess.run(
                ["which", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                # Verify it's from pipx
                if "/.local/bin/" in path or "/pipx/" in path:
                    return path
        except Exception as e:
            self.logger.debug(f"Error checking system PATH: {e}")

        return None

    def _check_local_venv(self, service_name: str) -> Optional[str]:
        """Check for local virtual environment installation (fallback)."""
        # Common local development paths
        possible_paths = [
            Path.home() / "Projects" / "managed" / service_name / ".venv" / "bin",
            self.project_root / ".venv" / "bin",
            self.project_root / "venv" / "bin",
        ]

        for base_path in possible_paths:
            if service_name == "mcp-vector-search":
                python_bin = base_path / "python"
                if python_bin.exists():
                    return str(python_bin)
            else:
                service_bin = base_path / service_name
                if service_bin.exists():
                    return str(service_bin)

        return None

    def generate_service_config(self, service_name: str) -> Optional[Dict]:
        """
        Generate configuration for a specific MCP service.

        Args:
            service_name: Name of the MCP service

        Returns:
            Service configuration dict or None if service not found
        """
        service_path = self.detect_service_path(service_name)
        if not service_path:
            return None

        config = {
            "type": "stdio",
            "command": service_path,
        }

        # Service-specific configurations
        if service_name == "mcp-vector-search":
            config["args"] = [
                "-m",
                "mcp_vector_search.mcp.server",
                str(self.project_root),
            ]
            config["env"] = {}
        elif service_name == "mcp-browser":
            config["args"] = ["mcp"]
            config["env"] = {"MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")}
        elif service_name == "mcp-ticketer":
            config["args"] = ["mcp"]
        elif service_name == "kuzu-memory":
            # Check kuzu-memory version to determine correct command
            # v1.1.0+ has "claude mcp-server", v1.0.0 has "serve"
            import subprocess
            try:
                result = subprocess.run(
                    [service_path, "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if "claude" in result.stdout:
                    # v1.1.0+ with claude command
                    config["args"] = ["claude", "mcp-server"]
                else:
                    # v1.0.0 with serve command
                    config["args"] = ["serve"]
            except:
                # Default to older version command
                config["args"] = ["serve"]
            # kuzu-memory works with project-specific databases, no custom path needed
        else:
            # Generic config for unknown services
            config["args"] = []

        return config

    def ensure_mcp_services_configured(self) -> Tuple[bool, str]:
        """
        Ensure MCP services are configured in ~/.claude.json on startup.

        This method checks if the core MCP services are configured in the
        current project's mcpServers section and automatically adds them if missing.

        Returns:
            Tuple of (success, message)
        """
        updated = False
        added_services = []
        project_key = str(self.project_root)

        # Load existing Claude config or create minimal structure
        claude_config = {}
        if self.claude_config_path.exists():
            try:
                with open(self.claude_config_path) as f:
                    claude_config = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading {self.claude_config_path}: {e}")
                return False, f"Failed to read Claude config: {e}"

        # Ensure projects structure exists
        if "projects" not in claude_config:
            claude_config["projects"] = {}

        if project_key not in claude_config["projects"]:
            claude_config["projects"][project_key] = {
                "allowedTools": [],
                "history": [],
                "mcpContextUris": [],
                "mcpServers": {},
                "enabledMcpjsonServers": [],
                "disabledMcpjsonServers": [],
                "hasTrustDialogAccepted": False,
                "projectOnboardingSeenCount": 0,
                "hasClaudeMdExternalIncludesApproved": False,
                "hasClaudeMdExternalIncludesWarningShown": False,
            }
            updated = True

        # Get the project's mcpServers section
        project_config = claude_config["projects"][project_key]
        if "mcpServers" not in project_config:
            project_config["mcpServers"] = {}
            updated = True

        # Check each service and add if missing
        for service_name in self.PIPX_SERVICES:
            if service_name not in project_config["mcpServers"]:
                # Try to detect and configure the service
                service_path = self.detect_service_path(service_name)
                if service_path:
                    config = self.generate_service_config(service_name)
                    if config:
                        project_config["mcpServers"][service_name] = config
                        added_services.append(service_name)
                        updated = True
                        self.logger.debug(
                            f"Added MCP service to config: {service_name}"
                        )
                else:
                    self.logger.debug(
                        f"MCP service {service_name} not found for auto-configuration"
                    )

        # Write updated config if changes were made
        if updated:
            try:
                # Create backup if file exists and is large (> 100KB)
                if self.claude_config_path.exists():
                    file_size = self.claude_config_path.stat().st_size
                    if file_size > 100000:  # 100KB
                        backup_path = self.claude_config_path.with_suffix(
                            f".backup.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
                        )
                        import shutil

                        shutil.copy2(self.claude_config_path, backup_path)
                        self.logger.debug(f"Created backup: {backup_path}")

                # Write updated config
                with open(self.claude_config_path, "w") as f:
                    json.dump(claude_config, f, indent=2)

                if added_services:
                    message = (
                        f"Auto-configured MCP services: {', '.join(added_services)}"
                    )
                    # Don't log here - let the caller handle logging to avoid duplicates
                    return True, message
                return True, "All MCP services already configured"
            except Exception as e:
                self.logger.error(f"Failed to write Claude config: {e}")
                return False, f"Failed to write configuration: {e}"

        return True, "All MCP services already configured"

    def update_mcp_config(self, force_pipx: bool = True) -> Tuple[bool, str]:
        """
        Update the MCP configuration in ~/.claude.json.

        Args:
            force_pipx: If True, only use pipx installations

        Returns:
            Tuple of (success, message)
        """
        # This method now delegates to ensure_mcp_services_configured
        # since we're updating the Claude config directly
        return self.ensure_mcp_services_configured()

    def update_project_mcp_config(self, force_pipx: bool = True) -> Tuple[bool, str]:
        """
        Update the .mcp.json configuration file (legacy method).

        Args:
            force_pipx: If True, only use pipx installations

        Returns:
            Tuple of (success, message)
        """
        mcp_config_path = self.project_root / ConfigLocation.PROJECT_MCP.value

        # Load existing config if it exists
        existing_config = {}
        if mcp_config_path.exists():
            try:
                with open(mcp_config_path) as f:
                    existing_config = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading existing config: {e}")

        # Generate new configurations
        new_config = {"mcpServers": {}}
        missing_services = []

        for service_name in self.PIPX_SERVICES:
            config = self.generate_service_config(service_name)
            if config:
                new_config["mcpServers"][service_name] = config
            elif force_pipx:
                missing_services.append(service_name)
            # Keep existing config if not forcing pipx
            elif service_name in existing_config.get("mcpServers", {}):
                new_config["mcpServers"][service_name] = existing_config["mcpServers"][
                    service_name
                ]

        # Add any additional services from existing config
        for service_name, config in existing_config.get("mcpServers", {}).items():
            if service_name not in new_config["mcpServers"]:
                new_config["mcpServers"][service_name] = config

        # Write the updated configuration
        try:
            with open(mcp_config_path, "w") as f:
                json.dump(new_config, f, indent=2)

            if missing_services:
                message = f"Updated .mcp.json. Missing services (install via pipx): {', '.join(missing_services)}"
                return True, message
            return True, "Successfully updated .mcp.json with pipx paths"
        except Exception as e:
            return False, f"Failed to update .mcp.json: {e}"

    def validate_configuration(self) -> Dict[str, bool]:
        """
        Validate that all configured MCP services are accessible.

        Returns:
            Dict mapping service names to availability status
        """
        project_key = str(self.project_root)

        # Check Claude config
        if not self.claude_config_path.exists():
            # Also check legacy .mcp.json
            mcp_config_path = self.project_root / ConfigLocation.PROJECT_MCP.value
            if mcp_config_path.exists():
                try:
                    with open(mcp_config_path) as f:
                        config = json.load(f)
                        results = {}
                        for service_name, service_config in config.get(
                            "mcpServers", {}
                        ).items():
                            command_path = service_config.get("command", "")
                            results[service_name] = Path(command_path).exists()
                        return results
                except Exception:
                    pass
            return {}

        try:
            with open(self.claude_config_path) as f:
                claude_config = json.load(f)

            # Get project's MCP servers
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

    def install_missing_services(self) -> Tuple[bool, str]:
        """
        Install missing MCP services via pipx.

        Returns:
            Tuple of (success, message)
        """
        missing = []
        for service_name in self.PIPX_SERVICES:
            if not self.detect_service_path(service_name):
                missing.append(service_name)

        if not missing:
            return True, "All MCP services are already installed"

        installed = []
        failed = []

        for service_name in missing:
            try:
                self.logger.info(f"Installing {service_name} via pipx...")
                subprocess.run(
                    ["pipx", "install", service_name],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                installed.append(service_name)
                self.logger.info(f"Successfully installed {service_name}")
            except subprocess.CalledProcessError as e:
                failed.append(service_name)
                self.logger.error(f"Failed to install {service_name}: {e.stderr}")

        if failed:
            return False, f"Failed to install: {', '.join(failed)}"
        if installed:
            return True, f"Successfully installed: {', '.join(installed)}"
        return True, "No services needed installation"
