#!/usr/bin/env python3
"""
Test script to verify hook configuration is working.

This script:
1. Checks if hooks are properly configured in settings.local.json
2. Verifies the hook handler script exists and is executable
3. Tests a simple hook event if possible
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def check_settings_file():
    """Check if hooks are configured in the correct settings file."""
    settings_local = Path.home() / ".claude" / "settings.local.json"
    settings_old = Path.home() / ".claude" / "settings.json"

    print("=" * 60)
    print("HOOK CONFIGURATION CHECK")
    print("=" * 60)

    # Check settings.local.json (the correct file)
    if settings_local.exists():
        print(f"✓ Found settings.local.json at: {settings_local}")
        with settings_local.open() as f:
            config = json.load(f)

        if "hooks" in config:
            print("✓ Hooks section found in settings.local.json")
            print("\nConfigured events:")
            for event, hooks_list in config["hooks"].items():
                print(f"  • {event}")
                for hook_config in hooks_list:
                    if "matcher" in hook_config:
                        print(f"    - Matcher: '{hook_config['matcher']}'")
                    if "hooks" in hook_config:
                        for hook in hook_config["hooks"]:
                            if hook.get("type") == "command":
                                cmd = hook.get("command", "").split("/")[-1]
                                print(f"    - Handler: {cmd}")
        else:
            print("✗ No hooks section in settings.local.json")
    else:
        print(f"✗ settings.local.json not found at: {settings_local}")

    # Check old settings.json
    print("\n" + "-" * 40)
    if settings_old.exists():
        with settings_old.open() as f:
            old_config = json.load(f)

        if "hooks" in old_config:
            print("⚠️  WARNING: Found hooks in settings.json (wrong file)")
            print("   Claude Code reads hooks from settings.local.json")
            print("   Run: python -m claude_mpm configure --install-hooks --force")
        else:
            print("✓ No hooks in settings.json (correct)")

    return settings_local.exists() and "hooks" in config


def check_hook_script():
    """Check if the hook handler script exists and is executable."""
    print("\n" + "=" * 60)
    print("HOOK HANDLER SCRIPT CHECK")
    print("=" * 60)

    # Try to find the script path from settings
    settings_local = Path.home() / ".claude" / "settings.local.json"
    script_path = None

    if settings_local.exists():
        with settings_local.open() as f:
            config = json.load(f)

        # Extract script path from hooks configuration
        if "hooks" in config:
            for event_hooks in config["hooks"].values():
                for hook_config in event_hooks:
                    if "hooks" in hook_config:
                        for hook in hook_config["hooks"]:
                            if hook.get("type") == "command":
                                script_path = Path(hook.get("command", ""))
                                break
                if script_path:
                    break

    if script_path and script_path.exists():
        print(f"✓ Hook script found at: {script_path}")

        # Check if executable
        if os.access(script_path, os.X_OK):
            print("✓ Script is executable")
        else:
            print("✗ Script is not executable")
            print(f"  Fix with: chmod +x {script_path}")

        # Check script content
        with script_path.open() as f:
            content = f.read()

        if "claude_mpm.hooks.claude_hooks.hook_handler" in content:
            print("✓ Script contains correct hook handler reference")
        else:
            print("⚠️  Script may not have correct handler reference")

        return True
    print("✗ Hook script not found")
    return False


def check_socketio_server():
    """Check if the SocketIO server is running."""
    print("\n" + "=" * 60)
    print("SOCKETIO SERVER CHECK")
    print("=" * 60)

    try:
        # Check if port 8765 is listening
        result = subprocess.run(
            ["lsof", "-i", ":8765"], capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            print("✓ SocketIO server is running on port 8765")
            print("  Dashboard URL: http://localhost:8765")
            return True
        print("✗ SocketIO server is not running")
        print("  Start with: python -m claude_mpm monitor")
        return False
    except Exception as e:
        print(f"⚠️  Could not check server status: {e}")
        return False


def main():
    """Run all checks."""
    print("\n" + "=" * 60)
    print("CLAUDE MPM HOOK VERIFICATION")
    print("=" * 60)

    all_good = True

    # Run checks
    if not check_settings_file():
        all_good = False

    if not check_hook_script():
        all_good = False

    if not check_socketio_server():
        all_good = False

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if all_good:
        print("✅ All checks passed!")
        print("\nHooks are properly configured. When you use tools in Claude Code:")
        print("1. PreToolUse and PostToolUse events will trigger")
        print("2. Events will be sent to the SocketIO server on port 8765")
        print("3. View them in the dashboard at http://localhost:8765")
        print("\nThe '*' matcher means all tools will trigger these hooks.")
    else:
        print("⚠️  Some issues were found. Please review the output above.")
        print("\nTo fix hook configuration:")
        print("  python -m claude_mpm configure --install-hooks --force")
        print("\nTo start the monitoring server:")
        print("  python -m claude_mpm monitor")

    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
