#!/usr/bin/env python3
"""
Phase 2 of memory manager refactoring - replace method calls with service calls.
"""

import re
from pathlib import Path


def update_method_calls():
    """Update method calls to use the new services."""

    manager_path = Path(
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/memory/agent_memory_manager.py"
    )
    content = manager_path.read_text()

    # Replace method calls
    replacements = [
        (r"self\._parse_memory_list\(", "self.format_service.parse_memory_list("),
        (
            r"self\._clean_template_placeholders_list\(",
            "self.format_service.clean_template_placeholders_list(",
        ),
        (
            r"self\._clean_template_placeholders\(",
            "self.format_service.clean_template_placeholders(",
        ),
        (
            r"self\._build_simple_memory_content\(",
            "self.format_service.build_simple_memory_content(",
        ),
        (
            r"self\._categorize_learning\(",
            "self.categorization_service.categorize_learning(",
        ),
        (
            r"self\._parse_memory_sections\(",
            "self.format_service.parse_memory_sections(",
        ),
    ]

    for old_pattern, new_text in replacements:
        content = re.sub(old_pattern, new_text, content)

    # Write back
    manager_path.write_text(content)
    print("✓ Updated method calls to use services")


def remove_old_methods():
    """Remove the methods that have been extracted to services."""

    manager_path = Path(
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/memory/agent_memory_manager.py"
    )
    lines = manager_path.read_text().splitlines()

    # Methods to remove
    methods_to_remove = [
        "_parse_memory_list",
        "_clean_template_placeholders_list",
        "_clean_template_placeholders",
        "_build_simple_memory_content",
        "_categorize_learning",
        "_parse_memory_sections",
    ]

    # Find and remove each method
    i = 0
    removed_count = 0
    while i < len(lines):
        for method in methods_to_remove:
            if f"def {method}(" in lines[i]:
                # Find the end of this method
                indent = len(lines[i]) - len(lines[i].lstrip())
                start = i
                j = i + 1

                # Skip to end of method
                while j < len(lines):
                    if lines[j].strip():  # Non-empty line
                        current_indent = len(lines[j]) - len(lines[j].lstrip())
                        if current_indent <= indent and lines[j].strip().startswith(
                            "def "
                        ):
                            # Found next method at same or lower indent
                            break
                    j += 1

                # Remove the method
                del lines[start:j]
                removed_count += 1
                print(f"✓ Removed method: {method} ({j - start} lines)")
                i = start - 1  # Adjust index
                break
        i += 1

    # Write back
    manager_path.write_text("\n".join(lines))
    print(f"✓ Removed {removed_count} methods")


def main():
    """Run Phase 2 refactoring."""
    print("Starting Phase 2: Method extraction to services")
    print("=" * 60)

    # Update method calls
    update_method_calls()

    # Remove old methods
    remove_old_methods()

    # Check final line count
    manager_path = Path(
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/memory/agent_memory_manager.py"
    )
    line_count = len(manager_path.read_text().splitlines())

    print("\n" + "=" * 60)
    print("Phase 2 Complete!")
    print(f"Final line count: {line_count} lines")
    if line_count < 800:
        print("✓ Successfully reduced to under 800 lines!")
    else:
        print(f"⚠ Still {line_count - 800} lines over target")


if __name__ == "__main__":
    main()
