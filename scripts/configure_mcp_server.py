#!/usr/bin/env python3
"""
MCP Server Configuration Script
================================

This script configures Claude Code to use the claude-mpm MCP gateway server
with the correct Python environment and wrapper script.

WHY: The MCP server needs to be configured with absolute paths and the proper
wrapper script to ensure the Python environment is set up correctly.

DESIGN DECISION: Use the wrapper script approach to handle environment setup
robustly, regardless of how Claude Code invokes the server.
"""

import json
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path


def get_config_path():
    """
    Get the Claude Code configuration file path based on the platform.
    
    Returns:
        Path: Path to the configuration file
    """
    system = platform.system()
    home = Path.home()
    
    if system == "Darwin":  # macOS
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        return home / ".config" / "Claude" / "config.json"
    elif system == "Windows":
        return home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def find_project_root():
    """
    Find the claude-mpm project root directory.
    
    Returns:
        Path: Project root directory
    """
    # Start from this script's location
    current = Path(__file__).resolve().parent.parent
    
    # Verify it's the correct directory
    if (current / "pyproject.toml").exists():
        return current
    
    # Try common locations
    common_paths = [
        Path("/Users/masa/Projects/claude-mpm"),
        Path.home() / "Projects" / "claude-mpm",
    ]
    
    for path in common_paths:
        if path.exists() and (path / "pyproject.toml").exists():
            return path
    
    raise RuntimeError("Could not find claude-mpm project root")


def backup_config(config_path):
    """
    Create a backup of the existing configuration file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Path: Path to the backup file, or None if no existing config
    """
    if not config_path.exists():
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config_path.parent / f"{config_path.stem}_backup_{timestamp}{config_path.suffix}"
    
    shutil.copy2(config_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    
    return backup_path


def load_or_create_config(config_path):
    """
    Load existing configuration or create a new one.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        dict: Configuration dictionary
    """
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                print(f"✅ Loaded existing configuration from {config_path}")
                return config
        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Existing config is invalid JSON: {e}")
            print("   Creating new configuration...")
    
    # Create new configuration
    config_path.parent.mkdir(parents=True, exist_ok=True)
    return {}


def configure_mcp_server(config, project_root):
    """
    Configure the MCP server in the configuration.
    
    Args:
        config: Configuration dictionary
        project_root: Path to project root
        
    Returns:
        dict: Updated configuration
    """
    # Ensure mcpServers section exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Find the claude-mpm command
    claude_mpm_path = shutil.which("claude-mpm")
    if not claude_mpm_path:
        # Try to find it in the virtual environment
        venv_path = project_root / "venv" / "bin" / "claude-mpm"
        if venv_path.exists():
            claude_mpm_path = str(venv_path)
        else:
            # Fallback to using python -m
            claude_mpm_path = sys.executable
            args = ["-m", "claude_mpm.cli", "mcp", "server"]
    else:
        args = ["mcp", "server"]
    
    # Configure the claude-mpm-gateway server
    mcp_config = {
        "command": claude_mpm_path,  # Use the claude-mpm command directly
        "args": args,  # Run mcp server subcommand
        "cwd": str(project_root),
        "env": {
            "PYTHONPATH": str(project_root / "src"),
            "CLAUDE_MPM_ROOT": str(project_root),
            "MCP_MODE": "production",
            "DISABLE_TELEMETRY": "1"
        }
    }
    
    # Check if configuration already exists and differs
    existing = config["mcpServers"].get("claude-mpm-gateway", {})
    if existing:
        print("\n📋 Existing configuration found:")
        print(f"   Command: {existing.get('command', 'not set')}")
        print(f"   Args: {existing.get('args', 'not set')}")
        print(f"   CWD: {existing.get('cwd', 'not set')}")
        
        if existing != mcp_config:
            print("\n🔄 Updating configuration...")
        else:
            print("\n✅ Configuration is already correct")
            return config
    
    # Update configuration
    config["mcpServers"]["claude-mpm-gateway"] = mcp_config
    
    print("\n✅ Configured claude-mpm-gateway server:")
    print(f"   Command: {mcp_config['command']}")
    print(f"   Args: {mcp_config['args']}")
    print(f"   CWD: {mcp_config['cwd']}")
    print(f"   Environment variables set: {list(mcp_config['env'].keys())}")
    
    return config


def save_config(config, config_path):
    """
    Save the configuration to file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to save the configuration
    """
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write configuration with nice formatting
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Configuration saved to {config_path}")


def verify_wrapper_script(project_root):
    """
    Verify the wrapper script exists and is executable.
    
    Args:
        project_root: Path to project root
        
    Returns:
        bool: True if wrapper is ready
    """
    wrapper_script = project_root / "scripts" / "mcp_wrapper.py"
    
    if not wrapper_script.exists():
        print(f"❌ Error: Wrapper script not found at {wrapper_script}")
        return False
    
    # Make it executable on Unix-like systems
    if platform.system() != "Windows":
        import stat
        current_perms = wrapper_script.stat().st_mode
        wrapper_script.chmod(current_perms | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"✅ Wrapper script is executable: {wrapper_script}")
    
    return True


def print_next_steps():
    """Print instructions for next steps."""
    print("\n" + "=" * 60)
    print("🎉 MCP Server Configuration Complete!")
    print("=" * 60)
    
    print("\n📝 Next Steps:")
    print("1. Restart Claude Code to load the new configuration")
    print("2. The MCP server will start automatically when Claude Code launches")
    print("3. Check server status with: python scripts/check_mcp_processes.py")
    
    print("\n🧪 To test the server manually:")
    print("   python scripts/mcp_wrapper.py")
    
    print("\n🔍 To verify the setup:")
    print("   python scripts/verify_mcp_setup.py")
    
    print("\n📊 To check running processes:")
    print("   python scripts/check_mcp_processes.py")
    
    print("\n⚠️  Important Notes:")
    print("- The server runs in stdio mode (communicates via stdin/stdout)")
    print("- Logs are written to stderr to avoid interfering with the protocol")
    print("- Multiple server instances may be spawned by Claude Code (this is normal)")


def main():
    """Main entry point."""
    print("=" * 60)
    print("🚀 MCP Server Configuration Script")
    print("=" * 60)
    
    try:
        # Find project root
        print("\n1️⃣  Finding project root...")
        project_root = find_project_root()
        print(f"   Project root: {project_root}")
        
        # Verify wrapper script
        print("\n2️⃣  Verifying wrapper script...")
        if not verify_wrapper_script(project_root):
            print("❌ Error: Wrapper script verification failed")
            sys.exit(1)
        
        # Get configuration path
        print("\n3️⃣  Determining configuration path...")
        config_path = get_config_path()
        print(f"   Configuration path: {config_path}")
        
        # Backup existing configuration
        print("\n4️⃣  Backing up existing configuration...")
        backup_path = backup_config(config_path)
        if backup_path:
            print(f"   Backup created: {backup_path}")
        else:
            print("   No existing configuration to backup")
        
        # Load or create configuration
        print("\n5️⃣  Loading configuration...")
        config = load_or_create_config(config_path)
        
        # Configure MCP server
        print("\n6️⃣  Configuring MCP server...")
        config = configure_mcp_server(config, project_root)
        
        # Save configuration
        print("\n7️⃣  Saving configuration...")
        save_config(config, config_path)
        
        # Print next steps
        print_next_steps()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())