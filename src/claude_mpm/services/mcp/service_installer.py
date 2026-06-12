"""
MCP Service Installer
=====================

Installs missing MCP services via pipx (preferred) with fallbacks to
uvx and ``pip install --user``.

Extracted from MCPConfigManager as part of god-class decomposition (#507).

References
----------
SPEC-INTEGRATIONS-05~1 : docs/specs/integrations.md#SPEC-INTEGRATIONS-05~1
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - Required for MCP service installation
import sys
import time
from typing import TYPE_CHECKING

from ...core.logger import get_logger

if TYPE_CHECKING:
    from .service_locator import MCPServiceLocator


class MCPServiceInstaller:
    """Install missing MCP services across supported package managers.

    :spec: SPEC-INTEGRATIONS-05~1
    """

    # Standard MCP services that should use pipx
    PIPX_SERVICES = {
        "mcp-vector-search",
        "mcp-browser",
        "mcp-ticketer",
        "kuzu-memory",
    }

    # MCP services installed via cargo (Rust binaries)
    CARGO_SERVICES = {
        "trusty-search",
        "trusty-memory",
        "trusty-analyze",
    }

    # Known missing dependencies for MCP services that pipx doesn't handle
    # automatically. Maps service names to list of missing dependencies that
    # need injection.
    SERVICE_MISSING_DEPENDENCIES = {
        "mcp-ticketer": [
            "gql"
        ],  # mcp-ticketer v0.1.8+ needs gql but doesn't declare it
        # Add more services here as needed, e.g.:
        # "another-service": ["dep1", "dep2"],
    }

    def __init__(self, locator: MCPServiceLocator) -> None:
        """Initialize the service installer.

        Args:
            locator: The :class:`MCPServiceLocator` used to verify installations.
        """
        self.logger = get_logger(__name__)
        self.locator = locator

    def install_missing_services(self) -> tuple[bool, str]:
        """Install missing MCP services via pipx with verification and fallbacks.

        Returns:
            Tuple of (success, message)

        :spec: SPEC-INTEGRATIONS-05~1
        """
        missing = []
        for service_name in self.PIPX_SERVICES:
            if not self.locator.detect_service_path(service_name):
                missing.append(service_name)

        if not missing:
            return True, "All MCP services are already installed"

        installed: list[str] = []
        failed: list[str] = []

        for service_name in missing:
            success, method = self._install_service_with_fallback(service_name)
            if success:
                installed.append(f"{service_name} ({method})")
                self.logger.info(f"Successfully installed {service_name} via {method}")
            else:
                failed.append(service_name)
                self.logger.error(f"Failed to install {service_name}")

        if failed:
            return False, f"Failed to install: {', '.join(failed)}"
        if installed:
            return True, f"Successfully installed: {', '.join(installed)}"
        return True, "No services needed installation"

    def _install_service_with_fallback(self, service_name: str) -> tuple[bool, str]:
        """Install a service with multiple fallback methods.

        Returns:
            Tuple of (success, installation_method)
        """
        # Method 1: Try pipx install
        if shutil.which("pipx"):
            try:
                self.logger.debug(f"Attempting to install {service_name} via pipx...")
                result = subprocess.run(  # nosec B603 B607 - Controlled pipx install
                    ["pipx", "install", service_name],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )

                if result.returncode == 0:
                    if service_name in self.SERVICE_MISSING_DEPENDENCIES:
                        self.logger.debug(
                            f"Injecting missing dependencies for newly installed {service_name}..."
                        )
                        self.inject_missing_dependencies(service_name)

                    if self._verify_service_installed(service_name, "pipx"):
                        return True, "pipx"

                    self.logger.warning(
                        f"pipx install succeeded but verification failed for {service_name}"
                    )
                else:
                    self.logger.debug(f"pipx install failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                self.logger.warning(f"pipx install timed out for {service_name}")
            except Exception as e:
                self.logger.debug(f"pipx install error: {e}")

        # Method 2: Try uvx (if available)
        if shutil.which("uvx"):
            try:
                self.logger.debug(f"Attempting to install {service_name} via uvx...")
                result = subprocess.run(  # nosec B603 B607 - Controlled uvx install
                    ["uvx", "install", service_name],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )

                if result.returncode == 0:
                    if self._verify_service_installed(service_name, "uvx"):
                        return True, "uvx"
            except Exception as e:
                self.logger.debug(f"uvx install error: {e}")

        # Method 3: Try pip install --user
        try:
            self.logger.debug(f"Attempting to install {service_name} via pip --user...")
            result = subprocess.run(  # nosec B603 B607 - Controlled pip install
                [sys.executable, "-m", "pip", "install", "--user", service_name],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if result.returncode == 0:
                if self._verify_service_installed(service_name, "pip"):
                    return True, "pip --user"

                self.logger.warning(
                    f"pip install succeeded but verification failed for {service_name}"
                )
        except Exception as e:
            self.logger.debug(f"pip install error: {e}")

        return False, "none"

    def inject_missing_dependencies(self, service_name: str) -> bool:
        """Inject missing dependencies into a pipx-installed MCP service.

        Some MCP services don't properly declare all their dependencies in
        their package metadata, which causes import errors when pipx creates
        isolated virtual environments. This method injects the missing
        dependencies using ``pipx inject``.

        Args:
            service_name: Name of the MCP service to fix

        Returns:
            True if dependencies were injected successfully or no injection
            needed, False otherwise.
        """
        if service_name not in self.SERVICE_MISSING_DEPENDENCIES:
            return True

        missing_deps = self.SERVICE_MISSING_DEPENDENCIES[service_name]
        if not missing_deps:
            return True

        self.logger.info(
            f"  → Injecting missing dependencies for {service_name}: {', '.join(missing_deps)}"
        )

        all_successful = True
        for dep in missing_deps:
            try:
                self.logger.debug(f"    Injecting {dep} into {service_name}...")
                result = subprocess.run(  # nosec B603 B607 - Controlled pipx inject
                    ["pipx", "inject", service_name, dep],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )

                if result.returncode == 0:
                    self.logger.debug(f"    ✅ Successfully injected {dep}")
                elif (
                    "already satisfied" in result.stderr.lower()
                    or "already installed" in result.stderr.lower()
                ):
                    self.logger.debug(f"    {dep} already present in {service_name}")
                else:
                    self.logger.error(f"    Failed to inject {dep}: {result.stderr}")
                    all_successful = False

            except subprocess.TimeoutExpired:
                self.logger.error(f"    Timeout while injecting {dep}")
                all_successful = False
            except Exception as e:
                self.logger.error(f"    Error injecting {dep}: {e}")
                all_successful = False

        return all_successful

    def _verify_service_installed(self, service_name: str, method: str) -> bool:
        """Verify that a service was successfully installed and is functional.

        Args:
            service_name: Name of the service
            method: Installation method used

        Returns:
            True if service is installed and functional
        """
        # Give the installation a moment to settle
        time.sleep(1)

        service_path = self.locator.detect_service_path(service_name)
        if not service_path:
            # Try pipx run as fallback for pipx installations
            if method == "pipx":
                try:
                    result = subprocess.run(  # nosec B603 B607 - Controlled pipx command
                        ["pipx", "run", service_name, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    if result.returncode == 0 or "version" in result.stdout.lower():
                        self.logger.debug(f"{service_name} accessible via 'pipx run'")
                        return True
                except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
                    pass
            return False

        try:
            test_commands = [
                [service_path, "--version"],
                [service_path, "--help"],
            ]

            for cmd in test_commands:
                result = subprocess.run(  # nosec B603 - Controlled service verification
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )

                output = (result.stdout + result.stderr).lower()
                if result.returncode == 0:
                    return True
                if any(
                    indicator in output
                    for indicator in ["version", "usage", "help", service_name.lower()]
                ):
                    if not any(
                        error in output
                        for error in ["error", "not found", "traceback", "no such"]
                    ):
                        return True
        except Exception as e:
            self.logger.debug(f"Verification error for {service_name}: {e}")

        return False
