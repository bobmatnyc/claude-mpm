#!/usr/bin/env python3
"""Install claude-mpm hooks for Claude Code integration."""

import json
import os
import shutil
import sys
from pathlib import Path


def detect_package_origin():
    """Detect how claude-mpm was installed."""
    # Check if we're in development mode (running from source)
    script_path = Path(__file__).resolve()
    if (script_path.parent.parent / "src" / "claude_mpm").exists():
        return "local", script_path.parent.parent

    # Check for npm installation (node_modules)
    node_modules_markers = [
        Path.cwd() / "node_modules" / "claude-mpm",
        Path.home() / "node_modules" / "claude-mpm",
        Path("/usr/local/lib/node_modules/claude-mpm"),
    ]
    for marker in node_modules_markers:
        if marker.exists():
            return "npm", marker

    # Check for PyPI installation
    try:
        import claude_mpm

        package_path = Path(claude_mpm.__file__).parent
        # PyPI packages are typically in site-packages
        if "site-packages" in str(package_path):
            return "pypi", package_path
        return "unknown", package_path
    except ImportError:
        pass

    return "unknown", None


def find_hook_files():
    """Find the hook files based on installation type."""
    origin, base_path = detect_package_origin()

    if origin == "local":
        # Development environment
        hook_dir = base_path / "src" / "claude_mpm" / "hooks" / "claude_hooks"
        print("📦 Package origin: Local development")
    elif origin == "npm":
        # npm installation
        hook_dir = base_path / "dist" / "claude_mpm" / "hooks" / "claude_hooks"
        if not hook_dir.exists():
            # Try alternative npm structure
            hook_dir = base_path / "src" / "claude_mpm" / "hooks" / "claude_hooks"
        print("📦 Package origin: npm")
    elif origin == "pypi":
        # PyPI installation
        hook_dir = base_path / "hooks" / "claude_hooks"
        print("📦 Package origin: PyPI")
    else:
        # Unknown, try to find it
        print("📦 Package origin: Unknown, searching...")
        possible_locations = [
            Path(sys.prefix)
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
            / "claude_mpm"
            / "hooks"
            / "claude_hooks",
            Path(sys.prefix) / "claude_mpm" / "hooks" / "claude_hooks",
        ]
        for loc in possible_locations:
            if loc.exists() and (loc / "hook_handler.py").exists():
                hook_dir = loc
                break
        else:
            return None

    # Verify the hook files exist
    if hook_dir and hook_dir.exists() and (hook_dir / "hook_handler.py").exists():
        return hook_dir

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

    # Make sure the wrapper script is executable
    hook_wrapper = hook_dir / "hook_wrapper.sh"
    if hook_wrapper.exists():
        import stat

        st = os.stat(hook_wrapper)
        os.chmod(hook_wrapper, st.st_mode | stat.S_IEXEC)
        print("✓ Made hook wrapper executable")

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
        with open(settings_file) as f:
            settings = json.load(f)
        print("✓ Found existing Claude settings")
    else:
        settings = {}
        print("✓ Creating new Claude settings")

    # Configure hooks
    hook_config = {
        "matcher": "*",
        "hooks": [{"type": "command", "command": hook_wrapper_path}],
    }

    # Update settings
    if "hooks" not in settings:
        settings["hooks"] = {}

    # Add hooks for all event types
    for event_type in [
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "Stop",
        "SubagentStop",
    ]:
        settings["hooks"][event_type] = [hook_config]

    # Write settings
    with open(settings_file, "w") as f:
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
