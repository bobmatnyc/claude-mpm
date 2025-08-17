#!/usr/bin/env python3
"""
Update Claude Desktop MCP configuration to use the correct command.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


def update_mcp_config():
    """Update the MCP configuration in Claude Desktop."""
    
    # Find config file
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    
    if not config_path.exists():
        print(f"❌ Config file not found at: {config_path}")
        return False
    
    # Create backup
    backup_path = config_path.with_suffix(f".json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(config_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    
    # Read current config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("Current MCP configuration:")
    if "mcpServers" in config and "claude-mpm-gateway" in config["mcpServers"]:
        print(json.dumps(config["mcpServers"]["claude-mpm-gateway"], indent=2))
    
    # Update configuration
    config["mcpServers"]["claude-mpm-gateway"] = {
        "command": "claude-mpm-mcp"
    }
    
    # Write updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n✅ Updated MCP configuration to:")
    print(json.dumps(config["mcpServers"]["claude-mpm-gateway"], indent=2))
    
    print("\n📌 Next steps:")
    print("1. Restart Claude Desktop to load the new configuration")
    print("2. The MCP tools should now include all 10 tools:")
    print("   - 5 basic tools (echo, calculator, system_info, run_command, summarize_document)")
    print("   - 5 ticket tools (ticket_create, ticket_list, ticket_update, ticket_view, ticket_search)")
    
    return True


if __name__ == "__main__":
    update_mcp_config()