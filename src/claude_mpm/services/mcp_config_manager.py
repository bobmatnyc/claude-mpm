"""
MCP Configuration Manager
========================

Manages MCP service configurations, preferring pipx installations
over local virtual environments for better isolation and management.

This module provides utilities to detect, configure, and validate
MCP service installations.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..core.logger import get_logger


class MCPConfigManager:
    """Manages MCP service configurations with pipx preference."""

    # Standard MCP services that should use pipx
    PIPX_SERVICES = {
        "mcp-vector-search",
        "mcp-browser",
        "mcp-ticketer",
    }

    def __init__(self):
        """Initialize the MCP configuration manager."""
        self.logger = get_logger(__name__)
        self.pipx_base = Path.home() / ".local" / "pipx" / "venvs"
        self.project_root = Path.cwd()

    def detect_service_path(self, service_name: str) -> Optional[str]:
        """
        Detect the best path for an MCP service.

        Priority order:
        1. Pipx installation (preferred)
        2. System PATH (likely from pipx)
        3. Local venv (fallback)

        Args:
            service_name: Name of the MCP service

        Returns:
            Path to the service executable or None if not found
        """
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

        self.logger.warning(f"Service {service_name} not found")
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
            config["env"] = {
                "MCP_BROWSER_HOME": str(Path.home() / ".mcp-browser")
            }
        elif service_name == "mcp-ticketer":
            config["args"] = ["mcp"]
        else:
            # Generic config for unknown services
            config["args"] = []

        return config

    def update_mcp_config(self, force_pipx: bool = True) -> Tuple[bool, str]:
        """
        Update the .mcp.json configuration file.

        Args:
            force_pipx: If True, only use pipx installations

        Returns:
            Tuple of (success, message)
        """
        mcp_config_path = self.project_root / ".mcp.json"

        # Load existing config if it exists
        existing_config = {}
        if mcp_config_path.exists():
            try:
                with open(mcp_config_path, "r") as f:
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
            else:
                # Keep existing config if not forcing pipx
                if service_name in existing_config.get("mcpServers", {}):
                    new_config["mcpServers"][service_name] = existing_config[
                        "mcpServers"
                    ][service_name]

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
            else:
                return True, "Successfully updated .mcp.json with pipx paths"
        except Exception as e:
            return False, f"Failed to update .mcp.json: {e}"

    def validate_configuration(self) -> Dict[str, bool]:
        """
        Validate that all configured MCP services are accessible.

        Returns:
            Dict mapping service names to availability status
        """
        mcp_config_path = self.project_root / ".mcp.json"
        if not mcp_config_path.exists():
            return {}

        try:
            with open(mcp_config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading config: {e}")
            return {}

        results = {}
        for service_name, service_config in config.get("mcpServers", {}).items():
            command_path = service_config.get("command", "")
            results[service_name] = Path(command_path).exists()

        return results

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
                result = subprocess.run(
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
        elif installed:
            return True, f"Successfully installed: {', '.join(installed)}"
        else:
            return True, "No services needed installation"