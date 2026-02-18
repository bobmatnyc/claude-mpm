"""
Package installer service for centralizing installation logic.

WHY: Replaces repeated installation patterns across setup commands
with a single declarative interface.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from ..cli.constants import SetupService

console = Console()


class InstallerType(str, Enum):
    """Supported package installers."""

    PIPX = "pipx"
    UV = "uv"
    PIP = "pip"

    def __str__(self) -> str:
        return self.value


class InstallAction(str, Enum):
    """Package installation actions."""

    INSTALL = "install"
    UPGRADE = "upgrade"
    REINSTALL = "reinstall"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PackageSpec:
    """Package specification for installation.

    Attributes:
        name: PyPI package name (e.g., "kuzu-memory>=1.6.33")
        binary_name: Binary name for which check (if different from package name)
        python_version: Python version requirement for uv tool install
        extras: Extra dependencies for uv --with flag
        module_name: Python module name for importlib check (e.g., "kuzu_memory")
    """

    name: str
    binary_name: str | None = None
    python_version: str | None = None
    extras: list[str] = field(default_factory=list)
    module_name: str | None = None

    @property
    def base_name(self) -> str:
        """Get package name without version specifier."""
        # Handle version specifiers like >=, ==, >, <, etc.
        for sep in [">=", "<=", "==", ">", "<", "~="]:
            if sep in self.name:
                return self.name.split(sep)[0]
        return self.name


class PackageInstallerService:
    """Centralized package installation service.

    Abstracts the repeated installation logic found in setup commands,
    supporting pipx, uv, and pip installers with install/upgrade/reinstall actions.

    Example:
        installer = PackageInstallerService()
        spec = PACKAGE_SPECS[SetupService.KUZU_MEMORY]
        result = installer.install(spec, InstallAction.INSTALL, force=False, upgrade=False)
    """

    def __init__(self) -> None:
        """Initialize the package installer service."""
        self._detected_installer: InstallerType | None = None

    @property
    def installer_type(self) -> InstallerType:
        """Get the detected installer type."""
        return self._detect_installer()

    def _detect_installer(self) -> InstallerType:
        """Detect the best available installer.

        Priority:
        - In uv projects: uv > pipx > pip
        - Otherwise: pipx > uv > pip

        Returns:
            The detected installer type.
        """
        if self._detected_installer is not None:
            return self._detected_installer

        from pathlib import Path

        from ..services.diagnostics.checks.installation_check import InstallationCheck

        # Check if we're in a uv project
        in_uv_project = False

        # Method 1: Check for uv.lock in current directory or parents
        current_path = Path.cwd()
        for path in [current_path] + list(current_path.parents):
            if (path / "uv.lock").exists():
                in_uv_project = True
                break

        # Method 2: Check if running in uv environment (sys.executable contains "uv")
        if not in_uv_project and "uv" in sys.executable:
            in_uv_project = True

        # Method 3: Check if sys.path contains uv directories
        if not in_uv_project and any("uv" in str(p) for p in sys.path):
            in_uv_project = True

        # Method 4: Check pyproject.toml for [tool.uv] section
        if not in_uv_project:
            pyproject = current_path / "pyproject.toml"
            if pyproject.exists():
                try:
                    import tomllib

                    with open(pyproject, "rb") as f:
                        data = tomllib.load(f)
                        # Check for [tool.uv] section
                        if "tool" in data and "uv" in data["tool"]:
                            in_uv_project = True
                except Exception:
                    # Ignore parsing errors, continue with detection
                    pass

        # Use existing detection utility for available methods
        checker = InstallationCheck()
        methods = checker._check_installation_method()
        detected_methods = methods.details.get("methods_detected", [])

        # Adjust priority based on project type
        if in_uv_project:
            # In uv projects: prioritize uv
            if "uv" in sys.executable or any("uv" in str(p) for p in sys.path):
                self._detected_installer = InstallerType.UV
            elif "pipx" in detected_methods:
                self._detected_installer = InstallerType.PIPX
            else:
                self._detected_installer = InstallerType.PIP
        # Outside uv projects: use traditional priority (pipx > uv > pip)
        elif "pipx" in detected_methods:
            self._detected_installer = InstallerType.PIPX
        elif any("uv" in str(p) for p in sys.path) or "uv" in sys.executable:
            self._detected_installer = InstallerType.UV
        else:
            self._detected_installer = InstallerType.PIP

        return self._detected_installer

    def is_installed(self, spec: PackageSpec) -> bool:
        """Check if a package is installed.

        Tries module import first, then falls back to binary check.

        Args:
            spec: The package specification to check.

        Returns:
            True if the package is installed, False otherwise.
        """
        # First try module import check
        module_name = spec.module_name or spec.base_name.replace("-", "_")
        try:
            module_spec = importlib.util.find_spec(module_name)
            if module_spec is not None:
                return True
        except (ImportError, ModuleNotFoundError):
            pass

        # Fall back to binary check if binary_name is specified
        if spec.binary_name:
            return shutil.which(spec.binary_name) is not None

        return False

    def install(
        self,
        spec: PackageSpec,
        action: InstallAction,
        *,
        force: bool = False,
        upgrade: bool = False,
    ) -> tuple[bool, str]:
        """Install, upgrade, or reinstall a package.

        Args:
            spec: The package specification.
            action: The installation action to perform.
            force: Force reinstall even if already installed.
            upgrade: Upgrade to latest version.

        Returns:
            Tuple of (success, message).
        """
        is_installed = self.is_installed(spec)
        installer = self._detect_installer()

        # Determine actual action based on flags
        if upgrade and is_installed:
            actual_action = InstallAction.UPGRADE
        elif force and is_installed:
            actual_action = InstallAction.REINSTALL
        elif not is_installed:
            actual_action = InstallAction.INSTALL
        else:
            # Already installed and no flags set
            return True, f"{spec.base_name} already installed"

        # Log the action
        action_verb = {
            InstallAction.INSTALL: "Installing",
            InstallAction.UPGRADE: "Upgrading",
            InstallAction.REINSTALL: "Reinstalling",
        }[actual_action]

        console.print(f"[dim]Detected: {installer} installation[/dim]")
        console.print(f"[yellow]{action_verb} {spec.name} via {installer}...[/yellow]")

        try:
            if actual_action == InstallAction.INSTALL:
                self._do_install(spec, installer)
            elif actual_action == InstallAction.UPGRADE:
                self._do_upgrade(spec, installer)
            elif actual_action == InstallAction.REINSTALL:
                self._do_reinstall(spec, installer)

            return True, f"{spec.base_name} {actual_action.value}d via {installer}"

        except subprocess.CalledProcessError as e:
            error_msg = (
                f"Failed to {actual_action.value} {spec.base_name} via {installer}. "
                f"Try manually: {installer} install {spec.name}"
            )
            if e.stderr:
                error_msg += f"\nError: {e.stderr}"
            return False, error_msg

    def _do_install(self, spec: PackageSpec, installer: InstallerType) -> None:
        """Perform package installation.

        Args:
            spec: The package specification.
            installer: The installer to use.

        Raises:
            subprocess.CalledProcessError: If installation fails.
        """
        if installer == InstallerType.PIPX:
            subprocess.run(
                ["pipx", "install", spec.name],
                check=True,
                capture_output=True,
                text=True,
            )  # nosec B603 B607

        elif installer == InstallerType.UV:
            cmd = ["uv", "tool", "install", spec.name]
            # Add extras with --with flag
            for extra in spec.extras:
                cmd.extend(["--with", extra])
            # Add python version if specified
            if spec.python_version:
                cmd.extend(["--python", spec.python_version])
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )  # nosec B603 B607

        elif installer == InstallerType.PIP:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--user",
                    spec.name,
                ],
                check=True,
                capture_output=True,
                text=True,
            )  # nosec B603 B607

    def _do_upgrade(self, spec: PackageSpec, installer: InstallerType) -> None:
        """Perform package upgrade.

        Args:
            spec: The package specification.
            installer: The installer to use.

        Raises:
            subprocess.CalledProcessError: If upgrade fails.
        """
        if installer == InstallerType.PIPX:
            subprocess.run(
                ["pipx", "upgrade", spec.base_name],
                check=True,
                capture_output=True,
                text=True,
            )  # nosec B603 B607

        elif installer == InstallerType.UV:
            subprocess.run(
                ["uv", "tool", "upgrade", spec.base_name],
                check=True,
                capture_output=True,
                text=True,
            )  # nosec B603 B607

        elif installer == InstallerType.PIP:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    spec.name,
                ],
                check=True,
                capture_output=True,
                text=True,
            )  # nosec B603 B607

    def _do_reinstall(self, spec: PackageSpec, installer: InstallerType) -> None:
        """Perform package reinstall.

        Args:
            spec: The package specification.
            installer: The installer to use.

        Raises:
            subprocess.CalledProcessError: If reinstall fails.
        """
        if installer == InstallerType.PIPX:
            subprocess.run(
                ["pipx", "reinstall", spec.base_name],
                check=True,
                capture_output=True,
                text=True,
            )  # nosec B603 B607

        elif installer == InstallerType.UV:
            # uv tool doesn't have reinstall, so uninstall then install
            subprocess.run(
                ["uv", "tool", "uninstall", spec.base_name],
                check=False,  # Don't fail if not installed
                capture_output=True,
                text=True,
            )  # nosec B603 B607
            # Now install fresh
            self._do_install(spec, installer)

        elif installer == InstallerType.PIP:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--force-reinstall",
                    spec.name,
                ],
                check=True,
                capture_output=True,
                text=True,
            )  # nosec B603 B607


# Package specifications for each service
# Import here to avoid circular imports at module level
def get_package_specs() -> dict[SetupService, PackageSpec]:
    """Get package specifications mapping.

    Returns:
        Dictionary mapping SetupService to PackageSpec.
    """
    from ..cli.constants import SetupService

    return {
        SetupService.KUZU_MEMORY: PackageSpec(
            name="kuzu-memory>=1.6.33",
            binary_name="kuzu-memory",
            python_version="3.13",
            extras=["numpy"],
            module_name="kuzu_memory",
        ),
        SetupService.MCP_VECTOR_SEARCH: PackageSpec(
            name="mcp-vector-search",
            binary_name="mcp-vector-search",
            python_version="3.13",
            module_name="mcp_vector_search",
        ),
        SetupService.MCP_SKILLSET: PackageSpec(
            name="mcp-skillset",
            binary_name="mcp-skillset",
            python_version="3.13",
            module_name="mcp_skillset",
        ),
        SetupService.GWORKSPACE_MCP: PackageSpec(
            name="gworkspace-mcp",
            binary_name="gworkspace-mcp",
            module_name="gworkspace_mcp",
        ),
        SetupService.MCP_TICKETER: PackageSpec(
            name="mcp-ticketer",
            binary_name="mcp-ticketer",
            python_version="3.13",
            module_name="mcp_ticketer",
        ),
    }


# Lazy-loaded PACKAGE_SPECS for backward compatibility
PACKAGE_SPECS: dict[SetupService, PackageSpec] | None = None


def get_spec(service: SetupService) -> PackageSpec:
    """Get package spec for a service.

    Args:
        service: The setup service.

    Returns:
        The package specification.

    Raises:
        KeyError: If service has no package spec.
    """
    global PACKAGE_SPECS
    if PACKAGE_SPECS is None:
        PACKAGE_SPECS = get_package_specs()
    return PACKAGE_SPECS[service]
