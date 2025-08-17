#!/usr/bin/env python3
"""
Script to fix syntax errors in import statements caused by the previous update.

This script fixes cases where class names were incorrectly replaced with function calls
in import statements.
"""

import re
import sys
from pathlib import Path
from typing import List


def fix_import_syntax(file_path: Path) -> bool:
    """
    Fix import syntax errors in a single file.

    Args:
        file_path: Path to the file to fix

    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix incorrect function call imports
        fixes = [
            # Fix import statements with function calls
            (
                r"from claude_mpm\.core\.unified_paths import get_path_manager\(\)",
                "from claude_mpm.core.unified_paths import get_path_manager",
            ),
            (
                r"from claude_mpm\.core\.unified_agent_registry import get_agent_registry\(\)",
                "from claude_mpm.core.unified_agent_registry import get_agent_registry",
            ),
            # Fix other incorrect replacements in import statements
            (r"import get_path_manager\(\)", "import get_path_manager"),
            (r"import get_agent_registry\(\)", "import get_agent_registry"),
        ]

        for pattern, replacement in fixes:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                print(f"  Fixed import syntax in {file_path}")

        # Write back if changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in a directory."""
    python_files = []
    for file_path in directory.rglob("*.py"):
        # Skip certain directories
        skip_dirs = {
            "__pycache__",
            ".git",
            "node_modules",
            ".pytest_cache",
            "venv",
            ".venv",
            "dist",
            "build",
            ".tox",
        }

        if any(skip_dir in str(file_path) for skip_dir in skip_dirs):
            continue

        # Skip backup files
        if file_path.name.endswith("_original.py"):
            continue

        python_files.append(file_path)

    return python_files


def main():
    """Main function to fix import syntax errors."""
    print("Fixing import syntax errors...")
    print("=" * 40)

    # Get project root
    project_root = Path(__file__).parent.parent.parent
    src_dir = project_root / "src"

    if not src_dir.exists():
        print(f"Error: src directory not found at {src_dir}")
        return 1

    total_fixed = 0

    # Fix imports in src directory
    python_files = find_python_files(src_dir)
    print(f"Checking {len(python_files)} files in src/")

    for file_path in python_files:
        if fix_import_syntax(file_path):
            total_fixed += 1

    # Also fix test files
    tests_dir = project_root / "tests"
    if tests_dir.exists():
        test_files = find_python_files(tests_dir)
        print(f"Checking {len(test_files)} files in tests/")

        for file_path in test_files:
            if fix_import_syntax(file_path):
                total_fixed += 1

    # Fix tools
    tools_dir = project_root / "tools"
    if tools_dir.exists():
        tool_files = find_python_files(tools_dir)
        print(f"Checking {len(tool_files)} files in tools/")

        for file_path in tool_files:
            if fix_import_syntax(file_path):
                total_fixed += 1

    print("=" * 40)
    print(f"Import syntax fix complete!")
    print(f"Files fixed: {total_fixed}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
