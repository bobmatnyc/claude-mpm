#!/usr/bin/env python3
"""
Post-installation message for pipx users.

This script displays helpful information after pipx installation of claude-mpm.
"""

import sys
import subprocess
from pathlib import Path


def check_pipx_installation():
    """Check if this is running in a pipx environment."""
    return "pipx" in sys.executable.lower()


def check_mcp_configured():
    """Check if MCP is already configured."""
    import platform
    
    system = platform.system()
    if system == "Darwin":
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        import os
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            config_path = Path(appdata) / "Claude" / "claude_desktop_config.json"
        else:
            config_path = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else:
        config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    
    if config_path.exists():
        try:
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
            return "claude-mpm-gateway" in config.get("mcpServers", {})
        except:
            pass
    
    return False


def main():
    """Display post-installation message."""
    print()
    print("="*60)
    print("✨ Claude MPM successfully installed via pipx!")
    print("="*60)
    
    # Check if this is a pipx installation
    if check_pipx_installation():
        # Check if MCP is configured
        if not check_mcp_configured():
            print()
            print("📌 IMPORTANT: MCP Gateway Configuration Required")
            print("-" * 40)
            print("To use MCP tools with Claude Code, configure it now:")
            print()
            print("  claude-mpm mcp-pipx-config")
            print()
            print("This will set up the MCP server for Claude Code integration.")
            print()
            print("Or for manual setup, see:")
            print("  https://github.com/Shredmetal/claude-mpm/blob/main/docs/MCP_PIPX_SETUP.md")
            print()
        else:
            print("✅ MCP Gateway appears to be configured")
            print()
    
    print("🚀 Quick Start:")
    print("-" * 40)
    print("  claude-mpm              # Start interactive mode")
    print("  claude-mpm --monitor    # Start with dashboard")
    print("  claude-mpm doctor       # Run diagnostics")
    print()
    print("📚 Documentation:")
    print("  https://github.com/Shredmetal/claude-mpm")
    print()
    print("Enjoy using Claude MPM! 🎉")
    print("="*60)
    print()


if __name__ == "__main__":
    main()