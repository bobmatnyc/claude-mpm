#!/usr/bin/env python3
"""
MCP configuration command for pipx installations.

This module provides a CLI command to configure MCP for users who installed
claude-mpm via pipx.
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


def find_claude_config_path() -> Path:
    """Find the Claude Code configuration file path."""
    system = platform.system()

    if system == "Darwin":  # macOS
        config_path = (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            config_path = Path(appdata) / "Claude" / "claude_desktop_config.json"
        else:
            config_path = (
                Path.home()
                / "AppData"
                / "Roaming"
                / "Claude"
                / "claude_desktop_config.json"
            )
    else:  # Linux and others
        config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    return config_path


def check_pipx_installation() -> bool:
    """Check if claude-mpm is installed via pipx."""
    try:
        # Check if running from pipx
        if "pipx" in sys.executable.lower():
            return True

        # Check pipx list
        result = subprocess.run(
            ["pipx", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            pipx_data = json.loads(result.stdout)
            return "claude-mpm" in pipx_data.get("venvs", {})
    except Exception:
        pass

    return False


def create_mcp_config() -> Dict[str, Any]:
    """Create MCP configuration for pipx installation."""
    return {"mcpServers": {"claude-mpm-gateway": {"command": "claude-mpm-mcp"}}}


def configure_mcp_for_pipx(args) -> int:
    """
    Configure MCP for pipx installation.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("Claude MPM - MCP Configuration for pipx")
    print("=" * 40)

    # Check if this is a pipx installation
    if not check_pipx_installation():
        print("\n⚠️  This doesn't appear to be a pipx installation")
        print("This command is specifically for pipx users.")
        print("\nFor other installation methods, see:")
        print("  docs/MCP_SETUP.md")

        if not args.force:
            return 1
        print("\n--force flag detected, continuing anyway...")

    # Find Claude config
    config_path = find_claude_config_path()
    print(f"\n📁 Claude config path: {config_path}")

    # Load existing config
    existing_config = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                existing_config = json.load(f)
            print("✅ Existing config loaded")
        except json.JSONDecodeError:
            print("⚠️  Config exists but is invalid JSON")
            if not args.force:
                print("Use --force to overwrite")
                return 1
    else:
        print("📝 Config will be created")
        config_path.parent.mkdir(parents=True, exist_ok=True)

    # Check for existing MCP config
    if (
        "mcpServers" in existing_config
        and "claude-mpm-gateway" in existing_config["mcpServers"]
    ):
        print("\n⚠️  claude-mpm-gateway is already configured")
        if not args.force:
            print("Use --force to overwrite")
            return 0
        print("Overwriting existing configuration...")

    # Create and merge config
    mcp_config = create_mcp_config()
    existing_config.update(mcp_config)

    # Show what will be written
    if not args.quiet:
        print("\n📝 Configuration to write:")
        print(json.dumps(mcp_config, indent=2))

    # Write config
    if not args.dry_run:
        try:
            with open(config_path, "w") as f:
                json.dump(existing_config, f, indent=2)
            print(f"\n✅ Configuration written to: {config_path}")
        except Exception as e:
            print(f"\n❌ Failed to write config: {e}")
            return 1
    else:
        print("\n--dry-run: Configuration not written")

    # Test the command
    print("\n🧪 Testing claude-mpm-mcp command...")
    try:
        result = subprocess.run(
            ["which", "claude-mpm-mcp"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            print(f"✅ Command found: {result.stdout.strip()}")
        else:
            print("⚠️  Command not found in PATH")
            print("   Ensure pipx bin directory is in your PATH")
    except Exception as e:
        print(f"⚠️  Could not test command: {e}")

    print("\n✨ Next steps:")
    print("1. Restart Claude Code")
    print("2. Look for the MCP icon in the interface")
    print("3. Try using @claude-mpm-gateway in a conversation")
    print("\nFor more help, see: docs/MCP_PIPX_SETUP.md")

    return 0


def add_parser(subparsers):
    """Add the mcp-pipx-config command parser."""
    parser = subparsers.add_parser(
        "mcp-pipx-config",
        help="Configure MCP for pipx installation",
        description="Configure MCP Gateway for Claude Code when installed via pipx",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force configuration even if not pipx or already configured",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--quiet", action="store_true", help="Suppress non-essential output"
    )

    parser.set_defaults(func=configure_mcp_for_pipx)
