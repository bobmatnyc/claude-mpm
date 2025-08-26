#!/usr/bin/env python3
"""Script to migrate logging imports from utils.logger to core.logger."""

import re
from pathlib import Path
from typing import List, Tuple


def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files in the project."""
    return list(root_dir.rglob("*.py"))


def update_imports(file_path: Path, dry_run: bool = False) -> Tuple[bool, List[str]]:
    """Update imports in a single file.

    Returns:
        Tuple of (was_modified, changes_made)
    """
    with open(file_path) as f:
        content = f.read()

    original_content = content
    changes = []

    # Pattern replacements
    replacements = [
        # utils.logger imports
        (
            r"from claude_mpm\.utils\.logger import",
            "from claude_mpm.core.logger import",
        ),
        (r"from \.\.utils\.logger import", "from ..core.logger import"),
        (r"from \.\.\.utils\.logger import", "from ...core.logger import"),
        (r"from \.utils\.logger import", "from .core.logger import"),
        # logging_config imports (preserve special imports)
        (
            r"from claude_mpm\.core\.logging_config import setup_logging",
            "from claude_mpm.core.logger import setup_logging",
        ),
        (
            r"from claude_mpm\.core\.logging_config import get_logger",
            "from claude_mpm.core.logger import get_logger",
        ),
        (
            r"from claude_mpm\.core\.logging_config import setup_streaming_logger",
            "from claude_mpm.core.logger import setup_streaming_logger",
        ),
        (
            r"from claude_mpm\.core\.logging_config import finalize_streaming_logs",
            "from claude_mpm.core.logger import finalize_streaming_logs",
        ),
        (r"from \.\.core\.logging_config import", "from ..core.logger import"),
        (r"from \.core\.logging_config import", "from .core.logger import"),
        # project_logger imports (preserve ProjectLogger imports)
        (
            r"from claude_mpm\.core\.project_logger import get_project_logger",
            "from claude_mpm.core.logger import get_project_logger",
        ),
        (
            r"from claude_mpm\.core\.project_logger import ProjectLogger",
            "from claude_mpm.core.logger import ProjectLogger",
        ),
        (r"from \.\.core\.project_logger import", "from ..core.logger import"),
        (r"from \.core\.project_logger import", "from .core.logger import"),
    ]

    for pattern, replacement in replacements:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changes.append(f"Replaced: {pattern} -> {replacement}")

    if content != original_content:
        if not dry_run:
            with open(file_path, "w") as f:
                f.write(content)
        return True, changes

    return False, []


def main():
    """Main migration function."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"

    print("Migrating logging imports...")
    print(f"Project root: {project_root}")
    print(f"Source directory: {src_dir}")

    # Find all Python files
    python_files = find_python_files(src_dir)
    python_files.extend(find_python_files(project_root / "scripts"))
    python_files.extend(find_python_files(project_root / "tests"))

    # Skip the new logger.py file and this script
    logger_file = src_dir / "claude_mpm" / "core" / "logger.py"
    this_script = Path(__file__)
    python_files = [f for f in python_files if f not in (logger_file, this_script)]

    print(f"\nFound {len(python_files)} Python files to check")

    modified_files = []

    for file_path in python_files:
        was_modified, changes = update_imports(file_path, dry_run=False)
        if was_modified:
            modified_files.append((file_path, changes))
            print(f"\nModified: {file_path.relative_to(project_root)}")
            for change in changes:
                print(f"  - {change}")

    print(f"\n\nSummary: Modified {len(modified_files)} files")

    if modified_files:
        print("\nModified files:")
        for file_path, _ in modified_files:
            print(f"  - {file_path.relative_to(project_root)}")


if __name__ == "__main__":
    main()
