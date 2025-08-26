#!/usr/bin/env python3
"""Test script for the enhanced Agent Management TUI screen.

This script tests the new 3-pane Agent Management interface with:
- Category tabs (System, Project, User)
- Agent list with deployment status
- Agent details and actions panel
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.configure_tui import ConfigureTUI, can_use_tui


def main():
    """Run the TUI with focus on Agent Management screen."""
    if not can_use_tui():
        print("Terminal does not support full-screen TUI mode.")
        print("Please run in a terminal that supports TUI (not a pipe or redirect).")
        return 1

    print("Starting enhanced Agent Management TUI...")
    print("Press Ctrl+Q to quit")
    print()
    print("Features to test:")
    print("1. Three-pane layout with categories, agent list, and details")
    print("2. Deploy/Undeploy agents to/from .claude/agents/")
    print("3. View agent properties (JSON)")
    print("4. Copy system agents to project or user directories")
    print("5. Edit project/user agents")
    print("6. Delete project/user agents")
    print()
    input("Press Enter to continue...")

    try:
        # Create the app with project scope
        app = ConfigureTUI(current_scope="project", project_dir=Path.cwd())

        # Run the app
        app.run()

        print("\nTUI closed successfully.")
        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 0
    except Exception as e:
        print(f"\nError running TUI: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
