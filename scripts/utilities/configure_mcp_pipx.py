#!/usr/bin/env python3
"""
Configure MCP server for Claude Code when claude-mpm is installed via pipx.

This script helps users set up the MCP server configuration for Claude Code
when claude-mpm has been installed using pipx.
"""

import json
import os
import sys
import subprocess
from pathlib import Path
import platform


def find_pipx_claude_mpm():
    """Find the pipx installation path for claude-mpm."""
    try:
        # Try to find pipx venv location
        result = subprocess.run(
            ["pipx", "list", "--json"],
            capture_output=True,
            text=True,
            check=True
        )
        pipx_data = json.loads(result.stdout)
        
        venvs = pipx_data.get("venvs", {})
        if "claude-mpm" in venvs:
            venv_info = venvs["claude-mpm"]
            # Get the main package location
            main_package = venv_info.get("metadata", {}).get("main_package", {})
            package_location = main_package.get("package_or_url")
            
            # Try to find the actual installation path
            pipx_home = Path(os.environ.get("PIPX_HOME", Path.home() / ".local" / "pipx"))
            venv_path = pipx_home / "venvs" / "claude-mpm"
            
            # Look for the package in site-packages
            for site_packages in venv_path.glob("lib/python*/site-packages"):
                claude_mpm_path = site_packages / "claude_mpm"
                if claude_mpm_path.exists():
                    return claude_mpm_path
                    
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
        pass
    
    # Fallback: try common locations
    common_paths = [
        Path.home() / ".local" / "pipx" / "venvs" / "claude-mpm",
        Path("/opt/pipx/venvs/claude-mpm"),
        Path("/usr/local/pipx/venvs/claude-mpm"),
    ]
    
    for base_path in common_paths:
        for site_packages in base_path.glob("lib/python*/site-packages"):
            claude_mpm_path = site_packages / "claude_mpm"
            if claude_mpm_path.exists():
                return claude_mpm_path
    
    return None


def find_claude_config_path():
    """Find the Claude Code configuration file path."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            config_path = Path(appdata) / "Claude" / "claude_desktop_config.json"
        else:
            config_path = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else:  # Linux and others
        config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    
    return config_path


def create_mcp_config(claude_mpm_path):
    """Create the MCP server configuration."""
    # Find the scripts directory (should be in the package)
    scripts_dir = claude_mpm_path / "scripts"
    if not scripts_dir.exists():
        # Try parent directory
        scripts_dir = claude_mpm_path.parent / "scripts"
    
    mcp_wrapper = scripts_dir / "mcp_wrapper.py" if scripts_dir.exists() else None
    
    # If we can't find mcp_wrapper.py, use the installed command
    if not mcp_wrapper or not mcp_wrapper.exists():
        # Use the installed claude-mpm-mcp command
        return {
            "mcpServers": {
                "claude-mpm-gateway": {
                    "command": "claude-mpm-mcp"
                }
            }
        }
    else:
        # Use the wrapper script with python3
        return {
            "mcpServers": {
                "claude-mpm-gateway": {
                    "command": "python3",
                    "args": [str(mcp_wrapper)],
                    "cwd": str(claude_mpm_path.parent)
                }
            }
        }


def main():
    print("Claude MPM - MCP Server Configuration for pipx Installation")
    print("=" * 60)
    
    # Check if pipx is installed
    print("\n1. Checking pipx installation...")
    try:
        subprocess.run(["pipx", "--version"], capture_output=True, check=True)
        print("✅ pipx is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pipx is not installed or not in PATH")
        print("\nPlease install pipx first:")
        print("  python3 -m pip install --user pipx")
        print("  python3 -m pipx ensurepath")
        return 1
    
    # Find claude-mpm installation
    print("\n2. Finding claude-mpm installation...")
    claude_mpm_path = find_pipx_claude_mpm()
    
    if not claude_mpm_path:
        print("❌ Could not find claude-mpm pipx installation")
        print("\nPlease ensure claude-mpm is installed via pipx:")
        print("  pipx install claude-mpm")
        print("\nIf you installed it differently, use the main MCP setup guide:")
        print("  See: docs/MCP_SETUP.md")
        return 1
    
    print(f"✅ Found claude-mpm at: {claude_mpm_path}")
    
    # Find Claude config path
    print("\n3. Finding Claude Code configuration...")
    config_path = find_claude_config_path()
    print(f"📁 Config path: {config_path}")
    
    # Check if config exists
    config_exists = config_path.exists()
    if config_exists:
        print("✅ Config file exists")
        try:
            with open(config_path, 'r') as f:
                existing_config = json.load(f)
        except json.JSONDecodeError:
            print("⚠️  Config file exists but is not valid JSON")
            existing_config = {}
    else:
        print("📝 Config file does not exist (will be created)")
        existing_config = {}
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create MCP configuration
    print("\n4. Generating MCP server configuration...")
    mcp_config = create_mcp_config(claude_mpm_path)
    
    # Merge with existing config
    if "mcpServers" in existing_config:
        print("⚠️  Existing MCP servers found in config")
        if "claude-mpm-gateway" in existing_config["mcpServers"]:
            print("⚠️  claude-mpm-gateway already configured")
            response = input("\nOverwrite existing configuration? (y/N): ").strip().lower()
            if response != 'y':
                print("Keeping existing configuration")
                return 0
    
    # Update configuration
    existing_config.update(mcp_config)
    
    # Show the configuration
    print("\n5. Configuration to be written:")
    print(json.dumps(mcp_config, indent=2))
    
    # Confirm
    response = input("\nWrite this configuration? (y/N): ").strip().lower()
    if response != 'y':
        print("Configuration not written")
        return 0
    
    # Write configuration
    try:
        with open(config_path, 'w') as f:
            json.dump(existing_config, f, indent=2)
        print(f"\n✅ Configuration written to: {config_path}")
        print("\n6. Next steps:")
        print("   1. Restart Claude Code")
        print("   2. Look for the MCP icon in Claude Code")
        print("   3. The claude-mpm tools should now be available")
        
        # Test the configuration
        print("\n7. Testing the configuration...")
        if "command" in mcp_config["mcpServers"]["claude-mpm-gateway"]:
            cmd = mcp_config["mcpServers"]["claude-mpm-gateway"]["command"]
            args = mcp_config["mcpServers"]["claude-mpm-gateway"].get("args", [])
            
            if cmd == "claude-mpm-mcp":
                # Test the installed command
                try:
                    result = subprocess.run(
                        ["which", "claude-mpm-mcp"],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode == 0:
                        print(f"✅ Command 'claude-mpm-mcp' found at: {result.stdout.strip()}")
                    else:
                        print("⚠️  Command 'claude-mpm-mcp' not found in PATH")
                        print("   Ensure pipx binaries are in your PATH")
                except Exception as e:
                    print(f"⚠️  Could not test command: {e}")
            else:
                # Test the wrapper script
                test_cmd = [cmd] + args
                wrapper_path = args[0] if args else None
                if wrapper_path and Path(wrapper_path).exists():
                    print(f"✅ Wrapper script exists: {wrapper_path}")
                else:
                    print(f"⚠️  Wrapper script not found: {wrapper_path}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error writing configuration: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())