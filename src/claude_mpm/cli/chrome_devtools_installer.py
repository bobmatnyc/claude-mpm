"""
Chrome DevTools MCP Auto-Installer
===================================

Automatically installs and configures chrome-devtools-mcp on startup
to enable browser automation and web interaction capabilities in Claude Code.

WHY: Users should have browser automation capabilities out-of-the-box without
manual MCP server configuration.

DESIGN DECISION: Non-blocking installation that doesn't prevent startup if it fails.
Uses the `claude mcp add` command for native Claude Code integration.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from ..core.logger import get_logger


class ChromeDevToolsInstaller:
    """Manages automatic installation of chrome-devtools-mcp."""

    MCP_SERVER_NAME = "chrome-devtools"
    INSTALL_COMMAND = ["npx", "chrome-devtools-mcp@latest"]

    def __init__(self):
        """Initialize the chrome-devtools installer."""
        self.logger = get_logger(__name__)
        self.claude_config_path = Path.home() / ".claude.json"

    def is_already_configured(self) -> bool:
        """
        Check if chrome-devtools-mcp is already configured in Claude.

        Returns:
            True if already configured, False otherwise
        """
        try:
            if not self.claude_config_path.exists():
                self.logger.debug("Claude config file not found")
                return False

            with open(self.claude_config_path) as f:
                config = json.load(f)

            # Check if chrome-devtools is in mcpServers
            mcp_servers = config.get("mcpServers", {})
            is_configured = self.MCP_SERVER_NAME in mcp_servers

            if is_configured:
                self.logger.debug(
                    f"{self.MCP_SERVER_NAME} already configured in Claude"
                )
            else:
                self.logger.debug(f"{self.MCP_SERVER_NAME} not found in Claude config")

            return is_configured

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse Claude config: {e}")
            return False
        except Exception as e:
            self.logger.debug(f"Error checking Chrome DevTools configuration: {e}")
            return False

    def install_mcp_server(self) -> Tuple[bool, Optional[str]]:
        """
        Install chrome-devtools-mcp using the claude CLI.

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Build the command: claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest
            command = [
                "claude",
                "mcp",
                "add",
                self.MCP_SERVER_NAME,
                "--",
            ] + self.INSTALL_COMMAND

            self.logger.debug(f"Running: {' '.join(command)}")

            # Run the command with timeout
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                check=False,
            )

            if result.returncode == 0:
                self.logger.info(
                    f"Successfully installed {self.MCP_SERVER_NAME} MCP server"
                )
                return True, None

            # Command failed
            error_msg = (
                f"Failed to install {self.MCP_SERVER_NAME}: {result.stderr.strip()}"
            )
            self.logger.warning(error_msg)
            return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = (
                f"Installation of {self.MCP_SERVER_NAME} timed out after 30 seconds"
            )
            self.logger.warning(error_msg)
            return False, error_msg

        except FileNotFoundError:
            error_msg = "Claude CLI not found. Is Claude Code installed?"
            self.logger.warning(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error installing {self.MCP_SERVER_NAME}: {e}"
            self.logger.warning(error_msg)
            return False, error_msg

    def auto_install(self, quiet: bool = False) -> bool:
        """
        Automatically install chrome-devtools-mcp if not already configured.

        Args:
            quiet: If True, suppress console output

        Returns:
            True if installation succeeded or already configured, False otherwise
        """
        # Check if already configured
        if self.is_already_configured():
            if not quiet:
                print("✓ Chrome DevTools MCP ready", flush=True)
            return True

        # Show progress feedback
        if not quiet:
            print("Installing Chrome DevTools MCP...", end=" ", flush=True)

        # Install the MCP server
        success, error = self.install_mcp_server()

        if success:
            if not quiet:
                print("✓", flush=True)
            return True

        # Installation failed
        if not quiet:
            print("(skipped)", flush=True)

        # Log the error but don't fail startup
        self.logger.debug(f"Chrome DevTools installation skipped: {error}")
        return False


def auto_install_chrome_devtools(quiet: bool = False) -> bool:
    """
    Convenience function to auto-install chrome-devtools-mcp.

    Args:
        quiet: If True, suppress console output

    Returns:
        True if installation succeeded or already configured, False otherwise
    """
    installer = ChromeDevToolsInstaller()
    return installer.auto_install(quiet=quiet)
