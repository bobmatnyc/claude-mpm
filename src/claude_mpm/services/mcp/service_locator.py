"""
MCP Service Locator
===================

Stateless filesystem/subprocess utilities for discovering MCP service
executables across pipx, uv tool, system PATH, and local venv locations.

Extracted from MCPConfigManager as part of god-class decomposition (#507).
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - Required for MCP service detection
from pathlib import Path

from ...core.logger import get_logger


class MCPServiceLocator:
    """Locate MCP service executables across supported install methods.

    This class is stateless (aside from configurable base paths) and performs
    only read-only filesystem and subprocess operations.
    """

    def __init__(
        self,
        pipx_base: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        """Initialize the service locator.

        Args:
            pipx_base: Base directory for pipx venvs. Defaults to
                ``~/.local/pipx/venvs``.
            project_root: Project root used as a fallback for local venv
                detection. Defaults to ``Path.cwd()``.
        """
        self.logger = get_logger(__name__)
        self.pipx_base = pipx_base or (Path.home() / ".local" / "pipx" / "venvs")
        self.project_root = project_root or Path.cwd()

    def detect_service_path(self, service_name: str) -> str | None:
        """Detect the best path for an MCP service.

        Priority order:
        1. For kuzu-memory: prefer v1.1.0+ with MCP support
        2. Pipx installation (preferred)
        3. uv tool installation
        4. System PATH (likely from pipx or homebrew)
        5. Local venv (fallback)

        Args:
            service_name: Name of the MCP service

        Returns:
            Path to the service executable or None if not found
        """
        # Special handling for kuzu-memory - prefer v1.1.0+ with MCP support
        if service_name == "kuzu-memory":
            candidates: list[str] = []

            pipx_path = self._check_pipx_installation(service_name)
            if pipx_path:
                candidates.append(pipx_path)

            uv_path = self._check_uv_tool_installation(service_name)
            if uv_path and uv_path not in candidates:
                candidates.append(uv_path)

            system_path = shutil.which(service_name)
            if system_path and system_path not in candidates:
                candidates.append(system_path)

            for path in candidates:
                try:
                    result = subprocess.run(  # nosec B603 B607 - Controlled service help check
                        [path, "--help"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    if "claude" in result.stdout or "mcp" in result.stdout:
                        self.logger.debug(
                            f"Found kuzu-memory with MCP support at {path}"
                        )
                        return path
                except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
                    pass

            if candidates:
                self.logger.warning(
                    f"Found kuzu-memory at {candidates[0]} but it lacks MCP support. "
                    f"Upgrade to v1.1.0+ for MCP integration: pipx upgrade kuzu-memory"
                )
            return None

        # Standard detection for other services
        pipx_path = self._check_pipx_installation(service_name)
        if pipx_path:
            self.logger.debug(f"Found {service_name} via pipx: {pipx_path}")
            return pipx_path

        uv_path = self._check_uv_tool_installation(service_name)
        if uv_path:
            self.logger.debug(f"Found {service_name} via uv tool: {uv_path}")
            return uv_path

        system_path = self._check_system_path(service_name)
        if system_path:
            self.logger.debug(f"Found {service_name} in PATH: {system_path}")
            return system_path

        local_path = self._check_local_venv(service_name)
        if local_path:
            self.logger.warning(
                f"Using local venv for {service_name} (consider installing via pipx)"
            )
            return local_path

        self.logger.debug(
            f"Service {service_name} not found - will auto-install when needed"
        )
        return None

    def _check_pipx_installation(self, service_name: str) -> str | None:
        """Check if service is installed via pipx."""
        pipx_venv = self.pipx_base / service_name

        if not pipx_venv.exists():
            return None

        if service_name == "mcp-vector-search":
            python_bin = pipx_venv / "bin" / "python"
            if python_bin.exists() and python_bin.is_file():
                return str(python_bin)
        else:
            service_bin = pipx_venv / "bin" / service_name
            if service_bin.exists() and service_bin.is_file():
                return str(service_bin)

        return None

    def _check_uv_tool_installation(self, service_name: str) -> str | None:
        """Check if service is installed via uv tool.

        Args:
            service_name: Name of the service (e.g., "mcp-vector-search")

        Returns:
            Path to the executable if found, None otherwise
        """
        uv_tool_base = Path.home() / ".local" / "share" / "uv" / "tools"
        uv_venv = uv_tool_base / service_name

        if not uv_venv.exists():
            return None

        if service_name == "mcp-vector-search":
            python_bin = uv_venv / "bin" / "python"
            if python_bin.exists() and python_bin.is_file():
                return str(python_bin)
        else:
            service_bin = uv_venv / "bin" / service_name
            if service_bin.exists() and service_bin.is_file():
                return str(service_bin)

        return None

    def _check_system_path(self, service_name: str) -> str | None:
        """Check if service is available in system PATH."""
        try:
            result = subprocess.run(  # nosec B603 B607 - Controlled which command
                ["which", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                if "/.local/bin/" in path or "/pipx/" in path:
                    return path
        except Exception as e:
            self.logger.debug(f"Error checking system PATH: {e}")

        return None

    def _check_local_venv(self, service_name: str) -> str | None:
        """Check for local virtual environment installation (fallback)."""
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
