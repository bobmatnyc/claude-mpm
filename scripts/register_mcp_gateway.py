#!/usr/bin/env python3
"""
Safe MCP Gateway Registration Script for claude-mpm

This script safely registers the claude-mpm MCP gateway with Claude Code,
preserving all existing MCP server configurations and creating backups.

NOTE: MCP integration is ONLY for Claude Code - NOT for Claude Desktop.
Claude Desktop uses a different system for agent deployment.

Usage:
    python scripts/register_mcp_gateway.py           # Register claude-mpm in Claude Code
    python scripts/register_mcp_gateway.py --dry-run # Preview changes
    python scripts/register_mcp_gateway.py --remove  # Unregister claude-mpm
"""

import argparse
import json
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class MCPConfigManager:
    """Manages Claude Code MCP configuration safely.
    
    NOTE: MCP is ONLY for Claude Code integration - NOT for Claude Desktop.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the configuration manager.

        Args:
            config_path: Path to Claude Code config (defaults to ~/.claude.json)
        """
        # Platform info
        system = platform.system()
        print(f"🖥️  Detected platform: {system}")
        
        # Claude Code config path (always in home directory)
        self.config_path = config_path if config_path else Path.home() / ".claude.json"
        print(f"📁 Claude Code config: {self.config_path}")

        self.gateway_name = "claude-mpm-gateway"

    def get_gateway_config(self) -> Dict[str, Any]:
        """Get the claude-mpm gateway configuration.

        Returns:
            Dictionary with MCP server configuration for claude-mpm
        """
        return {
            "command": "python",
            "args": ["-m", "claude_mpm.cli", "mcp", "start"],
            "cwd": str(Path.home() / "Projects" / "claude-mpm"),
        }

    def get_backup_dir(self) -> Path:
        """Get the backup directory for Claude Code config.

        Returns:
            Path to the backup directory
        """
        # For Claude Code, create backups in a subdirectory
        return self.config_path.parent / ".claude_backups"

    def load_config(self) -> Dict[str, Any]:
        """Load the current Claude Code configuration.

        Returns:
            Current configuration dictionary or empty structure if not exists
        """
        if not self.config_path.exists():
            print(f"📋 Config file not found at {self.config_path}")
            print("  Creating new configuration structure...")
            # For Claude Code, we need to preserve the projects structure
            return {"projects": {}}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                print(f"✅ Loaded existing config from {self.config_path}")

                # Claude Code has projects with mcpServers inside each project
                # We'll add global mcpServers at the root level if not present
                if "mcpServers" not in config:
                    # Check if there are project-specific servers we should preserve
                    has_project_servers = any(
                        "mcpServers" in proj
                        for proj in config.get("projects", {}).values()
                    )
                    if not has_project_servers:
                        config["mcpServers"] = {}
                        print("  Added missing global 'mcpServers' section")

                return config
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON config: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading config: {e}")
            sys.exit(1)

    def create_backup(self, config: Dict[str, Any]) -> Path:
        """Create a timestamped backup of the current Claude Code configuration.

        Args:
            config: Current configuration to backup

        Returns:
            Path to the backup file
        """
        # Get backup directory
        backup_dir = self.get_backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp-based backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_name = self.config_path.stem
        backup_path = backup_dir / f"{config_name}_{timestamp}.json"

        # Write backup
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        print(f"💾 Created backup at {backup_path}")
        return backup_path

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the configuration structure.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check basic structure
            if not isinstance(config, dict):
                print("❌ Config is not a dictionary")
                return False

            if "mcpServers" not in config:
                print("❌ Missing 'mcpServers' section")
                return False

            if not isinstance(config["mcpServers"], dict):
                print("❌ 'mcpServers' is not a dictionary")
                return False

            # Validate each MCP server configuration
            for name, server_config in config["mcpServers"].items():
                if not isinstance(server_config, dict):
                    print(f"❌ Server '{name}' configuration is not a dictionary")
                    return False

                if "command" not in server_config:
                    print(f"❌ Server '{name}' missing 'command' field")
                    return False

            # Try to serialize to JSON to ensure it's valid
            json.dumps(config)

            print("✅ Configuration validation passed")
            return True

        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            return False

    def register_gateway(self, dry_run: bool = False) -> bool:
        """Register the claude-mpm gateway in Claude Code configuration.

        Args:
            dry_run: If True, only preview changes without applying them

        Returns:
            True if successful, False otherwise
        """
        print(f"\n🚀 Registering claude-mpm MCP gateway for Claude Code...")
        print("\nℹ️  NOTE: MCP is ONLY for Claude Code - NOT for Claude Desktop")
        print("   Claude Desktop uses a different system for agent deployment\n")

        # Load current config
        config = self.load_config()

        # For Claude Code, handle both global and project-specific servers
        # We'll add to global mcpServers
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        servers_section = config["mcpServers"]

        # Check existing servers
        existing_servers = list(servers_section.keys())
        if existing_servers:
            print(f"📦 Existing MCP servers found: {', '.join(existing_servers)}")
        else:
            print("📦 No existing MCP servers found")

        # Check if already registered
        if self.gateway_name in servers_section:
            print(f"\n⚠️  {self.gateway_name} is already registered")
            existing_config = servers_section[self.gateway_name]
            new_config = self.get_gateway_config()

            if existing_config == new_config:
                print("  Configuration is already up to date")
                return True
            else:
                print("  Configuration differs from desired state")
                print("\n  Current configuration:")
                print(f"    {json.dumps(existing_config, indent=4)}")
                print("\n  New configuration:")
                print(f"    {json.dumps(new_config, indent=4)}")

        # Add/update gateway configuration
        updated_config = json.loads(json.dumps(config))  # Deep copy
        updated_config["mcpServers"][self.gateway_name] = self.get_gateway_config()

        # Show what will be added
        print(f"\n➕ Adding {self.gateway_name}")

        if dry_run:
            print("🔍 DRY RUN MODE - No changes made")
            return True

        # Validate before saving
        if not self.validate_config(updated_config):
            print("❌ Configuration validation failed")
            return False

        # Create backup
        self.create_backup(config)

        # Save updated configuration
        try:
            # Ensure parent directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write updated config
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(updated_config, f, indent=2)

            print(f"✅ Successfully registered {self.gateway_name}")
            print(f"  Configuration saved to {self.config_path}")

            # Show final server list
            final_servers = list(updated_config["mcpServers"].keys())
            print(f"  📦 MCP servers now registered: {', '.join(final_servers)}")
            
            print("\n💪 Next steps:")
            print("  1. Restart Claude Code if it's running")
            print("  2. Use the /mcp command to verify servers are available")
            print("  3. The MCP gateway should appear in the MCP menu")

        except Exception as e:
            print(f"❌ Failed to save configuration: {e}")
            return False

        return True

    def unregister_gateway(self, dry_run: bool = False) -> bool:
        """Remove the claude-mpm gateway from Claude Code configuration.

        Args:
            dry_run: If True, only preview changes without applying them

        Returns:
            True if successful, False otherwise
        """
        print(f"\n🗑️  Unregistering {self.gateway_name} from Claude Code...")

        # Load current config
        config = self.load_config()
        servers_section = config.get("mcpServers", {})

        # Check if registered
        if self.gateway_name not in servers_section:
            print(f"{self.gateway_name} is not registered")
            return True

        # Create updated config without gateway
        updated_config = json.loads(json.dumps(config))  # Deep copy
        if "mcpServers" in updated_config:
            del updated_config["mcpServers"][self.gateway_name]

        print(f"Removing {self.gateway_name} from configuration")

        if dry_run:
            print("🔍 DRY RUN MODE - No changes made")
            return True

        # Validate before saving
        if not self.validate_config(updated_config):
            print("❌ Configuration validation failed")
            return False

        # Create backup
        self.create_backup(config)

        # Save updated configuration
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(updated_config, f, indent=2)

            print(f"✅ Successfully unregistered {self.gateway_name}")

            # Show remaining servers
            remaining_servers = list(updated_config.get("mcpServers", {}).keys())
            if remaining_servers:
                print(f"📦 Remaining MCP servers: {', '.join(remaining_servers)}")
            else:
                print("📦 No MCP servers registered")

        except Exception as e:
            print(f"❌ Failed to save configuration: {e}")
            return False

        return True

    def show_status(self):
        """Display current MCP server registration status for Claude Code."""
        print("\n📊 MCP Server Registration Status for Claude Code")
        print("=" * 50)
        print(f"\nConfig file: {self.config_path}")
        print("-" * 40)

        if not self.config_path.exists():
            print("⚠️  Config file not found")
            print("\n💪 To fix: Run this script without --status to register the MCP gateway")
            return

        config = self.load_config()
        servers = config.get("mcpServers", {})

        if not servers:
            print("No MCP servers registered")
            print("\n💪 To fix: Run this script without --status to register the MCP gateway")
            return

        print(f"\nRegistered MCP servers ({len(servers)} total):\n")
        for name, server_config in servers.items():
            status = "✅" if name == self.gateway_name else "📦"
            print(f"{status} {name}")
            print(f"   Command: {server_config.get('command', 'N/A')}")
            if "args" in server_config:
                args_str = ' '.join(server_config['args']) if isinstance(server_config['args'], list) else str(server_config['args'])
                if len(args_str) > 60:
                    args_str = args_str[:57] + "..."
                print(f"   Args: {args_str}")
            if "cwd" in server_config:
                print(f"   Working Dir: {server_config['cwd']}")
            print()


def main():
    """Main entry point for the registration script."""
    parser = argparse.ArgumentParser(
        description="Safely register claude-mpm MCP gateway with Claude Code\n\n"
                    "NOTE: MCP is ONLY for Claude Code - NOT for Claude Desktop.\n"
                    "Claude Desktop uses a different system for agent deployment.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    parser.add_argument(
        "--remove", action="store_true", help="Unregister claude-mpm gateway"
    )
    parser.add_argument(
        "--status", action="store_true", help="Show current registration status"
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        help="Custom path to Claude Code config file (default: ~/.claude.json)",
    )

    args = parser.parse_args()

    # Initialize manager for Claude Code only
    manager = MCPConfigManager(args.config_path)

    # Execute requested action
    if args.status:
        manager.show_status()
    elif args.remove:
        success = manager.unregister_gateway(args.dry_run)
        sys.exit(0 if success else 1)
    else:
        success = manager.register_gateway(args.dry_run)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
