"""
Self-Upgrade Service
====================

Handles version checking and self-upgrade functionality for claude-mpm.
Supports pip, pipx, and npm installations with automatic detection.

WHY: Users should be notified of updates and have an easy way to upgrade
without manually running installation commands.

DESIGN DECISIONS:
- Detects installation method (pip/pipx/npm/editable)
- Non-blocking version checks with caching
- Interactive upgrade prompts with confirmation
- Automatic restart after upgrade
- Graceful failure handling (never breaks existing installation)
"""

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from packaging import version

from ..core.logger import get_logger
from ..core.unified_paths import PathContext
from .mcp_gateway.utils.package_version_checker import PackageVersionChecker


class InstallationMethod:
    """Installation method enumeration."""

    PIP = "pip"
    PIPX = "pipx"
    NPM = "npm"
    EDITABLE = "editable"
    UNKNOWN = "unknown"


class SelfUpgradeService:
    """
    Service for checking and performing self-upgrades.

    Capabilities:
    - Detect current installation method
    - Check PyPI/npm for latest version
    - Prompt user for upgrade confirmation
    - Execute upgrade command
    - Restart after upgrade
    """

    def __init__(self):
        """Initialize the self-upgrade service."""
        self.logger = get_logger("SelfUpgradeService")
        self.version_checker = PackageVersionChecker()
        self.current_version = self._get_current_version()
        self.installation_method = self._detect_installation_method()

    def _get_current_version(self) -> str:
        """
        Get the current installed version.

        Returns:
            Version string (e.g., "4.7.10")
        """
        try:
            from .. import __version__

            return __version__
        except ImportError:
            # Fallback to VERSION file
            try:
                version_file = Path(__file__).parent.parent / "VERSION"
                if version_file.exists():
                    return version_file.read_text().strip()
            except Exception:
                pass

        return "unknown"

    def _detect_installation_method(self) -> str:
        """
        Detect how claude-mpm was installed.

        Returns:
            Installation method constant
        """
        # Check for editable install
        if PathContext.detect_deployment_context().name in [
            "DEVELOPMENT",
            "EDITABLE_INSTALL",
        ]:
            return InstallationMethod.EDITABLE

        # Check for pipx by looking at executable path
        executable = sys.executable
        if "pipx" in executable:
            return InstallationMethod.PIPX

        # Check if npm wrapper is present
        try:
            result = subprocess.run(
                ["npm", "list", "-g", "claude-mpm"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and "claude-mpm" in result.stdout:
                return InstallationMethod.NPM
        except Exception:
            pass

        # Default to pip
        return InstallationMethod.PIP

    async def check_for_update(
        self, cache_ttl: Optional[int] = None
    ) -> Optional[Dict[str, any]]:
        """
        Check if an update is available.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 24 hours)

        Returns:
            Dict with update info or None:
            {
                "current": "4.7.10",
                "latest": "4.7.11",
                "update_available": True,
                "installation_method": "pipx",
                "upgrade_command": "pipx upgrade claude-mpm"
            }
        """
        if self.current_version == "unknown":
            self.logger.warning("Cannot check for updates: version unknown")
            return None

        # Check PyPI for Python installations
        if self.installation_method in [
            InstallationMethod.PIP,
            InstallationMethod.PIPX,
        ]:
            result = await self.version_checker.check_for_update(
                "claude-mpm", self.current_version, cache_ttl
            )
            if result and result.get("update_available"):
                result["installation_method"] = self.installation_method
                result["upgrade_command"] = self._get_upgrade_command()
                return result

        # Check npm for npm installations
        elif self.installation_method == InstallationMethod.NPM:
            npm_version = await self._check_npm_version()
            if npm_version:
                current_ver = version.parse(self.current_version)
                latest_ver = version.parse(npm_version)
                if latest_ver > current_ver:
                    return {
                        "current": self.current_version,
                        "latest": npm_version,
                        "update_available": True,
                        "installation_method": InstallationMethod.NPM,
                        "upgrade_command": self._get_upgrade_command(),
                        "checked_at": datetime.now(timezone.utc).isoformat(),
                    }

        return None

    async def _check_npm_version(self) -> Optional[str]:
        """
        Check npm registry for latest version.

        Returns:
            Latest version string or None
        """
        try:
            result = subprocess.run(
                ["npm", "view", "claude-mpm", "version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            self.logger.debug(f"npm version check failed: {e}")

        return None

    def _get_upgrade_command(self) -> str:
        """
        Get the appropriate upgrade command for current installation method.

        Returns:
            Shell command string to upgrade claude-mpm
        """
        if self.installation_method == InstallationMethod.PIPX:
            return "pipx upgrade claude-mpm"
        if self.installation_method == InstallationMethod.NPM:
            return "npm update -g claude-mpm"
        if self.installation_method == InstallationMethod.PIP:
            return f"{sys.executable} -m pip install --upgrade claude-mpm"
        if self.installation_method == InstallationMethod.EDITABLE:
            return "git pull && pip install -e ."
        return "pip install --upgrade claude-mpm"

    def prompt_for_upgrade(self, update_info: Dict[str, any]) -> bool:
        """
        Prompt user to upgrade.

        Args:
            update_info: Update information dict

        Returns:
            True if user confirms upgrade, False otherwise
        """
        current = update_info["current"]
        latest = update_info["latest"]
        method = update_info.get("installation_method", "unknown")

        print("\n🎉 New version available!")
        print(f"   Current: v{current}")
        print(f"   Latest:  v{latest}")
        print(f"   Installation method: {method}")
        print(f"\nTo upgrade, run: {update_info['upgrade_command']}")

        try:
            response = input("\nWould you like to upgrade now? [y/N]: ").strip().lower()
            return response in ["y", "yes"]
        except (KeyboardInterrupt, EOFError):
            print("\n")
            return False

    def perform_upgrade(self, update_info: Dict[str, any]) -> Tuple[bool, str]:
        """
        Perform the upgrade.

        Args:
            update_info: Update information dict

        Returns:
            Tuple of (success: bool, message: str)
        """
        command = update_info["upgrade_command"]

        # Don't upgrade editable installs automatically
        if self.installation_method == InstallationMethod.EDITABLE:
            return (
                False,
                "Editable installation detected. Please update manually with: git pull && pip install -e .",
            )

        print("\n⏳ Upgrading claude-mpm...")
        print(f"   Running: {command}")

        try:
            # Execute upgrade command
            result = subprocess.run(
                command,
                check=False,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )

            if result.returncode == 0:
                return (True, f"✅ Successfully upgraded to v{update_info['latest']}")
            error_msg = result.stderr or result.stdout or "Unknown error"
            return (False, f"❌ Upgrade failed: {error_msg}")

        except subprocess.TimeoutExpired:
            return (False, "❌ Upgrade timed out")
        except Exception as e:
            return (False, f"❌ Upgrade failed: {e!s}")

    def restart_after_upgrade(self) -> None:
        """
        Restart claude-mpm after a successful upgrade.

        Preserves original command line arguments.
        """
        print("\n🔄 Restarting claude-mpm...")

        try:
            # Get current command line arguments
            args = sys.argv[:]

            # Replace current process with new one
            if self.installation_method == InstallationMethod.PIPX:
                # Use pipx run
                os.execvp("pipx", ["pipx", "run", "claude-mpm", *args[1:]])
            elif self.installation_method == InstallationMethod.NPM:
                # Use npm executable
                os.execvp("claude-mpm", args)
            else:
                # Use Python executable
                os.execvp(sys.executable, [sys.executable, *args])

        except Exception as e:
            self.logger.error(f"Failed to restart: {e}")
            print(f"\n⚠️  Restart failed: {e}")
            print("Please restart claude-mpm manually.")

    async def check_and_prompt_on_startup(
        self, auto_upgrade: bool = False
    ) -> Optional[Dict[str, any]]:
        """
        Check for updates on startup and optionally prompt user.

        Args:
            auto_upgrade: If True, upgrade without prompting (use with caution)

        Returns:
            Update info if available, None otherwise
        """
        # Skip for editable installs
        if self.installation_method == InstallationMethod.EDITABLE:
            return None

        try:
            update_info = await self.check_for_update()

            if update_info and update_info.get("update_available"):
                if auto_upgrade or self.prompt_for_upgrade(update_info):
                    success, message = self.perform_upgrade(update_info)
                    print(message)
                    if success:
                        self.restart_after_upgrade()

                return update_info

        except Exception as e:
            self.logger.debug(f"Startup version check failed: {e}")

        return None
