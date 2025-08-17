#!/usr/bin/env python3
"""
MCP Configuration Verification Script

This script verifies that MCP configuration is correctly set up for Claude Code,
checking all necessary paths and servers are configured.
"""

import json
import platform
from pathlib import Path
from typing import Any, Dict, Optional


def get_config_path() -> Path:
    """Get the platform-specific configuration path."""
    system = platform.system()
    if system == "Darwin":  # macOS
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    elif system == "Linux":
        return Path.home() / ".config" / "Claude" / "config.json"
    elif system == "Windows":
        return (
            Path.home()
            / "AppData"
            / "Roaming"
            / "Claude"
            / "claude_desktop_config.json"
        )
    else:
        return Path.home() / ".config" / "Claude" / "config.json"


def load_config(path: Path) -> Optional[Dict[str, Any]]:
    """Load and parse configuration file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None


def verify_server(name: str, config: Dict[str, Any]) -> bool:
    """Verify a specific MCP server configuration."""
    required_fields = ["command"]

    for field in required_fields:
        if field not in config:
            print(f"  ❌ Missing required field: {field}")
            return False

    # Check if command exists (basic check)
    command = config.get("command", "")
    if not command:
        print(f"  ❌ Empty command field")
        return False

    # Check working directory if specified
    if "cwd" in config:
        cwd_path = Path(config["cwd"])
        if not cwd_path.exists():
            print(f"  ⚠️  Working directory does not exist: {cwd_path}")
        else:
            print(f"  ✅ Working directory exists: {cwd_path}")

    return True


def main():
    """Main verification routine."""
    print("🔍 MCP Configuration Verification Tool")
    print("=" * 50)

    # Get platform info
    system = platform.system()
    print(f"\n🖥️  Platform: {system}")

    # Get config path
    config_path = get_config_path()
    print(f"📁 Config path: {config_path}")

    # Check if config exists
    if not config_path.exists():
        print(f"\n❌ Configuration file does not exist!")
        print(f"   Expected at: {config_path}")
        return 1

    print(f"✅ Configuration file exists")

    # Check symlink on macOS/Linux
    if system in ["Darwin", "Linux"]:
        symlink_path = Path.home() / ".config" / "Claude" / "config.json"
        if symlink_path.is_symlink():
            target = symlink_path.resolve()
            if target == config_path:
                print(f"✅ Symlink correctly points to config")
            else:
                print(f"⚠️  Symlink points to different file: {target}")
        else:
            if symlink_path.exists():
                print(f"⚠️  ~/.config/Claude/config.json exists but is not a symlink")
            else:
                print(f"ℹ️  No symlink at ~/.config/Claude/config.json")

    # Load configuration
    print(f"\n📋 Loading configuration...")
    config = load_config(config_path)
    if not config:
        return 1

    # Check MCP servers
    servers = config.get("mcpServers", {})
    if not servers:
        print("❌ No MCP servers configured!")
        return 1

    print(f"✅ Found {len(servers)} MCP server(s)")

    # Required servers for full functionality
    required_servers = [
        "claude-mpm-gateway",
        "terminal",
        "mcp-cloud-bridge",
        "mem0ai-memory",
        "context7",
    ]

    print(f"\n📦 Verifying MCP Servers:")
    print("-" * 40)

    all_valid = True
    for server_name in required_servers:
        if server_name in servers:
            print(f"\n✅ {server_name}")
            server_config = servers[server_name]

            # Show basic info
            print(f"  Command: {server_config.get('command', 'N/A')}")
            if "args" in server_config:
                args_str = (
                    " ".join(server_config["args"])
                    if isinstance(server_config["args"], list)
                    else str(server_config["args"])
                )
                if len(args_str) > 60:
                    args_str = args_str[:57] + "..."
                print(f"  Args: {args_str}")

            # Verify configuration
            if not verify_server(server_name, server_config):
                all_valid = False
        else:
            print(f"\n❌ {server_name} - NOT CONFIGURED")
            all_valid = False

    # Check for extra servers
    extra_servers = set(servers.keys()) - set(required_servers)
    if extra_servers:
        print(f"\n📌 Additional servers configured:")
        for server_name in extra_servers:
            print(f"  - {server_name}")

    # Final summary
    print(f"\n{'=' * 50}")
    if all_valid and len(servers) >= len(required_servers):
        print("✅ MCP configuration is complete and valid!")
        print("\n💡 Next steps:")
        print("  1. Restart Claude Code if it's running")
        print("  2. Use the /mcp command to verify servers are available")
        print("  3. The servers should appear in the MCP menu")
        return 0
    else:
        print("⚠️  MCP configuration needs attention")
        if not all_valid:
            print("  - Some required servers are missing or misconfigured")
        print("\n💡 To fix:")
        print("  1. Run: python scripts/register_mcp_gateway.py")
        print("  2. Check the working directories for each server")
        print("  3. Ensure all required projects are cloned")
        return 1


if __name__ == "__main__":
    exit(main())
