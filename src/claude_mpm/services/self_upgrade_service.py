"""
Self-Upgrade Service
====================

Handles version checking and self-upgrade functionality for claude-mpm.
Supports pip, pipx, npm, uv tool, and Homebrew installations with automatic detection.
Also checks Claude Code version compatibility.

WHY: Users should be notified of updates and have an easy way to upgrade
without manually running installation commands. Claude Code version checking
ensures compatibility with required features.

DESIGN DECISIONS:
- Detects installation method (pip/pipx/npm/uv_tool/homebrew/editable)
- Non-blocking version checks with caching
- Interactive upgrade prompts with confirmation
- Automatic restart after upgrade
- Graceful failure handling (never breaks existing installation)
- Claude Code version detection and compatibility checking
"""

import os
import re
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
    UV_TOOL = "uv_tool"
    HOMEBREW = "homebrew"
    EDITABLE = "editable"
    UNKNOWN = "unknown"


class SelfUpgradeService:
    """
    Service for checking and performing self-upgrades.

    Capabilities:
    - Detect current installation method
    - Check PyPI/npm for latest version
    - Check Claude Code version and compatibility
    - Prompt user for upgrade confirmation
    - Execute upgrade command
    - Restart after upgrade
    """

    # Claude Code version requirements
    CLAUDE_CODE_MIN_VERSION = "1.0.92"
    CLAUDE_CODE_RECOMMENDED_VERSION = "2.0.30"

    def __init__(self):
        """Initialize the self-upgrade service."""
        self.logger = get_logger("SelfUpgradeService")
        self.version_checker = PackageVersionChecker()
        self.current_version = self._get_current_version()
        self.installation_method = self._detect_installation_method()
        self.claude_code_version = self._get_claude_code_version()

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

        Detection priority:
        1. Editable (skip auto-upgrade)
        2. UV Tool
        3. Homebrew
        4. Pipx
        5. NPM
        6. Pip (default)

        Returns:
            Installation method constant
        """
        # Check for editable install
        if PathContext.detect_deployment_context().name in [
            "DEVELOPMENT",
            "EDITABLE_INSTALL",
        ]:
            return InstallationMethod.EDITABLE

        # Check for UV tool installation
        if self._check_uv_tool_installation():
            return InstallationMethod.UV_TOOL

        # Check for Homebrew installation
        if self._check_homebrew_installation():
            return InstallationMethod.HOMEBREW

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

    def _check_uv_tool_installation(self) -> bool:
        """
        Check if claude-mpm is installed via uv tool.

        Detection methods:
        1. Check UV_TOOL_DIR environment variable
        2. Check if executable path contains .local/share/uv/tools/
        3. Fallback: Run `uv tool list` and check for claude-mpm

        Returns:
            True if UV tool installation detected
        """
        # Method 1: Check UV_TOOL_DIR environment variable
        uv_tool_dir = os.environ.get("UV_TOOL_DIR")
        if uv_tool_dir and "claude-mpm" in uv_tool_dir:
            return True

        # Method 2: Check executable path
        executable = sys.executable
        if ".local/share/uv/tools/" in executable or "uv/tools/" in executable:
            return True

        # Method 3: Fallback to `uv tool list` command
        try:
            result = subprocess.run(
                ["uv", "tool", "list"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and "claude-mpm" in result.stdout:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # uv not installed or command failed
            pass
        except Exception as e:
            self.logger.debug(f"UV tool check failed: {e}")

        return False

    def _check_homebrew_installation(self) -> bool:
        """
        Check if claude-mpm is installed via Homebrew.

        Detection methods:
        1. Check if executable path starts with /opt/homebrew/ or /usr/local/Cellar/
        2. Fallback: Run `brew list claude-mpm` to verify

        Returns:
            True if Homebrew installation detected
        """
        # Method 1: Check executable path
        executable = sys.executable
        if executable.startswith("/opt/homebrew/") or executable.startswith(
            "/usr/local/Cellar/"
        ):
            return True

        # Method 2: Fallback to `brew list` command
        try:
            result = subprocess.run(
                ["brew", "list", "claude-mpm"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            # brew list returns 0 if package is installed
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # brew not installed or command failed
            pass
        except Exception as e:
            self.logger.debug(f"Homebrew check failed: {e}")

        return False

    def _get_claude_code_version(self) -> Optional[str]:
        """
        Get the installed Claude Code version.

        Returns:
            Version string (e.g., "2.0.30") or None if not installed
        """
        try:
            # Try to get Claude Code version via CLI
            result = subprocess.run(
                ["claude", "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Parse version from output
                # Expected format: "Claude Code 2.0.30" or similar
                match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
                if match:
                    return match.group(1)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Claude Code not installed or command not found
            pass
        except Exception as e:
            self.logger.debug(f"Failed to detect Claude Code version: {e}")

        return None

    def check_claude_code_compatibility(self) -> Dict[str, any]:
        """
        Check Claude Code version compatibility.

        Returns:
            Dict with compatibility information:
            {
                "installed": bool,
                "version": str or None,
                "meets_minimum": bool,
                "is_recommended": bool,
                "status": str,
                "message": str
            }
        """
        if not self.claude_code_version:
            return {
                "installed": False,
                "version": None,
                "meets_minimum": False,
                "is_recommended": False,
                "status": "not_installed",
                "message": (
                    "Claude Code is not installed or not in PATH.\n"
                    "   Install from: https://docs.anthropic.com/en/docs/claude-code"
                ),
            }

        try:
            current = version.parse(self.claude_code_version)
            minimum = version.parse(self.CLAUDE_CODE_MIN_VERSION)
            recommended = version.parse(self.CLAUDE_CODE_RECOMMENDED_VERSION)

            meets_minimum = current >= minimum
            is_recommended = current >= recommended

            if is_recommended:
                status = "optimal"
                message = f"Claude Code v{self.claude_code_version} (optimal version)"
            elif meets_minimum:
                status = "compatible"
                message = (
                    f"Claude Code v{self.claude_code_version} is compatible\n"
                    f"   Recommended: Upgrade to v{self.CLAUDE_CODE_RECOMMENDED_VERSION}+ for best experience"
                )
            else:
                status = "outdated"
                message = (
                    f"Claude Code v{self.claude_code_version} is outdated\n"
                    f"   Minimum required: v{self.CLAUDE_CODE_MIN_VERSION}\n"
                    f"   Recommended: v{self.CLAUDE_CODE_RECOMMENDED_VERSION}+"
                )

            return {
                "installed": True,
                "version": self.claude_code_version,
                "meets_minimum": meets_minimum,
                "is_recommended": is_recommended,
                "status": status,
                "message": message,
            }

        except Exception as e:
            self.logger.debug(f"Version comparison failed: {e}")
            return {
                "installed": True,
                "version": self.claude_code_version,
                "meets_minimum": False,
                "is_recommended": False,
                "status": "unknown",
                "message": f"Unable to verify Claude Code version: {e}",
            }

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
            InstallationMethod.UV_TOOL,
            InstallationMethod.HOMEBREW,
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
        upgrade_commands = {
            InstallationMethod.UV_TOOL: "uv tool upgrade claude-mpm",
            InstallationMethod.HOMEBREW: "brew upgrade claude-mpm",
            InstallationMethod.PIPX: "pipx upgrade claude-mpm",
            InstallationMethod.NPM: "npm update -g claude-mpm",
            InstallationMethod.PIP: f"{sys.executable} -m pip install --upgrade claude-mpm",
            InstallationMethod.EDITABLE: "git pull && pip install -e .",
        }

        return upgrade_commands.get(
            self.installation_method, "pip install --upgrade claude-mpm"
        )

    def prompt_for_upgrade(self, update_info: Dict[str, any]) -> bool:
        """
        Prompt user to upgrade with enhanced formatting.

        Args:
            update_info: Update information dict

        Returns:
            True if user confirms upgrade, False otherwise
        """
        current = update_info["current"]
        latest = update_info["latest"]
        method = update_info.get("installation_method", "unknown")

        # Enhanced notification with release notes link
        print("\n" + "=" * 70)
        print("📢 Update Available for claude-mpm")
        print("=" * 70)
        print(f"   Current: v{current}")
        print(f"   Latest:  v{latest}")
        print(f"   Method:  {method}")
        print()
        print(f"   Upgrade: {update_info['upgrade_command']}")
        print(
            f"   Release: https://github.com/bobmatnyc/claude-mpm/releases/tag/v{latest}"
        )
        print("=" * 70)

        try:
            response = input("\nWould you like to upgrade now? [y/N]: ").strip().lower()
            return response in ["y", "yes"]
        except (KeyboardInterrupt, EOFError):
            print("\n")
            return False

    def display_update_notification(self, update_info: Dict[str, any]) -> None:
        """
        Display a non-interactive update notification.

        Args:
            update_info: Update information dict
        """
        current = update_info["current"]
        latest = update_info["latest"]
        command = update_info.get("upgrade_command", "pip install --upgrade claude-mpm")

        print(f"\nℹ️  Update available: v{current} → v{latest}")
        print(f"   Run: {command}")
        print(
            f"   Release notes: https://github.com/bobmatnyc/claude-mpm/releases/tag/v{latest}"
        )
        print()

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
            if self.installation_method == InstallationMethod.UV_TOOL:
                # Use uv run
                os.execvp("uv", ["uv", "tool", "run", "claude-mpm", *args[1:]])
            elif self.installation_method == InstallationMethod.HOMEBREW:
                # Use direct executable (installed to PATH by Homebrew)
                os.execvp("claude-mpm", args)
            elif self.installation_method == InstallationMethod.PIPX:
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
        self, auto_upgrade: bool = False, check_claude_code: bool = True
    ) -> Optional[Dict[str, any]]:
        """
        Check for updates on startup and optionally prompt user.
        Also checks Claude Code version compatibility.

        Args:
            auto_upgrade: If True, upgrade without prompting (use with caution)
            check_claude_code: If True, also check Claude Code compatibility

        Returns:
            Update info if available, None otherwise
        """
        # Skip for editable installs
        if self.installation_method == InstallationMethod.EDITABLE:
            return None

        try:
            # Check Claude Code compatibility first
            if check_claude_code:
                claude_compat = self.check_claude_code_compatibility()
                if not claude_compat["installed"]:
                    print("\n⚠️  Claude Code Not Detected")
                    print("   " + claude_compat["message"])
                elif claude_compat["status"] == "outdated":
                    print("\n⚠️  Claude Code Outdated")
                    print("   " + claude_compat["message"].replace("\n", "\n   "))
                elif claude_compat["status"] == "compatible":
                    # Only show if verbose or debug
                    self.logger.debug(claude_compat["message"])

            # Check for claude-mpm updates
            update_info = await self.check_for_update()

            if update_info and update_info.get("update_available"):
                if auto_upgrade:
                    success, message = self.perform_upgrade(update_info)
                    print(message)
                    if success:
                        self.restart_after_upgrade()
                else:
                    # Just display notification, don't prompt during startup
                    self.display_update_notification(update_info)

                return update_info

        except Exception as e:
            self.logger.debug(f"Startup version check failed: {e}")

        return None
