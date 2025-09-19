#!/usr/bin/env python3
"""Verify that AgentManagementScreen has been simplified."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def verify_simplification():
    """Check that the AgentManagementScreen compose method is simplified."""

    # Read the file and check for removed complexity
    file_path = Path("src/claude_mpm/cli/commands/configure_tui.py")
    content = file_path.read_text()

    print("Verification of AgentManagementScreen simplification:")
    print("=" * 50)

    # Check for removed components
    removed_items = [
        "ScrollableContainer",
        "agent-3pane-layout",
        "agent-categories-pane",
        "agent-list-pane",
        "agent-details-pane",
        "copy-to-project",
        "copy-to-user",
        "agent-details-scroll",
    ]

    # Find the compose method for AgentManagementScreen
    import re

    # Extract the compose method
    compose_match = re.search(
        r"class AgentManagementScreen.*?def compose\(self\).*?(?=\n    def |\n\nclass |\Z)",
        content,
        re.DOTALL,
    )

    if compose_match:
        compose_content = compose_match.group()
        print("\n✓ Found AgentManagementScreen compose method")

        # Check for removed items
        print("\nChecking for removed complex components:")
        for item in removed_items:
            if item in compose_content:
                print(f"  ✗ '{item}' still present (should be removed)")
            else:
                print(f"  ✓ '{item}' removed")

        # Check for simplified components
        simple_items = [
            "# Simple vertical layout",
            'DataTable(id="agent-list-table"',
            "height=20",
            'Label("Agent Management", id="screen-title")',
        ]

        print("\nChecking for simplified components:")
        for item in simple_items:
            if item in compose_content:
                print(f"  ✓ '{item}' present")
            else:
                print(f"  ✗ '{item}' not found")

        # Count lines in compose method
        compose_lines = compose_content.count("\n")
        print(f"\nCompose method size: ~{compose_lines} lines")
        if compose_lines < 50:
            print("  ✓ Compose method is compact")
        else:
            print("  ⚠ Compose method might still be complex")

    else:
        print("✗ Could not find AgentManagementScreen compose method")

    # Check CSS simplification
    print("\n" + "=" * 50)
    print("CSS Simplification Check:")

    css_complex = [
        "#agent-scroll-container",
        "#agent-3pane-layout",
        "#agent-categories-pane",
        "#agent-list-pane",
        "#agent-details-pane",
        "min-width: 30",
        "max-width: 55",
    ]

    print("\nChecking for removed complex CSS:")
    for item in css_complex:
        if item in content:
            print(f"  ✗ '{item}' still present")
        else:
            print(f"  ✓ '{item}' removed")

    css_simple = ["#agent-list-table {", "height: 20", "#agent-management-screen {"]

    print("\nChecking for simplified CSS:")
    for item in css_simple:
        if item in content:
            print(f"  ✓ '{item}' present")
        else:
            print(f"  ✗ '{item}' not found")

    print("\n" + "=" * 50)
    print("Verification complete!")


if __name__ == "__main__":
    try:
        verify_simplification()
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
