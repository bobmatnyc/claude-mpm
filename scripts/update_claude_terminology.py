#!/usr/bin/env python3
"""
Script to update Claude Desktop terminology to Claude Code throughout the codebase.

This script systematically updates all instances of "Claude Desktop" to "Claude Code"
in Python files, Markdown files, and other text files.

Note: Some instances may need special handling based on context.
"""

import os
import re
from pathlib import Path
from typing import Tuple


def should_skip_file(file_path: Path) -> bool:
    """Check if a file should be skipped."""
    skip_dirs = {
        ".git",
        "__pycache__",
        "venv",
        "node_modules",
        ".pytest_cache",
        "build",
        "dist",
    }

    for part in file_path.parts:
        if part in skip_dirs:
            return True

    # Skip binary files
    if file_path.suffix in {".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".bin"}:
        return True

    return False


def update_file(file_path: Path, dry_run: bool = False) -> Tuple[bool, int]:
    """Update Claude Desktop to Claude Code in a file.

    Returns:
        (was_updated, num_replacements)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return False, 0

    original_content = content

    # Replace "Claude Desktop" with "Claude Code"
    # Handle various cases
    patterns = [
        (r"Claude Desktop", "Claude Code"),
        (r"CLAUDE DESKTOP", "CLAUDE CODE"),
        (r"claude desktop", "claude code"),
    ]

    replacement_count = 0
    for pattern, replacement in patterns:
        new_content = re.sub(pattern, replacement, content)
        replacement_count += len(re.findall(pattern, content))
        content = new_content

    if content != original_content:
        if not dry_run:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        return True, replacement_count

    return False, 0


def main():
    """Main function to update terminology."""
    project_root = Path(__file__).parent.parent

    print("🔄 Updating Claude Desktop → Claude Code terminology")
    print("=" * 60)

    # File extensions to process
    extensions = {".py", ".md", ".txt", ".rst", ".yml", ".yaml", ".json", ".sh"}

    updated_files = []
    total_replacements = 0

    for root, dirs, files in os.walk(project_root):
        root_path = Path(root)

        # Skip certain directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d not in {"venv", "__pycache__", "node_modules"}
        ]

        for file in files:
            file_path = root_path / file

            # Check if we should process this file
            if file_path.suffix not in extensions:
                continue

            if should_skip_file(file_path):
                continue

            # Skip this script itself
            if file_path.name == "update_claude_terminology.py":
                continue

            was_updated, num_replacements = update_file(file_path)

            if was_updated:
                updated_files.append((file_path, num_replacements))
                total_replacements += num_replacements
                relative_path = file_path.relative_to(project_root)
                print(
                    f"  ✅ Updated: {relative_path} ({num_replacements} replacements)"
                )

    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"  - Files updated: {len(updated_files)}")
    print(f"  - Total replacements: {total_replacements}")

    if updated_files:
        print("\n📝 Updated files:")
        for file_path, count in sorted(updated_files, key=lambda x: x[1], reverse=True)[
            :10
        ]:
            relative_path = file_path.relative_to(project_root)
            print(f"  - {relative_path}: {count} replacements")

        if len(updated_files) > 10:
            print(f"  ... and {len(updated_files) - 10} more files")

    print("\n✅ Terminology update complete!")
    print("\n⚠️  Note: Please review the changes, especially in:")
    print("  - Configuration files")
    print("  - User-facing documentation")
    print("  - Test files")
    print("\nSome references might be intentionally referring to the old name.")


if __name__ == "__main__":
    main()
