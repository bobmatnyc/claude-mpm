#!/usr/bin/env python3
"""Verify that the TUI navigation is working correctly."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.configure_tui import ConfigureTUI, can_use_tui


def main():
    """Run the TUI verification."""
    print("=" * 60)
    print("TUI Navigation Verification")
    print("=" * 60)

    # Check if TUI is available
    if not can_use_tui():
        print("⚠️  TUI is not available in this environment")
        print("Reasons:")
        print("  - Not running in an interactive terminal")
        print("  - Terminal too small (needs 80x24 minimum)")
        print("  - TERM environment variable not set properly")
        return 1

    print("✓ TUI is available")
    print()
    print("Starting TUI with navigation test...")
    print()
    print("INSTRUCTIONS:")
    print("1. Use arrow keys to navigate the menu")
    print("2. Press Enter to select a menu item")
    print("3. Click on menu items with the mouse")
    print("4. Use Ctrl+A/T/B/S for quick navigation")
    print("5. Press Ctrl+Q to quit")
    print()
    print("EXPECTED BEHAVIOR:")
    print("- Clicking or selecting a menu item should switch screens")
    print("- The selected item should be highlighted")
    print("- A notification should appear when switching screens")
    print()
    print("Press Enter to start the TUI...")
    input()

    try:
        # Create and run the TUI
        app = ConfigureTUI(current_scope="project", project_dir=Path.cwd())
        app.run()
        print("\n✓ TUI exited successfully")
        return 0
    except KeyboardInterrupt:
        print("\n✓ TUI cancelled by user")
        return 0
    except Exception as e:
        print(f"\n❌ TUI error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
