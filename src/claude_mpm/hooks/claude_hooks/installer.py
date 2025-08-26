"""
Hook installer for Claude MPM integration with Claude Code.

This module provides functionality to install, update, and manage
claude-mpm hooks in the Claude Code environment.
"""

import json
import os
import shutil
import stat
from pathlib import Path
from typing import Dict, List, Tuple

from ...core.logger import get_logger


class HookInstaller:
    """Manages installation and configuration of Claude MPM hooks."""

    # Smart hook script template
    SMART_HOOK_SCRIPT = """#!/bin/bash
# Claude MPM Smart Hook Handler
# This script dynamically finds and routes hook events to claude-mpm
# Works with pip installations, local development, and virtual environments

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
        local base_dir=$(python3 -c "import claude_mpm; import os; print(os.path.dirname(os.path.dirname(claude_mpm.__file__)))" 2>/dev/null)
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
    pkg_dir = os.path.dirname(claude_mpm.__file__)
    # Check if we're in a development install (src directory)
    if 'src' in pkg_dir:
        # Go up to find the project root
        parts = pkg_dir.split(os.sep)
        if 'src' in parts:
            src_idx = parts.index('src')
            project_root = os.sep.join(parts[:src_idx])
            print(project_root)
        else:
            print(os.path.dirname(os.path.dirname(pkg_dir)))
    else:
        # Installed package - just return the package location
        print(os.path.dirname(pkg_dir))
except:
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
            local pkg_dir=$(cd "$path_dir" && python3 -c "import claude_mpm; import os; print(os.path.dirname(os.path.dirname(claude_mpm.__file__)))" 2>/dev/null)
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

    def __init__(self):
        """Initialize the hook installer."""
        self.logger = get_logger(__name__)
        self.claude_dir = Path.home() / ".claude"
        self.hooks_dir = self.claude_dir / "hooks"
        self.settings_file = self.claude_dir / "settings.json"

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

            # Create directories
            self.claude_dir.mkdir(exist_ok=True)
            self.hooks_dir.mkdir(exist_ok=True)

            # Install smart hook script
            hook_script_path = self.hooks_dir / "claude-mpm-hook.sh"
            if hook_script_path.exists() and not force:
                self.logger.info(
                    "Hook script already exists. Use --force to overwrite."
                )
            else:
                self._install_smart_hook_script(hook_script_path)

            # Update Claude settings
            self._update_claude_settings(hook_script_path)

            # Install commands if available
            self._install_commands()

            self.logger.info("Hook installation completed successfully!")
            return True

        except Exception as e:
            self.logger.error(f"Hook installation failed: {e}")
            return False

    def _install_smart_hook_script(self, hook_script_path: Path) -> None:
        """Install the smart hook script that dynamically finds claude-mpm."""
        self.logger.info(f"Installing smart hook script to {hook_script_path}")

        # Write the smart hook script
        with open(hook_script_path, "w") as f:
            f.write(self.SMART_HOOK_SCRIPT)

        # Make it executable
        st = os.stat(hook_script_path)
        os.chmod(hook_script_path, st.st_mode | stat.S_IEXEC)

        self.logger.info("Smart hook script installed and made executable")

    def _update_claude_settings(self, hook_script_path: Path) -> None:
        """Update Claude settings to use the installed hook."""
        self.logger.info("Updating Claude settings...")

        # Load existing settings or create new
        if self.settings_file.exists():
            with open(self.settings_file) as f:
                settings = json.load(f)
            self.logger.info("Found existing Claude settings")
        else:
            settings = {}
            self.logger.info("Creating new Claude settings")

        # Configure hooks
        hook_config = {
            "matcher": "*",
            "hooks": [{"type": "command", "command": str(hook_script_path.absolute())}],
        }

        # Update settings
        if "hooks" not in settings:
            settings["hooks"] = {}

        # Add hooks for all event types
        event_types = [
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
            "Stop",
            "SubagentStop",
        ]

        for event_type in event_types:
            settings["hooks"][event_type] = [hook_config]

        # Write settings
        with open(self.settings_file, "w") as f:
            json.dump(settings, f, indent=2)

        self.logger.info(f"Updated Claude settings at {self.settings_file}")

    def _install_commands(self) -> None:
        """Install custom commands for Claude Code."""
        # Find commands directory in the package
        package_root = Path(__file__).parent.parent.parent.parent
        commands_src = package_root / ".claude" / "commands"

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

        # Check hook script exists
        hook_script_path = self.hooks_dir / "claude-mpm-hook.sh"
        if not hook_script_path.exists():
            issues.append(f"Hook script not found at {hook_script_path}")

        # Check hook script is executable
        elif not os.access(hook_script_path, os.X_OK):
            issues.append(f"Hook script is not executable: {hook_script_path}")

        # Check Claude settings
        if not self.settings_file.exists():
            issues.append(f"Claude settings file not found at {self.settings_file}")
        else:
            try:
                with open(self.settings_file) as f:
                    settings = json.load(f)

                if "hooks" not in settings:
                    issues.append("No hooks configured in Claude settings")
                else:
                    # Check for required event types
                    required_events = ["Stop", "SubagentStop"]
                    for event in required_events:
                        if event not in settings["hooks"]:
                            issues.append(
                                f"Missing hook configuration for {event} event"
                            )

            except json.JSONDecodeError as e:
                issues.append(f"Invalid Claude settings JSON: {e}")

        # Check if claude-mpm is accessible
        try:
            import claude_mpm
        except ImportError:
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

            # Remove hook script
            hook_script_path = self.hooks_dir / "claude-mpm-hook.sh"
            if hook_script_path.exists():
                hook_script_path.unlink()
                self.logger.info(f"Removed hook script: {hook_script_path}")

            # Remove from Claude settings
            if self.settings_file.exists():
                with open(self.settings_file) as f:
                    settings = json.load(f)

                if "hooks" in settings:
                    # Remove claude-mpm hooks
                    for event_type in list(settings["hooks"].keys()):
                        hooks = settings["hooks"][event_type]
                        # Filter out claude-mpm hooks
                        filtered_hooks = [
                            h
                            for h in hooks
                            if not (
                                isinstance(h, dict)
                                and h.get("hooks", [{}])[0]
                                .get("command", "")
                                .endswith("claude-mpm-hook.sh")
                            )
                        ]

                        if filtered_hooks:
                            settings["hooks"][event_type] = filtered_hooks
                        else:
                            del settings["hooks"][event_type]

                    # Clean up empty hooks section
                    if not settings["hooks"]:
                        del settings["hooks"]

                    # Write back settings
                    with open(self.settings_file, "w") as f:
                        json.dump(settings, f, indent=2)

                    self.logger.info("Removed hooks from Claude settings")

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
        is_valid, issues = self.verify_hooks()

        hook_script_path = self.hooks_dir / "claude-mpm-hook.sh"

        status = {
            "installed": hook_script_path.exists(),
            "valid": is_valid,
            "issues": issues,
            "hook_script": str(hook_script_path) if hook_script_path.exists() else None,
            "settings_file": (
                str(self.settings_file) if self.settings_file.exists() else None
            ),
        }

        # Check Claude settings for hook configuration
        if self.settings_file.exists():
            try:
                with open(self.settings_file) as f:
                    settings = json.load(f)
                    if "hooks" in settings:
                        status["configured_events"] = list(settings["hooks"].keys())
            except:
                pass

        return status
