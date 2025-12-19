"""
Hook installer for Claude MPM integration with Claude Code.

This module provides functionality to install, update, and manage
claude-mpm hooks in the Claude Code environment.
"""

import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ...core.logger import get_logger


class HookInstaller:
    """Manages installation and configuration of Claude MPM hooks."""

    # Note: SMART_HOOK_SCRIPT is deprecated - we now use deployment-root script
    # Keep for backward compatibility during transition
    SMART_HOOK_SCRIPT = """#!/bin/bash
# DEPRECATED: This script is no longer used
# Claude MPM now uses deployment-root script at src/claude_mpm/scripts/claude-hook-handler.sh

# Function to find claude-mpm installation
find_claude_mpm() {
    # Method 1: Check if claude-mpm is installed via pip
    if command -v claude-mpm &> /dev/null; then
        # Get the actual path of the claude-mpm command
        local cmd_path=$(command -v claude-mpm)
        if [ -L "$cmd_path" ]; then
            # Follow symlink
            cmd_path=$(readlink -f "$cmd_path")
        fi
        # Extract the base directory (usually site-packages or venv)
        local base_dir=$(python3 -c "import claude_mpm; import os; print(Path(os.path.dirname(claude_mpm.__file__).parent))" 2>/dev/null)
        if [ -n "$base_dir" ]; then
            echo "$base_dir"
            return 0
        fi
    fi

    # Method 2: Check common development locations
    local dev_locations=(
        "$HOME/Projects/claude-mpm"
        "$HOME/projects/claude-mpm"
        "$HOME/dev/claude-mpm"
        "$HOME/Development/claude-mpm"
        "$HOME/src/claude-mpm"
        "$HOME/code/claude-mpm"
        "$HOME/workspace/claude-mpm"
        "$HOME/claude-mpm"
        "$(pwd)/claude-mpm"
        "$(pwd)"
    )

    for loc in "${dev_locations[@]}"; do
        if [ -f "$loc/src/claude_mpm/__init__.py" ]; then
            echo "$loc"
            return 0
        fi
    done

    # Method 3: Try to find via Python import
    local python_path=$(python3 -c "
try:
    import claude_mpm
    import os
    # Get the package directory
    pkg_dir = Path(claude_mpm.__file__).parent
    # Check if we're in a development install (src directory)
    if 'src' in pkg_dir:
        # Go up to find the project root
        parts = pkg_dir.split(os.sep)
        if 'src' in parts:
            src_idx = parts.index('src')
            project_root = os.sep.join(parts[:src_idx])
            print(project_root)
        else:
            print(Path(os.path.dirname(pkg_dir).parent))
    else:
        # Installed package - just return the package location
        print(Path(pkg_dir).parent)
except Exception:
    pass
" 2>/dev/null)

    if [ -n "$python_path" ]; then
        echo "$python_path"
        return 0
    fi

    # Method 4: Search in PATH for claude-mpm installations
    local IFS=':'
    for path_dir in $PATH; do
        if [ -f "$path_dir/claude-mpm" ]; then
            # Found claude-mpm executable, try to find its package
            local pkg_dir=$(cd "$path_dir" && python3 -c "import claude_mpm; import os; print(Path(os.path.dirname(claude_mpm.__file__).parent))" 2>/dev/null)
            if [ -n "$pkg_dir" ]; then
                echo "$pkg_dir"
                return 0
            fi
        fi
    done

    return 1
}

# Function to setup Python environment
setup_python_env() {
    local project_dir="$1"

    # Check for virtual environment in the project
    if [ -f "$project_dir/venv/bin/activate" ]; then
        source "$project_dir/venv/bin/activate"
        export PYTHON_CMD="$project_dir/venv/bin/python"
    elif [ -f "$project_dir/.venv/bin/activate" ]; then
        source "$project_dir/.venv/bin/activate"
        export PYTHON_CMD="$project_dir/.venv/bin/python"
    elif [ -n "$VIRTUAL_ENV" ]; then
        # Already in a virtual environment
        export PYTHON_CMD="$VIRTUAL_ENV/bin/python"
    elif command -v python3 &> /dev/null; then
        export PYTHON_CMD="python3"
    else
        export PYTHON_CMD="python"
    fi

    # Set PYTHONPATH for development installs
    if [ -d "$project_dir/src" ]; then
        export PYTHONPATH="$project_dir/src:$PYTHONPATH"
    fi
}

# Main execution
main() {
    # Debug mode (can be disabled in production)
    if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Smart hook starting..." >> /tmp/claude-mpm-hook.log
    fi

    # Find claude-mpm installation
    PROJECT_DIR=$(find_claude_mpm)

    if [ -z "$PROJECT_DIR" ]; then
        # Claude MPM not found - return continue to not block Claude
        if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
            echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Claude MPM not found, continuing..." >> /tmp/claude-mpm-hook.log
        fi
        echo '{"action": "continue"}'
        exit 0
    fi

    if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Found claude-mpm at: $PROJECT_DIR" >> /tmp/claude-mpm-hook.log
    fi

    # Setup Python environment
    setup_python_env "$PROJECT_DIR"

    # Debug logging
    if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] PYTHON_CMD: $PYTHON_CMD" >> /tmp/claude-mpm-hook.log
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] PYTHONPATH: $PYTHONPATH" >> /tmp/claude-mpm-hook.log
    fi

    # Set Socket.IO configuration for hook events
    export CLAUDE_MPM_SOCKETIO_PORT="${CLAUDE_MPM_SOCKETIO_PORT:-8765}"

    # Run the hook handler
    if ! "$PYTHON_CMD" -m claude_mpm.hooks.claude_hooks.hook_handler "$@" 2>/tmp/claude-mpm-hook-error.log; then
        # If the Python handler fails, always return continue to not block Claude
        if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
            echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Hook handler failed, see /tmp/claude-mpm-hook-error.log" >> /tmp/claude-mpm-hook.log
            echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Error: $(cat /tmp/claude-mpm-hook-error.log 2>/dev/null | head -5)" >> /tmp/claude-mpm-hook.log
        fi
        echo '{"action": "continue"}'
        exit 0
    fi

    # Success
    exit 0
}

# Run main function
main "$@"
"""

    # Minimum Claude Code version required for hook monitoring
    MIN_CLAUDE_VERSION = "1.0.92"
    # Minimum version for PreToolUse input modification support
    MIN_PRETOOL_MODIFY_VERSION = "2.0.30"

    def __init__(self):
        """Initialize the hook installer."""
        self.logger = get_logger(__name__)
        self.claude_dir = Path.home() / ".claude"
        self.hooks_dir = self.claude_dir / "hooks"  # Kept for backward compatibility
        # Use settings.json for hooks (Claude Code reads from this file)
        self.settings_file = self.claude_dir / "settings.json"
        # There is no legacy settings file - this was a bug where both pointed to same file
        # Setting to None to disable cleanup that was deleting freshly installed hooks
        self.old_settings_file = None
        self._claude_version: Optional[str] = None
        self._hook_script_path: Optional[Path] = None

    def get_claude_version(self) -> Optional[str]:
        """
        Get the installed Claude Code version.

        Returns:
            Version string (e.g., "1.0.92") or None if not detected
        """
        if self._claude_version is not None:
            return self._claude_version

        try:
            # Run claude --version command
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0:
                # Parse version from output (e.g., "1.0.92 (Claude Code)")
                version_text = result.stdout.strip()
                # Extract version number using regex
                match = re.match(r"^([\d\.]+)", version_text)
                if match:
                    self._claude_version = match.group(1)
                    self.logger.info(
                        f"Detected Claude Code version: {self._claude_version}"
                    )
                    return self._claude_version
            else:
                self.logger.warning(f"Failed to get Claude version: {result.stderr}")

        except FileNotFoundError:
            self.logger.warning("Claude Code command not found in PATH")
        except subprocess.TimeoutExpired:
            self.logger.warning("Claude version check timed out")
        except Exception as e:
            self.logger.warning(f"Error detecting Claude version: {e}")

        return None

    def is_version_compatible(self) -> Tuple[bool, str]:
        """
        Check if the installed Claude Code version meets minimum requirements.

        Returns:
            Tuple of (is_compatible, message)
        """
        version = self.get_claude_version()

        if version is None:
            return (
                False,
                "Could not detect Claude Code version. Hooks require Claude Code to be installed.",
            )

        # Parse version numbers for comparison
        def parse_version(v: str) -> List[int]:
            """Parse semantic version string to list of integers."""
            try:
                return [int(x) for x in v.split(".")]
            except (ValueError, AttributeError):
                return [0]

        current = parse_version(version)
        required = parse_version(self.MIN_CLAUDE_VERSION)

        # Compare versions (semantic versioning)
        for i in range(max(len(current), len(required))):
            curr_part = current[i] if i < len(current) else 0
            req_part = required[i] if i < len(required) else 0

            if curr_part < req_part:
                return (
                    False,
                    f"Claude Code {version} does not support matcher-based hooks. "
                    f"Version {self.MIN_CLAUDE_VERSION} or higher is required for hook monitoring. "
                    f"Please upgrade Claude Code to enable dashboard monitoring features.",
                )
            if curr_part > req_part:
                # Current version is higher, compatible
                break

        return (True, f"Claude Code {version} is compatible with hook monitoring.")

    def supports_pretool_modify(self) -> bool:
        """
        Check if the installed Claude Code version supports PreToolUse input modification.

        PreToolUse input modification was added in Claude Code v2.0.30.

        Returns:
            True if version supports input modification, False otherwise
        """
        version = self.get_claude_version()

        if version is None:
            return False

        def parse_version(v: str) -> List[int]:
            """Parse semantic version string to list of integers."""
            try:
                return [int(x) for x in v.split(".")]
            except (ValueError, AttributeError):
                return [0]

        current = parse_version(version)
        required = parse_version(self.MIN_PRETOOL_MODIFY_VERSION)

        # Compare versions
        for i in range(max(len(current), len(required))):
            curr_part = current[i] if i < len(current) else 0
            req_part = required[i] if i < len(required) else 0

            if curr_part < req_part:
                return False
            if curr_part > req_part:
                return True

        return True

    def get_hook_script_path(self) -> Path:
        """Get the path to the hook handler script based on installation method.

        Returns:
            Path to the claude-hook-handler.sh script

        Raises:
            FileNotFoundError: If the script cannot be found
        """
        if self._hook_script_path and self._hook_script_path.exists():
            return self._hook_script_path

        import claude_mpm

        # Get the claude_mpm package directory
        package_dir = Path(claude_mpm.__file__).parent

        # Check if we're in a development environment (src structure)
        if "src/claude_mpm" in str(package_dir):
            # Development install - script is in src/claude_mpm/scripts
            script_path = package_dir / "scripts" / "claude-hook-handler.sh"
        else:
            # Pip install - script should be in package/scripts
            script_path = package_dir / "scripts" / "claude-hook-handler.sh"

        # Verify the script exists
        if not script_path.exists():
            # Try alternative location for editable installs
            project_root = package_dir.parent.parent
            alt_path = (
                project_root
                / "src"
                / "claude_mpm"
                / "scripts"
                / "claude-hook-handler.sh"
            )
            if alt_path.exists():
                script_path = alt_path
            else:
                raise FileNotFoundError(
                    f"Hook handler script not found. Searched:\n"
                    f"  - {script_path}\n"
                    f"  - {alt_path}"
                )

        # Make sure it's executable
        if script_path.exists():
            st = Path(script_path).stat()
            Path(script_path).chmod(st.st_mode | stat.S_IEXEC)
            self._hook_script_path = script_path
            return script_path

        raise FileNotFoundError(f"Hook handler script not found at {script_path}")

    def install_hooks(self, force: bool = False) -> bool:
        """
        Install Claude MPM hooks.

        Args:
            force: Force reinstallation even if hooks already exist

        Returns:
            True if installation successful, False otherwise
        """
        try:
            self.logger.info("Starting hook installation...")

            # Check Claude Code version compatibility
            is_compatible, version_message = self.is_version_compatible()
            self.logger.info(version_message)

            if not is_compatible:
                self.logger.warning(
                    "Claude Code version is incompatible with hook monitoring. "
                    "Skipping hook installation to avoid configuration errors."
                )
                print(f"\n[Warning] {version_message}")
                print(
                    "Hook-based monitoring features will be disabled. "
                    "The dashboard and other features will still work without real-time monitoring."
                )
                return False

            # Create Claude directory (hooks_dir no longer needed)
            self.claude_dir.mkdir(exist_ok=True)

            # Get the deployment-root hook script path
            try:
                hook_script_path = self.get_hook_script_path()
                self.logger.info(
                    f"Using deployment-root hook script: {hook_script_path}"
                )
            except FileNotFoundError as e:
                self.logger.error(f"Failed to locate hook script: {e}")
                return False

            # Update Claude settings to use deployment-root script
            self._update_claude_settings(hook_script_path)

            # Install commands if available
            self._install_commands()

            # Clean up old deployed scripts if they exist
            self._cleanup_old_deployment()

            self.logger.info("Hook installation completed successfully!")
            return True

        except Exception as e:
            self.logger.error(f"Hook installation failed: {e}")
            return False

    def _cleanup_old_deployment(self) -> None:
        """Clean up old deployed hook scripts if they exist."""
        old_script = self.hooks_dir / "claude-mpm-hook.sh"
        if old_script.exists():
            try:
                old_script.unlink()
                self.logger.info(f"Removed old deployed script: {old_script}")
            except Exception as e:
                self.logger.warning(f"Could not remove old script {old_script}: {e}")

        # Clean up hooks directory if empty
        if self.hooks_dir.exists() and not any(self.hooks_dir.iterdir()):
            try:
                self.hooks_dir.rmdir()
                self.logger.info(f"Removed empty hooks directory: {self.hooks_dir}")
            except Exception as e:
                self.logger.debug(f"Could not remove hooks directory: {e}")

    def _cleanup_old_settings(self) -> None:
        """Remove hooks from old settings.json file if present."""
        # No-op: old_settings_file was pointing to same file as settings_file (bug)
        # This was causing freshly installed hooks to be immediately deleted
        if self.old_settings_file is None or not self.old_settings_file.exists():
            return

        try:
            with self.old_settings_file.open() as f:
                old_settings = json.load(f)

            # Remove hooks section if present
            if "hooks" in old_settings:
                del old_settings["hooks"]
                self.logger.info(f"Removing hooks from {self.old_settings_file}")

                # Write back the cleaned settings
                with self.old_settings_file.open("w") as f:
                    json.dump(old_settings, f, indent=2)

                self.logger.info(f"Cleaned up hooks from {self.old_settings_file}")
        except Exception as e:
            self.logger.warning(f"Could not clean up old settings file: {e}")

    def _update_claude_settings(self, hook_script_path: Path) -> None:
        """Update Claude settings to use the installed hook."""
        self.logger.info("Updating Claude settings...")

        # Load existing settings.json or create new
        if self.settings_file.exists():
            with self.settings_file.open() as f:
                settings = json.load(f)
            self.logger.info(f"Found existing Claude settings at {self.settings_file}")
        else:
            settings = {}
            self.logger.info(f"Creating new Claude settings at {self.settings_file}")

        # Preserve existing permissions and mcpServers if present
        if "permissions" not in settings:
            settings["permissions"] = {"allow": []}
        if "enableAllProjectMcpServers" not in settings:
            settings["enableAllProjectMcpServers"] = False

        # Update hooks section
        if "hooks" not in settings:
            settings["hooks"] = {}

        # Hook configuration for each event type
        hook_command = {"type": "command", "command": str(hook_script_path.absolute())}

        # Tool-related events need a matcher string
        tool_events = ["PreToolUse", "PostToolUse"]
        for event_type in tool_events:
            settings["hooks"][event_type] = [
                {
                    "matcher": "*",  # String value to match all tools
                    "hooks": [hook_command],
                }
            ]

        # Simple events (no subtypes, no matcher needed)
        simple_events = ["Stop", "SubagentStop", "SubagentStart"]
        for event_type in simple_events:
            settings["hooks"][event_type] = [
                {
                    "hooks": [hook_command],
                }
            ]

        # SessionStart needs matcher for subtypes (startup, resume)
        settings["hooks"]["SessionStart"] = [
            {
                "matcher": "*",  # Match all SessionStart subtypes
                "hooks": [hook_command],
            }
        ]

        # UserPromptSubmit needs matcher for potential subtypes
        settings["hooks"]["UserPromptSubmit"] = [
            {
                "matcher": "*",
                "hooks": [hook_command],
            }
        ]

        # Write settings to settings.json
        with self.settings_file.open("w") as f:
            json.dump(settings, f, indent=2)

        self.logger.info(f"Updated Claude settings at {self.settings_file}")

        # Clean up hooks from old settings.json if present
        self._cleanup_old_settings()

    def _install_commands(self) -> None:
        """Install custom commands for Claude Code."""
        # Find commands directory using proper resource resolution
        try:
            from ...core.unified_paths import get_package_resource_path

            commands_src = get_package_resource_path("commands")
        except FileNotFoundError:
            # Fallback to hardcoded path exploration for development
            package_root = Path(__file__).parent.parent.parent.parent
            commands_src = package_root / ".claude" / "commands"

            if not commands_src.exists():
                # Try the actual location in src/claude_mpm/commands
                commands_src = Path(__file__).parent.parent.parent / "commands"

        if not commands_src.exists():
            self.logger.debug(
                "No commands directory found, skipping command installation"
            )
            return

        commands_dst = self.claude_dir / "commands"
        commands_dst.mkdir(exist_ok=True)

        for cmd_file in commands_src.glob("*.md"):
            dst_file = commands_dst / cmd_file.name
            shutil.copy2(cmd_file, dst_file)
            self.logger.info(f"Installed command: {cmd_file.name}")

    def update_hooks(self) -> bool:
        """Update existing hooks to the latest version."""
        return self.install_hooks(force=True)

    def verify_hooks(self) -> Tuple[bool, List[str]]:
        """
        Verify that hooks are properly installed.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check version compatibility first
        is_compatible, version_message = self.is_version_compatible()
        if not is_compatible:
            issues.append(version_message)
            # If version is incompatible, skip other checks as hooks shouldn't be installed
            return False, issues

        # Check hook script exists at deployment root
        try:
            hook_script_path = self.get_hook_script_path()
            if not hook_script_path.exists():
                issues.append(f"Hook script not found at {hook_script_path}")
            # Check hook script is executable
            elif not os.access(hook_script_path, os.X_OK):
                issues.append(f"Hook script is not executable: {hook_script_path}")
        except FileNotFoundError as e:
            issues.append(str(e))

        # Check Claude settings
        if not self.settings_file.exists():
            issues.append(f"Claude settings file not found at {self.settings_file}")
        else:
            try:
                with self.settings_file.open() as f:
                    settings = json.load(f)

                if "hooks" not in settings:
                    issues.append("No hooks configured in Claude settings")
                else:
                    # Check for required event types
                    required_events = [
                        "Stop",
                        "SubagentStop",
                        "SubagentStart",
                        "PreToolUse",
                        "PostToolUse",
                    ]
                    for event in required_events:
                        if event not in settings["hooks"]:
                            issues.append(
                                f"Missing hook configuration for {event} event"
                            )

            except json.JSONDecodeError as e:
                issues.append(f"Invalid Claude settings JSON: {e}")

        # Check if claude-mpm is accessible
        import importlib.util

        if importlib.util.find_spec("claude_mpm") is None:
            issues.append("claude-mpm package not found in Python environment")

        is_valid = len(issues) == 0
        return is_valid, issues

    def uninstall_hooks(self) -> bool:
        """
        Remove Claude MPM hooks.

        Returns:
            True if uninstallation successful, False otherwise
        """
        try:
            self.logger.info("Uninstalling hooks...")

            # Clean up old deployed scripts if they still exist
            old_script = self.hooks_dir / "claude-mpm-hook.sh"
            if old_script.exists():
                old_script.unlink()
                self.logger.info(f"Removed old deployed script: {old_script}")

            # Remove from Claude settings
            settings_paths = [self.settings_file]
            if self.old_settings_file is not None:
                settings_paths.append(self.old_settings_file)

            for settings_path in settings_paths:
                if settings_path and settings_path.exists():
                    with settings_path.open() as f:
                        settings = json.load(f)

                    if "hooks" in settings:
                        # Remove claude-mpm hooks
                        for event_type in list(settings["hooks"].keys()):
                            hooks = settings["hooks"][event_type]
                            # Filter out claude-mpm hooks
                            filtered_hooks = []
                            for h in hooks:
                                # Check if this is a claude-mpm hook
                                is_claude_mpm = False
                                if isinstance(h, dict) and "hooks" in h:
                                    # Check each hook command in the hooks array
                                    for hook_cmd in h.get("hooks", []):
                                        if (
                                            isinstance(hook_cmd, dict)
                                            and hook_cmd.get("type") == "command"
                                        ):
                                            cmd = hook_cmd.get("command", "")
                                            if (
                                                "claude-hook-handler.sh" in cmd
                                                or cmd.endswith("claude-mpm-hook.sh")
                                            ):
                                                is_claude_mpm = True
                                                break

                                if not is_claude_mpm:
                                    filtered_hooks.append(h)

                            if filtered_hooks:
                                settings["hooks"][event_type] = filtered_hooks
                            else:
                                del settings["hooks"][event_type]

                        # Clean up empty hooks section
                        if not settings["hooks"]:
                            del settings["hooks"]

                        # Write back settings
                        with settings_path.open("w") as f:
                            json.dump(settings, f, indent=2)

                        self.logger.info(f"Removed hooks from {settings_path}")

            self.logger.info("Hook uninstallation completed")
            return True

        except Exception as e:
            self.logger.error(f"Hook uninstallation failed: {e}")
            return False

    def get_status(self) -> Dict[str, any]:
        """
        Get the current status of hook installation.

        Returns:
            Dictionary with status information
        """
        # Check version compatibility
        claude_version = self.get_claude_version()
        is_compatible, version_message = self.is_version_compatible()
        pretool_modify_supported = self.supports_pretool_modify()

        is_valid, issues = self.verify_hooks()

        # Try to get deployment-root script path
        try:
            hook_script_path = self.get_hook_script_path()
            hook_script_str = str(hook_script_path)
            script_exists = hook_script_path.exists()
        except FileNotFoundError:
            hook_script_str = None
            script_exists = False

        status = {
            "installed": script_exists and self.settings_file.exists(),
            "valid": is_valid,
            "issues": issues,
            "hook_script": hook_script_str,
            "settings_file": (
                str(self.settings_file) if self.settings_file.exists() else None
            ),
            "claude_version": claude_version,
            "version_compatible": is_compatible,
            "version_message": version_message,
            "deployment_type": "deployment-root",  # New field to indicate new architecture
            "pretool_modify_supported": pretool_modify_supported,  # v2.0.30+ feature
            "pretool_modify_message": (
                f"PreToolUse input modification supported (v{claude_version})"
                if pretool_modify_supported
                else f"PreToolUse input modification requires Claude Code {self.MIN_PRETOOL_MODIFY_VERSION}+ (current: {claude_version or 'unknown'})"
            ),
        }

        # Check Claude settings for hook configuration
        # Check both settings files to understand current state
        configured_in_local = False

        if self.settings_file.exists():
            try:
                with self.settings_file.open() as f:
                    settings = json.load(f)
                    if "hooks" in settings:
                        status["configured_events"] = list(settings["hooks"].keys())
                        configured_in_local = True
            except Exception:
                pass

        # Also check old settings file
        if self.old_settings_file is not None and self.old_settings_file.exists():
            try:
                with self.old_settings_file.open() as f:
                    old_settings = json.load(f)
                    if "hooks" in old_settings:
                        status["old_file_has_hooks"] = True
                        if not configured_in_local:
                            status["warning"] = (
                                "Hooks found in settings.local.json but Claude Code reads from settings.json"
                            )
            except Exception:
                pass

        status["settings_location"] = (
            "settings.json" if configured_in_local else "not configured"
        )

        return status
