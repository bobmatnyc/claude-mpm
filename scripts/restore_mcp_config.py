#!/usr/bin/env python3
"""
MCP Configuration Restoration Script

This script restores Claude Desktop and Claude Code MCP configurations from backup files,
intelligently merging configurations from multiple sources.

Usage:
    python scripts/restore_mcp_config.py                     # Interactive restore
    python scripts/restore_mcp_config.py --list             # List available backups
    python scripts/restore_mcp_config.py --from backup.json # Restore specific backup
    python scripts/restore_mcp_config.py --merge            # Merge all backups
    python scripts/restore_mcp_config.py --desktop-only     # Only restore Claude Desktop
    python scripts/restore_mcp_config.py --code-only        # Only restore Claude Code
"""

import argparse
import json
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class MCPConfigRestorer:
    """Manages restoration of Claude Desktop and Claude Code MCP configurations."""

    def __init__(self, config_path: Optional[Path] = None, app_type: str = "both"):
        """Initialize the restoration manager.

        Args:
            config_path: Path to config (defaults to platform-specific location)
            app_type: "desktop", "code", or "both" to specify which app(s) to restore
        """
        self.app_type = app_type
        self.configs = {}
        self.backup_locations = []

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

            # Add desktop backup locations
            self.backup_locations.append(self.configs["desktop"].parent / "backups")

        # Claude Code config path (always in home directory)
        if app_type in ["code", "both"]:
            if config_path and app_type == "code":
                self.configs["code"] = config_path
            else:
                self.configs["code"] = Path.home() / ".claude.json"

            # Add Claude Code backup locations
            self.backup_locations.extend(
                [
                    Path.home() / ".claude_backups",
                    Path.home(),  # Look for .claude.json.backup* files
                ]
            )

        print(f"🖥️  Detected platform: {system}")
        for app_name, path in self.configs.items():
            print(f"📁 {app_name.capitalize()} config: {path}")

        # Add platform-specific backup locations
        if system == "Darwin":  # macOS
            self.backup_locations.extend(
                [
                    Path.home()
                    / "Library"
                    / "Application Support"
                    / "Claude"
                    / "backups",
                    Path.home() / ".config" / "Claude" / "config.json.backup",
                    Path.home()
                    / ".config"
                    / "claude-desktop"
                    / "claude_desktop_config.json.backup",
                ]
            )
        elif system == "Linux":
            self.backup_locations.extend(
                [
                    Path.home()
                    / ".config"
                    / "claude-desktop"
                    / "claude_desktop_config.json.backup",
                    Path.home() / ".config" / "Claude" / "config.json.backup",
                ]
            )
        elif system == "Windows":
            self.backup_locations.extend(
                [
                    Path.home() / "AppData" / "Roaming" / "Claude" / "backups",
                    Path.home() / ".config" / "Claude" / "config.json.backup",
                ]
            )

        # Legacy locations
        self.backup_locations.append(Path.home() / ".config" / "claude-desktop")

    def find_backups(self) -> List[Tuple[Path, Dict[str, Any]]]:
        """Find all available backup files.

        Returns:
            List of tuples containing (backup_path, parsed_config)
        """
        backups = []

        for location in self.backup_locations:
            if location.is_file():
                # Single file backup
                config = self._load_json_file(location)
                if config:
                    backups.append((location, config))
            elif location.is_dir():
                # Directory with multiple backups
                for backup_file in location.glob("*.json*"):
                    if (
                        "backup" in backup_file.name
                        or backup_file.parent.name == "backups"
                    ):
                        config = self._load_json_file(backup_file)
                        if config:
                            backups.append((backup_file, config))

        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)

        return backups

    def _load_json_file(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load and parse a JSON file safely.

        Args:
            path: Path to JSON file

        Returns:
            Parsed JSON dictionary or None if invalid
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Ensure it has the expected structure
                if isinstance(config, dict):
                    return config
        except (json.JSONDecodeError, IOError):
            pass
        return None

    def extract_mcp_servers(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract MCP server configurations from a config.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary of MCP server configurations
        """
        servers = {}

        # Check for direct mcpServers key
        if "mcpServers" in config:
            servers.update(config["mcpServers"])

        # Check for nested structure (some backups might have different structure)
        if "mcp" in config and "servers" in config["mcp"]:
            servers.update(config["mcp"]["servers"])

        return servers

    def merge_configurations(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple configurations intelligently.

        Args:
            configs: List of configuration dictionaries

        Returns:
            Merged configuration with all unique MCP servers
        """
        merged = {"mcpServers": {}}
        all_servers = {}

        for config in configs:
            servers = self.extract_mcp_servers(config)
            for name, server_config in servers.items():
                if name not in all_servers:
                    all_servers[name] = server_config
                else:
                    # If duplicate, keep the one with more complete configuration
                    existing = all_servers[name]
                    if len(str(server_config)) > len(str(existing)):
                        all_servers[name] = server_config

        merged["mcpServers"] = all_servers
        return merged

    def list_backups(self) -> None:
        """List all available backup files with their contents."""
        print("\n🔍 Searching for backup files...")
        backups = self.find_backups()

        if not backups:
            print("❌ No backup files found")
            print("\nSearched locations:")
            for location in self.backup_locations:
                print(f"  - {location}")
            return

        print(f"\n📦 Found {len(backups)} backup file(s):\n")

        for i, (path, config) in enumerate(backups, 1):
            # Get file info
            stat = path.stat()
            mod_time = datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # Extract MCP servers
            servers = self.extract_mcp_servers(config)
            server_names = list(servers.keys()) if servers else []

            print(f"{i}. {path}")
            print(f"   Modified: {mod_time}")
            print(f"   Size: {stat.st_size:,} bytes")
            if server_names:
                print(f"   MCP Servers: {', '.join(server_names)}")
            else:
                print(f"   MCP Servers: (none)")
            print()

    def show_preview(self, config: Dict[str, Any], source: str = "merged") -> None:
        """Show a preview of what will be restored.

        Args:
            config: Configuration to preview
            source: Description of the source
        """
        print(f"\n📋 Preview of {source} configuration:")
        print("=" * 50)

        servers = config.get("mcpServers", {})
        if not servers:
            print("No MCP servers in this configuration")
            return

        print(f"\nMCP Servers ({len(servers)} total):")
        for name, server_config in servers.items():
            print(f"\n  📦 {name}")
            print(f"     Command: {server_config.get('command', 'N/A')}")
            if "args" in server_config:
                args_str = (
                    " ".join(server_config["args"])
                    if isinstance(server_config["args"], list)
                    else str(server_config["args"])
                )
                if len(args_str) > 50:
                    args_str = args_str[:47] + "..."
                print(f"     Args: {args_str}")
            if "cwd" in server_config:
                print(f"     Working Dir: {server_config['cwd']}")

    def create_backup(self) -> Path:
        """Create a backup of the current configuration.

        Returns:
            Path to the backup file
        """
        if not self.config_path.exists():
            print("  No existing config to backup")
            return None

        # Create backup directory
        backup_dir = self.config_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"config_before_restore_{timestamp}.json"

        # Copy current config
        shutil.copy2(self.config_path, backup_path)
        print(f"💾 Created backup of current config at {backup_path}")

        return backup_path

    def restore_from_backup(
        self, backup_path: Optional[Path] = None, merge_all: bool = False
    ) -> bool:
        """Restore configuration from backup file(s).

        Args:
            backup_path: Specific backup file to restore from
            merge_all: If True, merge all found backups

        Returns:
            True if successful, False otherwise
        """
        # Find backups
        backups = self.find_backups()

        if not backups:
            print("❌ No backup files found to restore from")
            return False

        # Determine what to restore
        if backup_path:
            # Restore specific backup
            config_to_restore = None
            for path, config in backups:
                if path == backup_path:
                    config_to_restore = config
                    source_desc = f"backup: {backup_path.name}"
                    break

            if not config_to_restore:
                print(f"❌ Backup file not found: {backup_path}")
                return False

        elif merge_all:
            # Merge all backups
            print(f"\n🔄 Merging {len(backups)} backup files...")
            all_configs = [config for _, config in backups]
            config_to_restore = self.merge_configurations(all_configs)
            source_desc = f"merge of {len(backups)} backups"

            # Show which backups are being merged
            print("\nMerging configurations from:")
            for path, config in backups:
                servers = self.extract_mcp_servers(config)
                print(f"  - {path.name} ({len(servers)} servers)")

        else:
            # Interactive selection
            print("\n📦 Available backups:")
            for i, (path, config) in enumerate(backups, 1):
                servers = self.extract_mcp_servers(config)
                print(f"  {i}. {path.name} ({len(servers)} servers)")

            print(f"  {len(backups) + 1}. Merge all backups")

            try:
                choice = input(
                    f"\nSelect backup to restore (1-{len(backups) + 1}): "
                ).strip()
                choice_num = int(choice)

                if choice_num == len(backups) + 1:
                    # Merge all
                    return self.restore_from_backup(merge_all=True)
                elif 1 <= choice_num <= len(backups):
                    # Specific backup
                    selected_path, config_to_restore = backups[choice_num - 1]
                    source_desc = f"backup: {selected_path.name}"
                else:
                    print("❌ Invalid selection")
                    return False

            except (ValueError, KeyboardInterrupt):
                print("\n❌ Restoration cancelled")
                return False

        # Show preview
        self.show_preview(config_to_restore, source_desc)

        # Confirm restoration
        print(f"\n⚠️  This will replace the current configuration at:")
        print(f"   {self.config_path}")

        try:
            confirm = input("\nProceed with restoration? (yes/no): ").strip().lower()
            if confirm not in ["yes", "y"]:
                print("❌ Restoration cancelled")
                return False
        except KeyboardInterrupt:
            print("\n❌ Restoration cancelled")
            return False

        # Create backup of current config
        if self.config_path.exists():
            self.create_backup()

        # Perform restoration
        try:
            # Ensure parent directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write restored configuration
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_to_restore, f, indent=2)

            print(f"\n✅ Successfully restored configuration from {source_desc}")
            print(f"   Configuration saved to {self.config_path}")

            # Show summary
            servers = config_to_restore.get("mcpServers", {})
            if servers:
                print(f"\n📦 Restored MCP servers: {', '.join(servers.keys())}")

            return True

        except Exception as e:
            print(f"❌ Failed to restore configuration: {e}")
            return False

    def show_comparison(self) -> None:
        """Show comparison between current config and available backups."""
        print("\n📊 Configuration Comparison")
        print("=" * 50)

        # Load current config
        current_servers = {}
        if self.config_path.exists():
            current_config = self._load_json_file(self.config_path)
            if current_config:
                current_servers = self.extract_mcp_servers(current_config)

        print(f"\n📍 Current configuration ({self.config_path}):")
        if current_servers:
            print(f"   MCP Servers: {', '.join(current_servers.keys())}")
        else:
            print("   No MCP servers configured")

        # Find and show backups
        backups = self.find_backups()
        if backups:
            print(f"\n💾 Available backups ({len(backups)} found):")

            all_servers = set()
            for path, config in backups:
                servers = self.extract_mcp_servers(config)
                all_servers.update(servers.keys())

                # Show what's different
                unique_in_backup = set(servers.keys()) - set(current_servers.keys())
                print(f"\n   {path.name}:")
                print(
                    f"     Servers: {', '.join(servers.keys()) if servers else '(none)'}"
                )
                if unique_in_backup:
                    print(f"     Unique: {', '.join(unique_in_backup)}")

            # Show summary
            unique_across_backups = all_servers - set(current_servers.keys())
            if unique_across_backups:
                print(f"\n📌 Servers in backups but not current config:")
                print(f"   {', '.join(unique_across_backups)}")


def main():
    """Main entry point for the restoration script."""
    parser = argparse.ArgumentParser(
        description="Restore Claude Desktop MCP configurations from backups"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all available backup files"
    )
    parser.add_argument(
        "--from",
        dest="backup_file",
        type=Path,
        help="Restore from specific backup file",
    )
    parser.add_argument(
        "--merge", action="store_true", help="Merge all available backups"
    )
    parser.add_argument(
        "--compare", action="store_true", help="Compare current config with backups"
    )
    parser.add_argument(
        "--config-path", type=Path, help="Custom path to Claude Desktop config.json"
    )

    args = parser.parse_args()

    # Initialize restorer
    restorer = MCPConfigRestorer(args.config_path)

    # Execute requested action
    if args.list:
        restorer.list_backups()
    elif args.compare:
        restorer.show_comparison()
    elif args.backup_file or args.merge:
        success = restorer.restore_from_backup(args.backup_file, args.merge)
        sys.exit(0 if success else 1)
    else:
        # Interactive mode
        print("\n🔧 MCP Configuration Restore Tool")
        print("=" * 50)
        success = restorer.restore_from_backup()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
