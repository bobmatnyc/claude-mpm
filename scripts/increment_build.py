#!/usr/bin/env python3
"""
Build number increment script for claude-mpm.

WHY: Track every code change with a unique build number that auto-increments
only when actual code changes are made (not documentation or configuration).

DESIGN DECISION: Uses git diff to detect code changes and only increments
the build number when relevant files are modified. This prevents build
number inflation from documentation or configuration changes.

BUILD NUMBER FORMAT:
    - Stored as a simple integer in BUILD_NUMBER file
    - Combined with VERSION for display:
      * Development: "3.9.5+build.275" (PEP 440)
      * UI/Logging: "v3.9.5-build.275"
      * PyPI Release: "3.9.5" (clean)

USAGE:
    python scripts/increment_build.py [--check-only] [--force]

    --check-only: Check if increment is needed without changing the file
    --force: Force increment regardless of changes
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def get_project_root() -> Path:
    """Get the project root directory.

    Returns:
        Path to the project root (parent of scripts directory)
    """
    script_dir = Path(__file__).parent.absolute()
    return script_dir.parent


def get_current_build_number(build_file: Path) -> int:
    """Read the current build number from BUILD_NUMBER file.

    Args:
        build_file: Path to the BUILD_NUMBER file

    Returns:
        Current build number, or 0 if file doesn't exist
    """
    if not build_file.exists():
        return 0

    try:
        content = build_file.read_text().strip()
        return int(content)
    except (OSError, ValueError) as e:
        print(
            f"Warning: Could not read build number from {build_file}: {e}",
            file=sys.stderr,
        )
        return 0


def write_build_number(build_file: Path, build_number: int) -> None:
    """Write the build number to BUILD_NUMBER file.

    Args:
        build_file: Path to the BUILD_NUMBER file
        build_number: Build number to write
    """
    try:
        build_file.write_text(str(build_number))
        print(f"Build number updated to: {build_number}")
    except OSError as e:
        print(
            f"Error: Could not write build number to {build_file}: {e}", file=sys.stderr
        )
        sys.exit(1)


def get_git_diff_files(staged_only: bool = True) -> List[str]:
    """Get list of modified files from git.

    Args:
        staged_only: If True, only check staged files. If False, check all changes.

    Returns:
        List of modified file paths relative to repository root
    """
    try:
        # Determine which files to check
        if staged_only:
            # Check staged files (for pre-commit hook)
            cmd = ["git", "diff", "--cached", "--name-only"]
        else:
            # Check all modified files (staged and unstaged)
            cmd = ["git", "diff", "HEAD", "--name-only"]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, cwd=get_project_root()
        )

        files = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return [f for f in files if f]  # Filter out empty strings

    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not get git diff: {e}", file=sys.stderr)
        return []


def has_code_changes(files: List[str]) -> Tuple[bool, List[str]]:
    """Check if the list of files contains code changes.

    Code changes are defined as:
    - Python files (*.py) in src/
    - Shell scripts (*.sh) in scripts/

    Excluded:
    - Markdown files (*.md)
    - JSON files in agents/templates/
    - Documentation files in docs/
    - Test files (can be configured)

    Args:
        files: List of file paths to check

    Returns:
        Tuple of (has_changes, list_of_code_files)
    """
    code_files = []

    for file in files:
        # Skip if it's the BUILD_NUMBER file itself
        if file == "BUILD_NUMBER":
            continue

        # Check for code files
        if file.endswith(".py") and file.startswith("src/"):
            # Python source files
            code_files.append(file)
        elif file.endswith(".sh") and file.startswith("scripts/"):
            # Shell scripts
            code_files.append(file)
        elif file.endswith(".py") and file.startswith("scripts/"):
            # Python scripts in scripts directory
            code_files.append(file)
        # Intentionally exclude:
        # - *.md files (documentation)
        # - *.json files in agents/templates/ (configuration)
        # - files in docs/ directory (documentation)

    return bool(code_files), code_files


def main():
    """Main entry point for the build increment script."""
    parser = argparse.ArgumentParser(
        description="Increment build number for code changes"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check if increment is needed without changing the file",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force increment regardless of changes"
    )
    parser.add_argument(
        "--staged-only",
        action="store_true",
        default=True,
        help="Only check staged files (default for pre-commit hook)",
    )
    parser.add_argument(
        "--all-changes",
        action="store_true",
        help="Check all changes, not just staged files",
    )

    args = parser.parse_args()

    # Determine which files to check
    staged_only = not args.all_changes

    # Get project root and build file path
    project_root = get_project_root()
    build_file = project_root / "BUILD_NUMBER"

    # Get current build number
    current_build = get_current_build_number(build_file)

    # Check for code changes or force increment
    if args.force:
        has_changes = True
        code_files = ["<forced>"]
        print("Forcing build number increment...")
    else:
        # Get modified files from git
        modified_files = get_git_diff_files(staged_only=staged_only)

        # Check if any are code files
        has_changes, code_files = has_code_changes(modified_files)

    if args.check_only:
        # Just report whether increment is needed
        if has_changes:
            print(f"Build increment needed. Code files changed: {len(code_files)}")
            for f in code_files[:10]:  # Show first 10 files
                print(f"  - {f}")
            if len(code_files) > 10:
                print(f"  ... and {len(code_files) - 10} more")
            sys.exit(0)  # Exit 0 means increment needed
        else:
            print("No code changes detected, build increment not needed")
            sys.exit(1)  # Exit 1 means no increment needed

    # Perform the increment if needed
    if has_changes:
        new_build = current_build + 1
        write_build_number(build_file, new_build)
        print(f"Code changes detected in {len(code_files)} file(s)")
        for f in code_files[:5]:  # Show first 5 files
            print(f"  - {f}")
        if len(code_files) > 5:
            print(f"  ... and {len(code_files) - 5} more")
    else:
        print(f"No code changes detected, keeping build number at: {current_build}")


if __name__ == "__main__":
    main()
