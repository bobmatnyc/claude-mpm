#!/usr/bin/env python3
"""
Test script for the configure command.

This script tests the new configure command functionality.
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.cli import main


def test_configure_help():
    """Test configure command help."""
    print("Testing: claude-mpm configure --help")
    sys.argv = ["claude-mpm", "configure", "--help"]
    try:
        main()
    except SystemExit as e:
        if e.code == 0:
            print("✓ Help displayed successfully\n")
        else:
            print(f"✗ Help failed with code {e.code}\n")


def test_configure_list_agents():
    """Test listing agents non-interactively."""
    print("Testing: claude-mpm configure --list-agents")
    sys.argv = ["claude-mpm", "configure", "--list-agents"]
    try:
        result = main()
        print(f"✓ List agents completed with code {result}\n")
    except Exception as e:
        print(f"✗ List agents failed: {e}\n")


def test_configure_version_info():
    """Test version info display."""
    print("Testing: claude-mpm configure --version-info")
    sys.argv = ["claude-mpm", "configure", "--version-info"]
    try:
        result = main()
        print(f"✓ Version info completed with code {result}\n")
    except Exception as e:
        print(f"✗ Version info failed: {e}\n")


def test_configure_enable_agent():
    """Test enabling an agent."""
    print("Testing: claude-mpm configure --enable-agent engineer")
    sys.argv = ["claude-mpm", "configure", "--enable-agent", "engineer"]
    try:
        result = main()
        print(f"✓ Enable agent completed with code {result}\n")
    except Exception as e:
        print(f"✗ Enable agent failed: {e}\n")


def test_configure_disable_agent():
    """Test disabling an agent."""
    print("Testing: claude-mpm configure --disable-agent designer")
    sys.argv = ["claude-mpm", "configure", "--disable-agent", "designer"]
    try:
        result = main()
        print(f"✓ Disable agent completed with code {result}\n")
    except Exception as e:
        print(f"✗ Disable agent failed: {e}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing claude-mpm configure command")
    print("=" * 60)
    print()

    test_configure_help()
    test_configure_list_agents()
    test_configure_version_info()
    test_configure_enable_agent()
    test_configure_disable_agent()

    print("=" * 60)
    print("Testing complete!")
    print("=" * 60)
