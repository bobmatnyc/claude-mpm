#!/usr/bin/env python3
"""
Demo script showing both configuration interface modes:
1. Modern Textual full-screen TUI
2. Classic Rich menu-based interface

Run with different flags to see different modes:
- Normal: Will auto-detect and use best available
- --force-rich: Force use of Rich menu interface
- --no-textual: Disable Textual and use Rich
"""

import argparse
import sys
from pathlib import Path

# Add src to path for development testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.configure import ConfigureCommand


def demo_textual_mode():
    """Demo the Textual full-screen mode."""
    print("\n" + "=" * 60)
    print("DEMO: Textual Full-Screen Mode")
    print("=" * 60)
    print("""
Features:
- Full-screen windowed interface
- Mouse support (click on elements)
- Keyboard navigation (Tab, arrows, shortcuts)
- Live search and filtering
- Modal dialogs for confirmations
- Professional dark theme with CSS styling

Screens:
1. Agent Management - DataTable with enable/disable toggles
2. Template Editing - Side-by-side template viewer/editor
3. Behavior Files - Tree view with YAML editor
4. Settings - Version info and scope switching

Keyboard Shortcuts:
- Ctrl+A: Jump to Agent Management
- Ctrl+T: Jump to Template Editing
- Ctrl+B: Jump to Behavior Files
- Ctrl+S: Jump to Settings
- Ctrl+Q: Quit
- Tab: Navigate between UI elements
- Enter: Select/Activate
- Arrow keys: Navigate lists and tables
""")
    print("Press Enter to launch Textual TUI...")
    input()

    # Create mock args
    class Args:
        use_textual = True
        force_rich = False
        scope = "project"
        project_dir = None
        no_colors = False
        list_agents = False
        enable_agent = None
        disable_agent = None
        export_config = None
        import_config = None
        version_info = False
        agents = False
        templates = False
        behaviors = False

    args = Args()
    command = ConfigureCommand()
    result = command._run_interactive_tui(args)

    print(f"\nResult: {result.message}")

def demo_rich_mode():
    """Demo the Rich menu-based mode."""
    print("\n" + "=" * 60)
    print("DEMO: Rich Menu-Based Mode")
    print("=" * 60)
    print("""
Features:
- Terminal-based menu navigation
- Colored output with Rich formatting
- Tables and panels for data display
- Interactive prompts for user input
- Works in any terminal

Menu Options:
1. Agent Management - Enable/disable agents
2. Template Editing - Edit agent JSON templates
3. Behavior Files - Manage identity and workflow configs
4. Switch Scope - Toggle between project and user scope
5. Version Info - Display MPM and Claude versions
q. Quit - Exit configuration interface

Navigation:
- Enter menu number to select
- Follow prompts for actions
- Use 'b' to go back in sub-menus
""")
    print("Press Enter to launch Rich menu interface...")
    input()

    # Create mock args
    class Args:
        use_textual = False
        force_rich = True
        scope = "project"
        project_dir = None
        no_colors = False
        list_agents = False
        enable_agent = None
        disable_agent = None
        export_config = None
        import_config = None
        version_info = False
        agents = False
        templates = False
        behaviors = False

    args = Args()
    command = ConfigureCommand()
    result = command._run_interactive_tui(args)

    print(f"\nResult: {result.message}")

def main():
    """Main demo entry point."""
    parser = argparse.ArgumentParser(description="Demo Claude MPM Configuration Interfaces")
    parser.add_argument(
        "--mode",
        choices=["textual", "rich", "both"],
        default="both",
        help="Which interface mode to demo"
    )

    args = parser.parse_args()

    print("Claude MPM Configuration Interface Demo")
    print("========================================")

    if args.mode == "textual":
        demo_textual_mode()
    elif args.mode == "rich":
        demo_rich_mode()
    else:
        print("\nThis demo shows both configuration interface modes.")
        print("You can run with --mode=textual or --mode=rich to see just one.\n")

        print("1. Textual Full-Screen TUI (modern, recommended)")
        print("2. Rich Menu Interface (classic, fallback)")
        print("\nWhich would you like to try? (1/2/q): ", end="")

        choice = input().strip()
        if choice == "1":
            demo_textual_mode()
        elif choice == "2":
            demo_rich_mode()
        elif choice.lower() != "q":
            print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()
