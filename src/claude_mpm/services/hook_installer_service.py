"""Hook Installer Service for Claude MPM.

This service manages the automatic installation and removal of Claude Code hooks
to enable monitor event forwarding via Socket.IO.
"""

import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..core.logging_config import get_logger


class HookInstallerService:
    """Service for managing Claude Code hook installation and removal."""

    def __init__(self):
        """Initialize the hook installer service."""
        self.logger = get_logger(__name__)
        self.claude_dir = Path.home() / ".claude"
        self.settings_file = self.claude_dir / "settings.json"

    def is_hooks_configured(self) -> bool:
        """Check if hooks are configured in Claude settings.

        Returns:
            True if hooks are properly configured, False otherwise.
        """
        try:
            if not self.settings_file.exists():
                self.logger.debug("Claude settings file does not exist")
                return False

            with open(self.settings_file) as f:
                settings = json.load(f)

            # Check if hooks section exists
            if "hooks" not in settings:
                self.logger.debug("No hooks section in Claude settings")
                return False

            # Check for required hook types
            required_hooks = [
                "UserPromptSubmit",
                "PreToolUse",
                "PostToolUse",
                "Stop",
                "SubagentStop",
            ]

            for hook_type in required_hooks:
                if hook_type not in settings["hooks"]:
                    self.logger.debug(f"Missing hook type: {hook_type}")
                    return False

                # Check if hook is configured with our wrapper
                hooks = settings["hooks"][hook_type]
                if not hooks or not isinstance(hooks, list):
                    self.logger.debug(f"Invalid hooks for {hook_type}")
                    return False

                # Look for our hook wrapper in the configuration
                # Accept either hook_wrapper.sh or claude-hook-handler.sh
                has_our_hook = False
                for hook_config in hooks:
                    if "hooks" in hook_config and isinstance(
                        hook_config["hooks"], list
                    ):
                        for hook in hook_config["hooks"]:
                            if hook.get("type") == "command":
                                command = hook.get("command", "")
                                if (
                                    "hook_wrapper.sh" in command
                                    or "claude-hook-handler.sh" in command
                                ):
                                    has_our_hook = True
                                    break
                    if has_our_hook:
                        break

                if not has_our_hook:
                    self.logger.debug(f"Our hook not found for {hook_type}")
                    return False

            self.logger.info("Claude hooks are properly configured")
            return True

        except Exception as e:
            self.logger.error(f"Error checking hook configuration: {e}")
            return False

    def _detect_package_origin(self) -> Tuple[str, Optional[Path]]:
        """Detect how claude-mpm was installed.

        Returns:
            Tuple of (origin_type, base_path) where origin_type is one of:
            'local', 'pypi', 'pipx', 'npm', or 'unknown'
        """
        # Check if we're in development mode (running from source)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        if (project_root / "src" / "claude_mpm").exists() and (
            project_root / "pyproject.toml"
        ).exists():
            return "local", project_root

        # Check for pipx installation
        if "pipx/venvs/claude-mpm" in str(sys.executable):
            # pipx installation - find the site-packages directory
            import claude_mpm

            package_path = Path(claude_mpm.__file__).parent
            return "pipx", package_path

        # Check for PyPI installation
        try:
            import claude_mpm

            package_path = Path(claude_mpm.__file__).parent
            if "site-packages" in str(package_path):
                return "pypi", package_path
            return "unknown", package_path
        except ImportError:
            pass

        # Check for npm installation (node_modules)
        node_modules_markers = [
            Path.cwd() / "node_modules" / "claude-mpm",
            Path.home() / "node_modules" / "claude-mpm",
            Path("/usr/local/lib/node_modules/claude-mpm"),
        ]
        for marker in node_modules_markers:
            if marker.exists():
                return "npm", marker

        return "unknown", None

    def _find_hook_script(self) -> Optional[Path]:
        """Find the hook script based on installation type.

        Returns:
            Path to the hook script (claude-hook-handler.sh), or None if not found.
        """
        origin, base_path = self._detect_package_origin()

        self.logger.debug(f"Package origin: {origin}, base_path: {base_path}")

        # Primary script to look for (preferred)
        primary_script = "claude-hook-handler.sh"
        # Fallback script for backward compatibility
        fallback_script = "hook_wrapper.sh"

        if origin == "local":
            # Development environment - script is in src/claude_mpm/scripts
            script_path = base_path / "src" / "claude_mpm" / "scripts" / primary_script
            if not script_path.exists():
                # Try hooks directory as fallback
                fallback_path = (
                    base_path
                    / "src"
                    / "claude_mpm"
                    / "hooks"
                    / "claude_hooks"
                    / fallback_script
                )
                if fallback_path.exists():
                    script_path = fallback_path
            self.logger.info("Package origin: Local development")
        elif origin == "pipx":
            # pipx installation - script should be in package/scripts
            script_path = base_path / "scripts" / primary_script
            if not script_path.exists():
                # Try hooks directory as fallback
                fallback_path = base_path / "hooks" / "claude_hooks" / fallback_script
                if fallback_path.exists():
                    script_path = fallback_path
            self.logger.info("Package origin: pipx")
        elif origin == "pypi":
            # PyPI installation
            script_path = base_path / "scripts" / primary_script
            if not script_path.exists():
                # Try hooks directory as fallback
                fallback_path = base_path / "hooks" / "claude_hooks" / fallback_script
                if fallback_path.exists():
                    script_path = fallback_path
            self.logger.info("Package origin: PyPI")
        elif origin == "npm":
            # npm installation
            script_path = base_path / "dist" / "claude_mpm" / "scripts" / primary_script
            if not script_path.exists():
                # Try alternative npm structure
                script_path = (
                    base_path / "src" / "claude_mpm" / "scripts" / primary_script
                )
            if not script_path.exists():
                # Try hooks directory as fallback
                fallback_path = (
                    base_path
                    / "dist"
                    / "claude_mpm"
                    / "hooks"
                    / "claude_hooks"
                    / fallback_script
                )
                if fallback_path.exists():
                    script_path = fallback_path
            self.logger.info("Package origin: npm")
        else:
            # Unknown, try to find it
            self.logger.info("Package origin: Unknown, searching...")
            possible_locations = [
                Path(sys.prefix)
                / "lib"
                / f"python{sys.version_info.major}.{sys.version_info.minor}"
                / "site-packages"
                / "claude_mpm"
                / "scripts"
                / primary_script,
                Path(sys.prefix) / "claude_mpm" / "scripts" / primary_script,
                # For pipx environments
                Path(sys.executable).parent.parent
                / "lib"
                / f"python{sys.version_info.major}.{sys.version_info.minor}"
                / "site-packages"
                / "claude_mpm"
                / "scripts"
                / primary_script,
                # Fallback to hooks directory
                Path(sys.prefix)
                / "lib"
                / f"python{sys.version_info.major}.{sys.version_info.minor}"
                / "site-packages"
                / "claude_mpm"
                / "hooks"
                / "claude_hooks"
                / fallback_script,
            ]
            for loc in possible_locations:
                self.logger.debug(f"Checking location: {loc}")
                if loc.exists():
                    script_path = loc
                    break
            else:
                return None

        # Verify the script exists
        if script_path and script_path.exists():
            self.logger.info(f"Found hook script at: {script_path}")
            return script_path

        self.logger.warning(f"Hook script not found: {script_path}")
        return None

    def install_hooks(self, force: bool = False) -> bool:
        """Install hooks for Claude Code integration.

        Args:
            force: If True, reinstall even if already configured.

        Returns:
            True if hooks were installed successfully, False otherwise.
        """
        try:
            # Check if already configured
            if not force and self.is_hooks_configured():
                self.logger.info("Hooks are already configured")
                return True

            self.logger.info("Installing Claude Code hooks...")

            # Find hook script
            hook_script = self._find_hook_script()
            if not hook_script:
                self.logger.error("Could not find claude-mpm hook script!")
                self.logger.error("Make sure claude-mpm is properly installed.")
                return False

            # Make sure the script is executable
            st = os.stat(hook_script)
            os.chmod(hook_script, st.st_mode | stat.S_IEXEC)
            self.logger.debug(f"Made hook script executable: {hook_script}")

            hook_script_path = str(hook_script.absolute())
            self.logger.info(f"Hook script path: {hook_script_path}")

            # Create claude directory if it doesn't exist
            self.claude_dir.mkdir(exist_ok=True)

            # Load existing settings or create new
            if self.settings_file.exists():
                with open(self.settings_file) as f:
                    settings = json.load(f)
                self.logger.debug("Found existing Claude settings")
            else:
                settings = {}
                self.logger.debug("Creating new Claude settings")

            # Configure hooks
            hook_config = {
                "matcher": "*",
                "hooks": [{"type": "command", "command": hook_script_path}],
            }

            # Update settings
            if "hooks" not in settings:
                settings["hooks"] = {}

            # Add hooks for all event types
            for event_type in [
                "UserPromptSubmit",
                "PreToolUse",
                "PostToolUse",
                "Stop",
                "SubagentStop",
            ]:
                settings["hooks"][event_type] = [hook_config]

            # Write settings
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=2)

            self.logger.info(f"Updated Claude settings at: {self.settings_file}")

            # Copy commands if they exist (for local development)
            origin, base_path = self._detect_package_origin()
            if origin == "local" and base_path:
                commands_src = base_path / "tools" / "dev" / ".claude" / "commands"
                if commands_src.exists():
                    commands_dst = self.claude_dir / "commands"
                    commands_dst.mkdir(exist_ok=True)

                    for cmd_file in commands_src.glob("*.md"):
                        shutil.copy2(cmd_file, commands_dst / cmd_file.name)
                        self.logger.debug(f"Copied command: {cmd_file.name}")

            self.logger.info("Hook installation complete!")
            return True

        except Exception as e:
            self.logger.error(f"Error installing hooks: {e}")
            return False

    def _is_claude_mpm_hook(self, hook_config: Dict[str, Any]) -> bool:
        """Check if a hook configuration belongs to Claude MPM.

        Args:
            hook_config: The hook configuration to check.

        Returns:
            True if this is a Claude MPM hook, False otherwise.
        """
        if "hooks" in hook_config and isinstance(hook_config["hooks"], list):
            for hook in hook_config["hooks"]:
                if hook.get("type") == "command":
                    command = hook.get("command", "")
                    # Check for known Claude MPM hook scripts and paths
                    claude_mpm_indicators = [
                        "hook_wrapper.sh",
                        "claude-hook-handler.sh",
                        "claude-mpm",
                    ]
                    if any(indicator in command for indicator in claude_mpm_indicators):
                        return True
        return False

    def uninstall_hooks(self) -> bool:
        """Remove hooks from Claude settings.

        Returns:
            True if hooks were removed successfully, False otherwise.
        """
        try:
            if not self.settings_file.exists():
                self.logger.info("No Claude settings file found, nothing to uninstall")
                return True

            self.logger.info("Removing Claude Code hooks...")

            with open(self.settings_file) as f:
                settings = json.load(f)

            hooks_removed = 0
            # Remove only our hooks, preserve other settings
            if "hooks" in settings:
                hook_types = [
                    "UserPromptSubmit",
                    "PreToolUse",
                    "PostToolUse",
                    "Stop",
                    "SubagentStop",
                ]

                for hook_type in hook_types:
                    if hook_type in settings["hooks"]:
                        # Filter out our hooks
                        original_count = len(settings["hooks"][hook_type])
                        filtered_hooks = [
                            hook_config
                            for hook_config in settings["hooks"][hook_type]
                            if not self._is_claude_mpm_hook(hook_config)
                        ]

                        removed_count = original_count - len(filtered_hooks)
                        if removed_count > 0:
                            hooks_removed += removed_count
                            self.logger.debug(
                                f"Removed {removed_count} hook(s) from {hook_type}"
                            )

                        # Update or remove the hook type
                        if filtered_hooks:
                            settings["hooks"][hook_type] = filtered_hooks
                        else:
                            del settings["hooks"][hook_type]

                # If no hooks remain, remove the hooks section
                if not settings["hooks"]:
                    del settings["hooks"]

            # Write updated settings
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=2)

            if hooks_removed > 0:
                self.logger.info(
                    f"Successfully removed {hooks_removed} Claude MPM hook(s)"
                )
            else:
                self.logger.info("No Claude MPM hooks found to remove")

            # Optionally remove commands directory if it only contains our commands
            commands_dir = self.claude_dir / "commands"
            if commands_dir.exists():
                our_commands = [
                    "mpm.md",
                    "mpm-status.md",
                ]  # Add other command files as needed
                all_files = list(commands_dir.glob("*.md"))

                # Check if only our commands exist
                if all(f.name in our_commands for f in all_files):
                    shutil.rmtree(commands_dir)
                    self.logger.debug("Removed commands directory")

            return True

        except Exception as e:
            self.logger.error(f"Error uninstalling hooks: {e}")
            return False

    def get_hook_status(self) -> Dict[str, Any]:
        """Get detailed status of hook configuration.

        Returns:
            Dictionary with hook status information.
        """
        status = {
            "configured": False,
            "settings_file": str(self.settings_file),
            "settings_exists": self.settings_file.exists(),
            "hook_types": {},
            "hook_script_path": None,
            "hook_wrapper_path": None,  # Keep for backward compatibility
        }

        try:
            if self.settings_file.exists():
                with open(self.settings_file) as f:
                    settings = json.load(f)

                if "hooks" in settings:
                    for hook_type in [
                        "UserPromptSubmit",
                        "PreToolUse",
                        "PostToolUse",
                        "Stop",
                        "SubagentStop",
                    ]:
                        if hook_type in settings["hooks"]:
                            hooks = settings["hooks"][hook_type]
                            # Find our hook wrapper path
                            for hook_config in hooks:
                                if "hooks" in hook_config:
                                    for hook in hook_config["hooks"]:
                                        if hook.get("type") == "command":
                                            command = hook.get("command", "")
                                            if (
                                                "hook_wrapper.sh" in command
                                                or "claude-hook-handler.sh" in command
                                            ):
                                                status["hook_script_path"] = command
                                                status["hook_wrapper_path"] = (
                                                    command  # For backward compatibility
                                                )
                                                status["hook_types"][hook_type] = True
                                                break

            status["configured"] = self.is_hooks_configured()

        except Exception as e:
            self.logger.error(f"Error getting hook status: {e}")

        return status
