#!/usr/bin/env python3
"""
MCP Configuration Sync Script

This script syncs MCP server configurations between Claude Desktop and Claude Code,
ensuring both applications have the same MCP servers configured.

Usage:
    python scripts/sync_mcp_configs.py                  # Interactive sync
    python scripts/sync_mcp_configs.py --to-code        # Copy Desktop → Code
    python scripts/sync_mcp_configs.py --to-desktop     # Copy Code → Desktop
    python scripts/sync_mcp_configs.py --status         # Show differences
    python scripts/sync_mcp_configs.py --merge          # Merge configurations
"""

import json
import argparse
import sys
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Set, Tuple


class MCPConfigSync:
    """Syncs MCP configurations between Claude Desktop and Claude Code."""
    
    def __init__(self):
        """Initialize the sync manager."""
        system = platform.system()
        
        # Claude Desktop config path
        if system == "Darwin":  # macOS
            self.desktop_config = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif system == "Linux":
            self.desktop_config = Path.home() / ".config" / "Claude" / "config.json"
        elif system == "Windows":
            self.desktop_config = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        else:
            self.desktop_config = Path.home() / ".config" / "Claude" / "config.json"
        
        # Claude Code config path (always in home directory)
        self.code_config = Path.home() / ".claude.json"
        
        print(f"🖥️  Platform: {system}")
        print(f"📁 Desktop config: {self.desktop_config}")
        print(f"📁 Code config: {self.code_config}")
    
    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load a configuration file.
        
        Args:
            config_path: Path to the config file
            
        Returns:
            Configuration dictionary or empty structure if not exists
        """
        if not config_path.exists():
            print(f"⚠️  Config file not found: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON from {config_path}: {e}")
            return {}
        except Exception as e:
            print(f"❌ Error reading {config_path}: {e}")
            return {}
    
    def get_mcp_servers(self, config: Dict[str, Any], config_type: str) -> Dict[str, Any]:
        """Extract MCP servers from a configuration.
        
        Args:
            config: Configuration dictionary
            config_type: "desktop" or "code"
            
        Returns:
            Dictionary of MCP servers
        """
        if config_type == "code":
            # Claude Code may have mcpServers at root level
            return config.get("mcpServers", {})
        else:
            # Claude Desktop has mcpServers at root
            return config.get("mcpServers", {})
    
    def create_backup(self, config_path: Path):
        """Create a timestamped backup of a configuration file.
        
        Args:
            config_path: Path to the config file to backup
        """
        if not config_path.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.parent / f"{config_path.name}.backup_{timestamp}"
        
        try:
            import shutil
            shutil.copy2(config_path, backup_path)
            print(f"💾 Created backup: {backup_path}")
        except Exception as e:
            print(f"⚠️  Failed to create backup: {e}")
    
    def show_status(self) -> Tuple[Set[str], Set[str], Set[str]]:
        """Show the current MCP server configuration status.
        
        Returns:
            Tuple of (desktop_only, code_only, common) server names
        """
        print("\n📊 MCP Configuration Status")
        print("=" * 60)
        
        # Load configurations
        desktop_config = self.load_config(self.desktop_config)
        code_config = self.load_config(self.code_config)
        
        # Get MCP servers
        desktop_servers = set(self.get_mcp_servers(desktop_config, "desktop").keys())
        code_servers = set(self.get_mcp_servers(code_config, "code").keys())
        
        # Calculate differences
        desktop_only = desktop_servers - code_servers
        code_only = code_servers - desktop_servers
        common = desktop_servers & code_servers
        
        # Display results
        print(f"\n🖥️  Claude Desktop MCP Servers ({len(desktop_servers)} total):")
        if desktop_servers:
            for server in sorted(desktop_servers):
                marker = "✅" if server in common else "⚠️"
                print(f"  {marker} {server}")
        else:
            print("  (none)")
        
        print(f"\n💻 Claude Code MCP Servers ({len(code_servers)} total):")
        if code_servers:
            for server in sorted(code_servers):
                marker = "✅" if server in common else "⚠️"
                print(f"  {marker} {server}")
        else:
            print("  (none)")
        
        print(f"\n📈 Summary:")
        print(f"  Common servers: {len(common)}")
        print(f"  Desktop only: {len(desktop_only)}")
        print(f"  Code only: {len(code_only)}")
        
        if desktop_only:
            print(f"\n⚠️  Servers only in Desktop: {', '.join(sorted(desktop_only))}")
        if code_only:
            print(f"\n⚠️  Servers only in Code: {', '.join(sorted(code_only))}")
        
        return desktop_only, code_only, common
    
    def sync_to_code(self, dry_run: bool = False) -> bool:
        """Copy MCP servers from Claude Desktop to Claude Code.
        
        Args:
            dry_run: If True, preview changes without applying them
            
        Returns:
            True if successful, False otherwise
        """
        print("\n📤 Syncing Desktop → Code...")
        
        # Load desktop configuration
        desktop_config = self.load_config(self.desktop_config)
        desktop_servers = self.get_mcp_servers(desktop_config, "desktop")
        
        if not desktop_servers:
            print("⚠️  No MCP servers found in Claude Desktop configuration")
            return False
        
        # Load Code configuration
        code_config = self.load_config(self.code_config)
        if not code_config:
            code_config = {}
        
        # Update Code configuration with Desktop servers
        code_config["mcpServers"] = desktop_servers.copy()
        
        print(f"  Copying {len(desktop_servers)} servers to Claude Code")
        print(f"  Servers: {', '.join(sorted(desktop_servers.keys()))}")
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes made")
            return True
        
        # Create backup
        self.create_backup(self.code_config)
        
        # Save updated configuration
        try:
            with open(self.code_config, 'w', encoding='utf-8') as f:
                json.dump(code_config, f, indent=2)
            print(f"✅ Successfully synced to {self.code_config}")
            return True
        except Exception as e:
            print(f"❌ Failed to save configuration: {e}")
            return False
    
    def sync_to_desktop(self, dry_run: bool = False) -> bool:
        """Copy MCP servers from Claude Code to Claude Desktop.
        
        Args:
            dry_run: If True, preview changes without applying them
            
        Returns:
            True if successful, False otherwise
        """
        print("\n📥 Syncing Code → Desktop...")
        
        # Load Code configuration
        code_config = self.load_config(self.code_config)
        code_servers = self.get_mcp_servers(code_config, "code")
        
        if not code_servers:
            print("⚠️  No MCP servers found in Claude Code configuration")
            return False
        
        # Load Desktop configuration
        desktop_config = self.load_config(self.desktop_config)
        if not desktop_config:
            desktop_config = {}
        
        # Update Desktop configuration with Code servers
        desktop_config["mcpServers"] = code_servers.copy()
        
        print(f"  Copying {len(code_servers)} servers to Claude Desktop")
        print(f"  Servers: {', '.join(sorted(code_servers.keys()))}")
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes made")
            return True
        
        # Create backup
        self.create_backup(self.desktop_config)
        
        # Save updated configuration
        try:
            # Ensure parent directory exists
            self.desktop_config.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.desktop_config, 'w', encoding='utf-8') as f:
                json.dump(desktop_config, f, indent=2)
            print(f"✅ Successfully synced to {self.desktop_config}")
            return True
        except Exception as e:
            print(f"❌ Failed to save configuration: {e}")
            return False
    
    def merge_configs(self, dry_run: bool = False) -> bool:
        """Merge MCP servers from both configurations.
        
        Args:
            dry_run: If True, preview changes without applying them
            
        Returns:
            True if successful, False otherwise
        """
        print("\n🔄 Merging configurations...")
        
        # Load both configurations
        desktop_config = self.load_config(self.desktop_config)
        code_config = self.load_config(self.code_config)
        
        # Get MCP servers
        desktop_servers = self.get_mcp_servers(desktop_config, "desktop")
        code_servers = self.get_mcp_servers(code_config, "code")
        
        # Merge servers (Code servers take precedence for conflicts)
        merged_servers = desktop_servers.copy()
        merged_servers.update(code_servers)
        
        print(f"  Desktop servers: {len(desktop_servers)}")
        print(f"  Code servers: {len(code_servers)}")
        print(f"  Merged total: {len(merged_servers)}")
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes made")
            print("\nMerged servers:")
            for name in sorted(merged_servers.keys()):
                print(f"  - {name}")
            return True
        
        # Create backups
        self.create_backup(self.desktop_config)
        self.create_backup(self.code_config)
        
        # Update both configurations
        desktop_config["mcpServers"] = merged_servers
        code_config["mcpServers"] = merged_servers
        
        success = True
        
        # Save Desktop configuration
        try:
            self.desktop_config.parent.mkdir(parents=True, exist_ok=True)
            with open(self.desktop_config, 'w', encoding='utf-8') as f:
                json.dump(desktop_config, f, indent=2)
            print(f"✅ Updated Desktop: {self.desktop_config}")
        except Exception as e:
            print(f"❌ Failed to save Desktop config: {e}")
            success = False
        
        # Save Code configuration
        try:
            with open(self.code_config, 'w', encoding='utf-8') as f:
                json.dump(code_config, f, indent=2)
            print(f"✅ Updated Code: {self.code_config}")
        except Exception as e:
            print(f"❌ Failed to save Code config: {e}")
            success = False
        
        if success:
            print(f"\n✅ Successfully merged {len(merged_servers)} MCP servers")
        
        return success
    
    def interactive_sync(self):
        """Interactive sync mode with user prompts."""
        desktop_only, code_only, common = self.show_status()
        
        if not desktop_only and not code_only:
            print("\n✅ Configurations are already in sync!")
            return
        
        print("\n🔧 Sync Options:")
        print("1. Copy Desktop → Code (overwrites Code config)")
        print("2. Copy Code → Desktop (overwrites Desktop config)")
        print("3. Merge both (combine all servers)")
        print("4. Exit without changes")
        
        while True:
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == "1":
                self.sync_to_code()
                break
            elif choice == "2":
                self.sync_to_desktop()
                break
            elif choice == "3":
                self.merge_configs()
                break
            elif choice == "4":
                print("👋 Exiting without changes")
                break
            else:
                print("❌ Invalid option. Please select 1-4.")


def main():
    """Main entry point for the sync script."""
    parser = argparse.ArgumentParser(
        description="Sync MCP servers between Claude Desktop and Claude Code"
    )
    parser.add_argument(
        "--to-code",
        action="store_true",
        help="Copy Desktop servers to Code"
    )
    parser.add_argument(
        "--to-desktop",
        action="store_true",
        help="Copy Code servers to Desktop"
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge servers from both configurations"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current configuration differences"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    
    args = parser.parse_args()
    
    # Initialize sync manager
    sync = MCPConfigSync()
    
    # Execute requested action
    if args.status:
        sync.show_status()
    elif args.to_code:
        success = sync.sync_to_code(args.dry_run)
        sys.exit(0 if success else 1)
    elif args.to_desktop:
        success = sync.sync_to_desktop(args.dry_run)
        sys.exit(0 if success else 1)
    elif args.merge:
        success = sync.merge_configs(args.dry_run)
        sys.exit(0 if success else 1)
    else:
        # Interactive mode
        sync.interactive_sync()


if __name__ == "__main__":
    main()