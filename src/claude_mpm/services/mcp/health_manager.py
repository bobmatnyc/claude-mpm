"""
MCP Service Health Manager
==========================

Detects and repairs corrupted MCP service installations.

Extracted from MCPConfigManager as part of god-class decomposition (#507).
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - Required for MCP service health checks
from typing import TYPE_CHECKING

from ...core.logger import get_logger

if TYPE_CHECKING:
    from .service_installer import MCPServiceInstaller
    from .service_locator import MCPServiceLocator


class MCPServiceHealthManager:
    """Detect and repair corrupted MCP service installations."""

    def __init__(
        self,
        locator: MCPServiceLocator,
        installer: MCPServiceInstaller,
    ) -> None:
        """Initialize the health manager.

        Args:
            locator: Service locator used for filesystem-based diagnostics.
            installer: Service installer used to repair broken installations.
        """
        self.logger = get_logger(__name__)
        self.locator = locator
        self.installer = installer

    def fix_mcp_service_issues(self) -> tuple[bool, str]:
        """Detect and fix corrupted MCP service installations.

        NOTE: Proactive health checking has been disabled. Each MCP service
        should stand on its own and handle its own issues. This function
        now only returns success without checking services.

        Returns:
            Tuple of (success, message)
        """
        return True, "MCP services managing their own health"

    def _detect_service_issue(self, service_name: str) -> str | None:
        """Detect what type of issue a service has.

        Returns:
            Issue type: 'not_installed', 'import_error', 'missing_dependency',
            'path_issue', 'unknown_error', or None if no issue.
        """
        if not shutil.which("pipx"):
            return "not_installed"

        try:
            pipx_venv_bin = self.locator.pipx_base / service_name / "bin" / service_name
            if pipx_venv_bin.exists():
                self.logger.debug(
                    f"    Testing {service_name} from installed pipx venv: {pipx_venv_bin}"
                )
                result = subprocess.run(  # nosec B603 - Controlled service help check
                    [str(pipx_venv_bin), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )

                stderr_lower = result.stderr.lower()
                stdout_lower = result.stdout.lower()
                combined_output = stderr_lower + stdout_lower

                if (
                    "modulenotfounderror" in combined_output
                    or "importerror" in combined_output
                ):
                    if service_name == "mcp-ticketer" and "gql" in combined_output:
                        return "missing_dependency"
                    return "import_error"

                if "no such file or directory" in combined_output:
                    return "path_issue"

                if (
                    "usage:" in combined_output
                    or "help" in combined_output
                    or result.returncode in [0, 1]
                ):
                    self.logger.debug(
                        f"    {service_name} is working correctly (installed in venv)"
                    )
                    return None

                if result.returncode not in [0, 1]:
                    self.logger.debug(
                        f"{service_name} returned unexpected exit code: {result.returncode}"
                    )
                    return "unknown_error"

                return None

            # Service not installed in pipx venv - use pipx run for detection
            self.logger.debug(
                f"    Testing {service_name} via pipx run (not installed in venv)"
            )
            result = subprocess.run(  # nosec B603 B607 - Controlled pipx run command
                ["pipx", "run", service_name, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            stderr_lower = result.stderr.lower()
            stdout_lower = result.stdout.lower()
            combined_output = stderr_lower + stdout_lower

            if (
                "no apps associated" in combined_output
                or "not found" in combined_output
            ):
                return "not_installed"

            if (
                "modulenotfounderror" in combined_output
                or "importerror" in combined_output
            ):
                self.logger.debug(
                    f"{service_name} has import errors in pipx run cache - needs proper installation"
                )
                return "not_installed"

            if "no such file or directory" in combined_output:
                return "path_issue"

            if (
                "usage:" in combined_output
                or "help" in combined_output
                or result.returncode in [0, 1]
            ):
                return None

            if result.returncode not in [0, 1]:
                return "unknown_error"

        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            self.logger.debug(f"Error detecting issue for {service_name}: {e}")
            return "unknown_error"

        return None

    def _reinstall_service(self, service_name: str) -> bool:
        """Reinstall a corrupted MCP service.

        Args:
            service_name: Name of the service to reinstall

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Uninstalling {service_name}...")

            uninstall_result = subprocess.run(  # nosec B603 B607 - Controlled pipx uninstall
                ["pipx", "uninstall", service_name],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            self.logger.debug(f"Uninstall result: {uninstall_result.returncode}")

            self.logger.debug(f"Installing fresh {service_name}...")
            install_result = subprocess.run(  # nosec B603 B607 - Controlled pipx install
                ["pipx", "install", service_name],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if install_result.returncode == 0:
                if service_name in self.installer.SERVICE_MISSING_DEPENDENCIES:
                    self.logger.debug(
                        f"Injecting missing dependencies for {service_name}..."
                    )
                    self.installer.inject_missing_dependencies(service_name)

                issue = self._detect_service_issue(service_name)
                if issue is None:
                    self.logger.info(f"✅ Successfully reinstalled {service_name}")
                    return True
                self.logger.warning(
                    f"Reinstalled {service_name} but still has issue: {issue}"
                )
                return False
            self.logger.error(
                f"Failed to reinstall {service_name}: {install_result.stderr}"
            )
            return False

        except Exception as e:
            self.logger.error(f"Error reinstalling {service_name}: {e}")
            return False

    def _auto_reinstall_mcp_service(self, service_name: str) -> bool:
        """Automatically reinstall an MCP service with missing dependencies.

        This method:

        1. Uninstalls the corrupted/incomplete service
        2. Reinstalls it fresh from pipx
        3. Verifies the reinstall was successful
        4. Updates status after successful reinstall

        Args:
            service_name: Name of the MCP service to reinstall

        Returns:
            True if reinstall successful, False otherwise
        """
        try:
            if not shutil.which("pipx"):
                self.logger.error("pipx not found - cannot auto-reinstall")
                return False

            self.logger.info(f"  → Uninstalling {service_name}...")
            uninstall_result = subprocess.run(  # nosec B603 B607 - Controlled pipx uninstall
                ["pipx", "uninstall", service_name],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if uninstall_result.returncode != 0:
                self.logger.debug(
                    f"Uninstall had warnings (expected if corrupted): {uninstall_result.stderr}"
                )

            self.logger.info(f"  → Installing fresh {service_name}...")
            install_result = subprocess.run(  # nosec B603 B607 - Controlled pipx install
                ["pipx", "install", service_name],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if install_result.returncode != 0:
                self.logger.error(
                    f"Install failed for {service_name}: {install_result.stderr}"
                )
                return False

            if service_name in self.installer.SERVICE_MISSING_DEPENDENCIES:
                self.logger.info(
                    f"  → Fixing missing dependencies for {service_name}..."
                )
                if not self.installer.inject_missing_dependencies(service_name):
                    self.logger.warning(
                        f"Failed to inject all dependencies for {service_name}, but continuing..."
                    )

            self.logger.debug(f"  → Verifying {service_name} installation...")
            issue = self._detect_service_issue(service_name)

            if issue is None:
                self.logger.info(f"  ✅ Successfully reinstalled {service_name}")
                return True

            if issue == "missing_dependency" and service_name == "mcp-ticketer":
                self.logger.error(
                    f"  {service_name} still has missing dependencies after injection. "
                    f"Manual fix: pipx inject {service_name} gql"
                )
            else:
                self.logger.warning(
                    f"Reinstalled {service_name} but still has issue: {issue}"
                )
            return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout while reinstalling {service_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error auto-reinstalling {service_name}: {e}")
            return False
