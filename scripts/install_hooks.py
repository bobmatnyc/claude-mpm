#!/usr/bin/env python3
"""Install claude-mpm hooks for Claude Code integration."""

import json
import os
import shutil
import sys
from pathlib import Path


def find_hook_files():
    """Find the hook files in the installed package."""
    # Try different possible locations
    locations = [
        # Development environment
        Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks",
        # Installed package - site-packages
        Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "claude_mpm" / "hooks" / "claude_hooks",
        # Installed package - alternative location
        Path(sys.prefix) / "claude_mpm" / "hooks" / "claude_hooks",
    ]
    
    # Also check if claude_mpm is importable
    try:
        import claude_mpm
        package_dir = Path(claude_mpm.__file__).parent
        locations.append(package_dir / "hooks" / "claude_hooks")
    except ImportError:
        pass
    
    for location in locations:
        if location.exists() and (location / "hook_handler.py").exists():
            return location
    
    return None


def install_hooks():
    """Install hooks for Claude Code."""
    # Find claude settings directory
    claude_dir = Path.home() / ".claude"
    settings_file = claude_dir / "settings.json"
    
    # Find hook files
    hook_dir = find_hook_files()
    if not hook_dir:
        print("❌ Could not find claude-mpm hook files!")
        print("Make sure claude-mpm is properly installed.")
        return False
    
    print(f"✓ Found hook files at: {hook_dir}")
    
    # Get absolute path to hook wrapper
    hook_wrapper = hook_dir / "hook_wrapper.sh"
    if not hook_wrapper.exists():
        print(f"❌ Hook wrapper not found at: {hook_wrapper}")
        return False
    
    hook_wrapper_path = str(hook_wrapper.absolute())
    print(f"✓ Hook wrapper path: {hook_wrapper_path}")
    
    # Create claude directory if it doesn't exist
    claude_dir.mkdir(exist_ok=True)
    
    # Load existing settings or create new
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        print("✓ Found existing Claude settings")
    else:
        settings = {}
        print("✓ Creating new Claude settings")
    
    # Configure hooks
    hook_config = {
        "matcher": "*",
        "hooks": [
            {
                "type": "command",
                "command": hook_wrapper_path
            }
        ]
    }
    
    # Update settings
    if "hooks" not in settings:
        settings["hooks"] = {}
    
    # Add hooks for all event types
    for event_type in ["UserPromptSubmit", "PreToolUse", "PostToolUse"]:
        settings["hooks"][event_type] = [hook_config]
    
    # Write settings
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    print(f"✓ Updated Claude settings at: {settings_file}")
    
    # Copy commands if they exist
    commands_src = Path(__file__).parent.parent / ".claude" / "commands"
    if commands_src.exists():
        commands_dst = claude_dir / "commands"
        commands_dst.mkdir(exist_ok=True)
        
        for cmd_file in commands_src.glob("*.md"):
            shutil.copy2(cmd_file, commands_dst / cmd_file.name)
            print(f"✓ Copied command: {cmd_file.name}")
    
    print("\n✨ Hook installation complete!")
    print("\nYou can now use /mpm commands in Claude Code:")
    print("  /mpm         - Show help")
    print("  /mpm status  - Show claude-mpm status")
    
    return True


if __name__ == "__main__":
    success = install_hooks()
    sys.exit(0 if success else 1)