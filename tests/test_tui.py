#!/usr/bin/env python3
"""Test script for the TUI configuration interface."""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.configure_tui import ConfigureTUI, can_use_tui


def main():
    """Run the TUI test."""
    print("Testing TUI configuration interface...")
    print(f"Terminal support: {can_use_tui()}")

    if not can_use_tui():
        print("Terminal does not support TUI mode")
        return 1

    print("\nLaunching TUI...")
    print("Watch the console/log output for debug messages")
    print("Try clicking on menu items and observe the logs")
    print("\nPress Ctrl+Q to quit\n")

    try:
        app = ConfigureTUI(current_scope="project", project_dir=Path.cwd())
        app.run()
        return 0
    except KeyboardInterrupt:
        print("\nTUI cancelled by user")
        return 0
    except Exception as e:
        print(f"\nError running TUI: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
