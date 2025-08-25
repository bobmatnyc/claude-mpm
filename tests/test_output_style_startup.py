#!/usr/bin/env python3
"""Test script to verify output style is set on startup."""

import json
import subprocess
import sys
import time
from pathlib import Path


def check_output_style():
    """Check if output style is properly set."""
    settings_file = Path.home() / ".claude" / "settings.json"
    output_style_file = Path.home() / ".claude" / "output-styles" / "claude-mpm.md"

    # Check settings
    if settings_file.exists():
        settings = json.loads(settings_file.read_text())
        active_style = settings.get("activeOutputStyle", "none")
        print(f"✓ Active output style: {active_style}")

        if active_style != "claude-mpm":
            print(f"✗ Expected 'claude-mpm' but got '{active_style}'")
            return False
    else:
        print("✗ Settings file not found")
        return False

    # Check output style file
    if output_style_file.exists():
        print(f"✓ Output style file exists: {output_style_file}")
    else:
        print(f"✗ Output style file not found: {output_style_file}")
        return False

    return active_style == "claude-mpm"


def reset_output_style():
    """Reset output style for testing."""
    settings_file = Path.home() / ".claude" / "settings.json"
    if settings_file.exists():
        settings = json.loads(settings_file.read_text())
        settings["activeOutputStyle"] = "default"
        settings_file.write_text(json.dumps(settings, indent=2))
        print("Reset output style to 'default' for testing")


def test_startup():
    """Test that output style is set on startup."""
    print("\n=== Testing Output Style on Startup ===\n")

    # Step 1: Reset output style
    print("Step 1: Resetting output style...")
    reset_output_style()

    # Step 2: Run claude-mpm briefly
    print("\nStep 2: Starting claude-mpm...")
    try:
        # Start claude-mpm and let it initialize
        proc = subprocess.Popen(
            ["venv/bin/claude-mpm", "run", "--verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Wait for initialization
        time.sleep(3)

        # Terminate the process
        proc.terminate()
        proc.wait(timeout=2)

    except Exception as e:
        print(f"Error running claude-mpm: {e}")
        return False

    # Step 3: Check if output style was set
    print("\nStep 3: Checking output style...")
    if check_output_style():
        print("\n✅ SUCCESS: Output style is properly set to 'Claude MPM' on startup!")
        return True
    print("\n✗ FAILURE: Output style was not set correctly on startup.")
    return False


if __name__ == "__main__":
    success = test_startup()
    sys.exit(0 if success else 1)
