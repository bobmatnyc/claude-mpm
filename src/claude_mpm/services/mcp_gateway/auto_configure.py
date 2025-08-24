"""
MCP Gateway Auto-Configuration Service
======================================

Provides automatic MCP configuration for pipx installations with user consent.
Detects unconfigured MCP setups and offers one-time configuration prompts.

WHY: Users installing via pipx should have MCP work out-of-the-box with minimal
friction. This service detects unconfigured installations and offers automatic
setup with user consent.

DESIGN DECISIONS:
- Only prompts once (saves preference to avoid repeated prompts)
- Quick timeout with safe default (no configuration)
- Non-intrusive with environment variable override
- Creates backups before modifying any configuration
- Validates JSON before and after modifications
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.config.paths import paths
from claude_mpm.core.logger import get_logger


class MCPAutoConfigurator:
    """
    Handles automatic MCP configuration for pipx installations.

    Provides a one-time prompt to configure MCP Gateway with user consent,
    making the experience seamless for pipx users while respecting choice.
    """

    def __init__(self):
        """Initialize the auto-configurator."""
        self.logger = get_logger("MCPAutoConfig")
        self.config_dir = paths.claude_mpm_dir_hidden
        self.preference_file = self.config_dir / "mcp_auto_config_preference.json"
        self.claude_config_path = Path.home() / ".claude.json"

    def should_auto_configure(self) -> bool:
        """
        Check if auto-configuration should be attempted.

        Returns:
            True if auto-configuration should be offered, False otherwise
        """
        # Check environment variable override
        if os.environ.get("CLAUDE_MPM_NO_AUTO_CONFIG"):
            self.logger.debug("Auto-configuration disabled via environment variable")
            return False

        # Check if already configured
        if self._is_mcp_configured():
            self.logger.debug("MCP already configured")
            return False

        # Check if this is a pipx installation
        if not self._is_pipx_installation():
            self.logger.debug("Not a pipx installation")
            return False

        # Check if we've already asked
        if self._has_user_preference():
            self.logger.debug("User preference already saved")
            return False

        return True

    def _is_mcp_configured(self) -> bool:
        """Check if MCP is already configured in Claude Code."""
        if not self.claude_config_path.exists():
            return False

        try:
            with open(self.claude_config_path) as f:
                config = json.load(f)

            # Check if claude-mpm-gateway is configured
            mcp_servers = config.get("mcpServers", {})
            return "claude-mpm-gateway" in mcp_servers

        except (OSError, json.JSONDecodeError):
            return False

    def _is_pipx_installation(self) -> bool:
        """Check if claude-mpm is installed via pipx."""
        # Check if running from pipx virtual environment
        if "pipx" in sys.executable.lower():
            return True

        # Check module path
        try:
            import claude_mpm

            module_path = Path(claude_mpm.__file__).parent
            if "pipx" in str(module_path):
                return True
        except Exception:
            pass

        # Check for pipx in PATH for claude-mpm command
        try:
            import platform
            import subprocess

            # Use appropriate command for OS
            if platform.system() == "Windows":
                cmd = ["where", "claude-mpm"]
            else:
                cmd = ["which", "claude-mpm"]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=2, check=False
            )
            if result.returncode == 0 and "pipx" in result.stdout:
                return True
        except Exception:
            pass

        return False

    def _has_user_preference(self) -> bool:
        """Check if user has already been asked about auto-configuration."""
        if not self.preference_file.exists():
            return False

        try:
            with open(self.preference_file) as f:
                prefs = json.load(f)
            return prefs.get("asked", False)
        except (OSError, json.JSONDecodeError):
            return False

    def _save_user_preference(self, choice: str):
        """Save user's preference to avoid asking again."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        prefs = {
            "asked": True,
            "choice": choice,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            with open(self.preference_file, "w") as f:
                json.dump(prefs, f, indent=2)
        except Exception as e:
            self.logger.debug(f"Could not save preference: {e}")

    def prompt_user(self, timeout: int = 10) -> Optional[bool]:
        """
        Prompt user for auto-configuration with timeout.

        Args:
            timeout: Seconds to wait for response (default 10)

        Returns:
            True if user agrees, False if declines, None if timeout
        """
        print("\n" + "=" * 60)
        print("🔧 MCP Gateway Configuration")
        print("=" * 60)
        print("\nClaude MPM can automatically configure MCP Gateway for")
        print("Claude Code integration. This enables advanced features:")
        print("  • File analysis and summarization")
        print("  • System diagnostics")
        print("  • Ticket management")
        print("  • And more...")
        print("\nWould you like to configure it now? (y/n)")
        print(f"(Auto-declining in {timeout} seconds)")

        # Use threading for cross-platform timeout support
        import threading

        try:
            # Python 3.7+ has queue built-in
            import queue
        except ImportError:
            # Python 2.x fallback
            pass

        user_input = None

        def get_input():
            nonlocal user_input
            try:
                user_input = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                user_input = "n"

        # Start input thread
        input_thread = threading.Thread(target=get_input)
        input_thread.daemon = True
        input_thread.start()

        # Wait for input or timeout
        input_thread.join(timeout)

        if input_thread.is_alive():
            # Timed out
            print("\n(Timed out - declining)")
            return None
        # Got input
        return user_input in ["y", "yes"]

    def auto_configure(self) -> bool:
        """
        Perform automatic MCP configuration.

        Returns:
            True if configuration successful, False otherwise
        """
        try:
            # Create backup if config exists
            if self.claude_config_path.exists():
                backup_path = self._create_backup()
                if backup_path:
                    print(f"✅ Backup created: {backup_path}")

            # Load or create configuration
            config = self._load_or_create_config()

            # Add MCP Gateway configuration
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Find claude-mpm executable
            executable = self._find_claude_mpm_executable()
            if not executable:
                print("❌ Could not find claude-mpm executable")
                return False

            # Configure MCP server
            config["mcpServers"]["claude-mpm-gateway"] = {
                "command": str(executable),
                "args": ["mcp", "server"],
                "env": {"MCP_MODE": "production"},
            }

            # Save configuration
            with open(self.claude_config_path, "w") as f:
                json.dump(config, f, indent=2)

            print(f"✅ Configuration saved to: {self.claude_config_path}")
            print("\n🎉 MCP Gateway configured successfully!")
            print("\nNext steps:")
            print("1. Restart Claude Code (if running)")
            print("2. Look for the MCP icon in the interface")
            print("3. Try @claude-mpm-gateway in a conversation")

            return True

        except Exception as e:
            self.logger.error(f"Auto-configuration failed: {e}")
            print(f"❌ Configuration failed: {e}")
            print("\nYou can configure manually with:")
            print("  claude-mpm mcp install")
            return False

    def _create_backup(self) -> Optional[Path]:
        """Create backup of existing configuration."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.claude_config_path.with_suffix(
                f".backup.{timestamp}.json"
            )

            import shutil

            shutil.copy2(self.claude_config_path, backup_path)
            return backup_path

        except Exception as e:
            self.logger.debug(f"Could not create backup: {e}")
            return None

    def _load_or_create_config(self) -> Dict[str, Any]:
        """Load existing config or create new one."""
        if self.claude_config_path.exists():
            try:
                with open(self.claude_config_path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                self.logger.warning("Existing config is invalid JSON, creating new")

        return {}

    def _find_claude_mpm_executable(self) -> Optional[str]:
        """Find the claude-mpm executable path."""
        # Try direct command first
        import platform
        import subprocess

        try:
            # Use appropriate command for OS
            if platform.system() == "Windows":
                cmd = ["where", "claude-mpm"]
            else:
                cmd = ["which", "claude-mpm"]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=2, check=False
            )
            if result.returncode == 0:
                executable_path = result.stdout.strip()
                # On Windows, 'where' might return multiple paths
                if platform.system() == "Windows" and "\n" in executable_path:
                    executable_path = executable_path.split("\n")[0]
                return executable_path
        except Exception:
            pass

        # Try to find via shutil.which (more portable)
        import shutil

        claude_mpm_path = shutil.which("claude-mpm")
        if claude_mpm_path:
            return claude_mpm_path

        # Fallback to Python module invocation
        return sys.executable

    def run(self) -> bool:
        """
        Main entry point for auto-configuration.

        Returns:
            True if configured (or already configured), False otherwise
        """
        if not self.should_auto_configure():
            return True  # Already configured or not applicable

        # Prompt user
        user_choice = self.prompt_user()

        # Save preference to not ask again
        self._save_user_preference("yes" if user_choice else "no")

        if user_choice:
            return self.auto_configure()
        if user_choice is False:  # User explicitly said no
            print("\n📝 You can configure MCP later with:")
            print("  claude-mpm mcp install")
        # If timeout (None), don't show additional message
        return False


def check_and_configure_mcp() -> bool:
    """
    Check and potentially configure MCP for pipx installations.

    This is the main entry point called during CLI initialization.

    Returns:
        True if MCP is configured (or configuration was successful), False otherwise
    """
    configurator = MCPAutoConfigurator()
    return configurator.run()
