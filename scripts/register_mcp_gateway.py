#!/usr/bin/env python3
"""
Safe MCP Gateway Registration Script for claude-mpm

This script safely registers the claude-mpm MCP gateway with both Claude Desktop
and Claude Code, preserving all existing MCP server configurations and creating backups.

Usage:
    python scripts/register_mcp_gateway.py           # Register claude-mpm in both apps
    python scripts/register_mcp_gateway.py --dry-run # Preview changes
    python scripts/register_mcp_gateway.py --remove  # Unregister claude-mpm
    python scripts/register_mcp_gateway.py --desktop-only  # Only configure Claude Desktop
    python scripts/register_mcp_gateway.py --code-only     # Only configure Claude Code
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
    """Manages Claude Desktop and Claude Code MCP configuration safely."""

    def __init__(self, config_path: Optional[Path] = None, app_type: str = "both"):
        """Initialize the configuration manager.

        Args:
            config_path: Path to config (defaults to platform-specific location)
            app_type: "desktop", "code", or "both" to specify which app(s) to configure
        """
        self.app_type = app_type
        self.configs = {}

        # Platform-specific configuration paths
        system = platform.system()

        # Claude Desktop config path
        if app_type in ["desktop", "both"]:
            if config_path and app_type == "desktop":
                self.configs["desktop"] = config_path
            else:
                if system == "Darwin":  # macOS
                    self.configs["desktop"] = (
                        Path.home()
                        / "Library"
                        / "Application Support"
                        / "Claude"
                        / "claude_desktop_config.json"
                    )
                elif system == "Linux":
                    self.configs["desktop"] = (
                        Path.home() / ".config" / "Claude" / "config.json"
                    )
                elif system == "Windows":
                    self.configs["desktop"] = (
                        Path.home()
                        / "AppData"
                        / "Roaming"
                        / "Claude"
                        / "claude_desktop_config.json"
                    )
                else:
                    self.configs["desktop"] = (
                        Path.home() / ".config" / "Claude" / "config.json"
                    )

        # Claude Code config path (always in home directory)
        if app_type in ["code", "both"]:
            if config_path and app_type == "code":
                self.configs["code"] = config_path
            else:
                self.configs["code"] = Path.home() / ".claude.json"

        print(f"🖥️  Detected platform: {system}")
        for app_name, path in self.configs.items():
            print(f"📁 {app_name.capitalize()} config: {path}")

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

    def get_backup_dir(self, config_path: Path) -> Path:
        """Get the backup directory for a config path.

        Args:
            config_path: The configuration file path

        Returns:
            Path to the backup directory
        """
        if config_path.name == ".claude.json":
            # For Claude Code, create backups in a subdirectory
            return config_path.parent / ".claude_backups"
        else:
            # For Claude Desktop, use parent/backups
            return config_path.parent / "backups"

    def load_config(self, config_path: Path = None) -> Dict[str, Any]:
        """Load the current configuration.

        Args:
            config_path: Optional specific config path to load

        Returns:
            Current configuration dictionary or empty structure if not exists
        """
        # Use provided path or first available config
        if not config_path:
            if self.configs:
                config_path = list(self.configs.values())[0]
            else:
                raise ValueError("No config path available")

        if not config_path.exists():
            print(f"📋 Config file not found at {config_path}")
            print("  Creating new configuration structure...")

            # For Claude Code, we need to preserve the projects structure
            if config_path.name == ".claude.json":
                return {"projects": {}}
            else:
                return {"mcpServers": {}}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                print(f"✅ Loaded existing config from {config_path}")

                # Handle different config structures
                if config_path.name == ".claude.json":
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
                else:
                    # Claude Desktop structure
                    if "mcpServers" not in config:
                        config["mcpServers"] = {}
                        print("  Added missing 'mcpServers' section")

                return config
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON config: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading config: {e}")
            sys.exit(1)

    def create_backup(self, config: Dict[str, Any], config_path: Path) -> Path:
        """Create a timestamped backup of the current configuration.

        Args:
            config: Current configuration to backup
            config_path: Path to the config file being backed up

        Returns:
            Path to the backup file
        """
        # Get backup directory based on config type
        backup_dir = self.get_backup_dir(config_path)
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp-based backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_name = config_path.stem
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
        """Register the claude-mpm gateway in the configuration(s).

        Args:
            dry_run: If True, only preview changes without applying them

        Returns:
            True if successful, False otherwise
        """
        print(f"\n🚀 Registering claude-mpm MCP gateway...")

        all_success = True

        for app_name, config_path in self.configs.items():
            print(f"\n--- Configuring {app_name.capitalize()} ---")

            # Load current config
            config = self.load_config(config_path)

            # Determine where mcpServers should be
            if config_path.name == ".claude.json":
                # For Claude Code, handle both global and project-specific servers
                # We'll add to global mcpServers
                if "mcpServers" not in config:
                    config["mcpServers"] = {}
                servers_section = config["mcpServers"]
            else:
                # For Claude Desktop
                servers_section = config.get("mcpServers", {})

            # Check existing servers
            existing_servers = list(servers_section.keys())
            if existing_servers:
                print(f"  📦 Existing MCP servers found: {', '.join(existing_servers)}")
            else:
                print("  📦 No existing MCP servers found")

            # Check if already registered
            if self.gateway_name in servers_section:
                print(f"  ⚠️  {self.gateway_name} is already registered")
                existing_config = servers_section[self.gateway_name]
                new_config = self.get_gateway_config()

                if existing_config == new_config:
                    print("    Configuration is already up to date")
                    continue
                else:
                    print("    Configuration differs from desired state")
                    print("\n    Current configuration:")
                    print(f"      {json.dumps(existing_config, indent=6)}")
                    print("\n    New configuration:")
                    print(f"      {json.dumps(new_config, indent=6)}")

            # Add/update gateway configuration
            updated_config = json.loads(json.dumps(config))  # Deep copy
            if config_path.name == ".claude.json":
                updated_config["mcpServers"][
                    self.gateway_name
                ] = self.get_gateway_config()
            else:
                updated_config["mcpServers"][
                    self.gateway_name
                ] = self.get_gateway_config()

            # Show what will be added
            print(f"  ➕ Adding {self.gateway_name}")

            if dry_run:
                print("  🔍 DRY RUN MODE - No changes made")
                continue

            # Validate before saving
            if not self.validate_config(updated_config):
                print("  ❌ Configuration validation failed, skipping")
                all_success = False
                continue

            # Create backup
            self.create_backup(config, config_path)

            # Save updated configuration
            try:
                # Ensure parent directory exists
                config_path.parent.mkdir(parents=True, exist_ok=True)

                # Write updated config
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(updated_config, f, indent=2)

                print(f"  ✅ Successfully registered {self.gateway_name}")
                print(f"    Configuration saved to {config_path}")

                # Show final server list
                if config_path.name == ".claude.json":
                    final_servers = list(updated_config["mcpServers"].keys())
                else:
                    final_servers = list(updated_config["mcpServers"].keys())
                print(f"    📦 MCP servers now registered: {', '.join(final_servers)}")

            except Exception as e:
                print(f"  ❌ Failed to save configuration: {e}")
                all_success = False

        return all_success

    def unregister_gateway(self, dry_run: bool = False) -> bool:
        """Remove the claude-mpm gateway from the configuration(s).

        Args:
            dry_run: If True, only preview changes without applying them

        Returns:
            True if successful, False otherwise
        """
        print(f"\n🗑️  Unregistering {self.gateway_name}...")

        all_success = True

        for app_name, config_path in self.configs.items():
            print(f"\n--- Configuring {app_name.capitalize()} ---")

            # Load current config
            config = self.load_config(config_path)

            # Determine where mcpServers are
            if config_path.name == ".claude.json":
                servers_section = config.get("mcpServers", {})
            else:
                servers_section = config.get("mcpServers", {})

            # Check if registered
            if self.gateway_name not in servers_section:
                print(f"  {self.gateway_name} is not registered")
                continue

            # Create updated config without gateway
            updated_config = json.loads(json.dumps(config))  # Deep copy
            if config_path.name == ".claude.json" and "mcpServers" in updated_config:
                del updated_config["mcpServers"][self.gateway_name]
            elif "mcpServers" in updated_config:
                del updated_config["mcpServers"][self.gateway_name]

            print(f"  Removing {self.gateway_name} from configuration")

            if dry_run:
                print("  🔍 DRY RUN MODE - No changes made")
                continue

            # Validate before saving
            if not self.validate_config(updated_config):
                print("  ❌ Configuration validation failed, skipping")
                all_success = False
                continue

            # Create backup
            self.create_backup(config, config_path)

            # Save updated configuration
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(updated_config, f, indent=2)

                print(f"  ✅ Successfully unregistered {self.gateway_name}")

                # Show remaining servers
                if config_path.name == ".claude.json":
                    remaining_servers = list(
                        updated_config.get("mcpServers", {}).keys()
                    )
                else:
                    remaining_servers = list(updated_config["mcpServers"].keys())

                if remaining_servers:
                    print(f"  📦 Remaining MCP servers: {', '.join(remaining_servers)}")
                else:
                    print("  📦 No MCP servers registered")

            except Exception as e:
                print(f"  ❌ Failed to save configuration: {e}")
                all_success = False

        return all_success

    def show_status(self):
        """Display current MCP server registration status."""
        print("\n📊 MCP Server Registration Status")
        print("=" * 50)

        for app_name, config_path in self.configs.items():
            print(f"\n{app_name.capitalize()} ({config_path}):")
            print("-" * 40)

            if not config_path.exists():
                print("  ⚠️  Config file not found")
                continue

            config = self.load_config(config_path)

            # Get servers based on config type
            if config_path.name == ".claude.json":
                servers = config.get("mcpServers", {})
            else:
                servers = config.get("mcpServers", {})

            if not servers:
                print("  No MCP servers registered")
                continue

            for name, server_config in servers.items():
                status = "  ✅" if name == self.gateway_name else "  📦"
                print(f"\n{status} {name}")
                print(f"    Command: {server_config.get('command', 'N/A')}")
                if "args" in server_config:
                    print(f"    Args: {' '.join(server_config['args'])}")
                if "cwd" in server_config:
                    print(f"    Working Dir: {server_config['cwd']}")


def main():
    """Main entry point for the registration script."""
    parser = argparse.ArgumentParser(
        description="Safely register claude-mpm MCP gateway with Claude Desktop and Claude Code"
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
        help="Custom path to config file (use with --desktop-only or --code-only)",
    )
    parser.add_argument(
        "--desktop-only", action="store_true", help="Only configure Claude Desktop"
    )
    parser.add_argument(
        "--code-only", action="store_true", help="Only configure Claude Code"
    )

    args = parser.parse_args()

    # Determine app type
    if args.desktop_only:
        app_type = "desktop"
    elif args.code_only:
        app_type = "code"
    else:
        app_type = "both"

    # Initialize manager
    manager = MCPConfigManager(args.config_path, app_type)

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
