#!/usr/bin/env python3
"""
Fix Memory File Naming Inconsistencies
=====================================

This script migrates memory files from hyphenated naming (data-engineer_memories.md)
to underscore naming (data_engineer_memories.md) to match deployed agent naming conventions.

Usage:
    python scripts/fix_memory_file_naming.py [--dry-run]

Options:
    --dry-run: Preview changes without actually renaming files
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))


def find_memory_directories() -> List[Path]:
    """Find all .claude-mpm/memories directories in the project."""
    memories_dirs = []

    # Search for .claude-mpm/memories directories
    for path in project_root.rglob(".claude-mpm"):
        memories_dir = path / "memories"
        if memories_dir.exists() and memories_dir.is_dir():
            memories_dirs.append(memories_dir)

    return memories_dirs


def find_misnamed_files(memories_dir: Path) -> List[Tuple[Path, Path]]:
    """Find memory files with hyphens that should have underscores.

    Returns:
        List of tuples (current_path, new_path) for files that need renaming
    """
    files_to_rename = []

    # Look for memory files with hyphens
    for file_path in memories_dir.glob("*-*_memories.md"):
        # Get the agent name from the filename
        filename = file_path.name
        # Replace hyphens with underscores in agent name
        new_filename = filename.replace("-", "_")
        new_path = file_path.parent / new_filename

        # Only add if the new file doesn't already exist
        if not new_path.exists():
            files_to_rename.append((file_path, new_path))
        else:
            print(f"⚠️  Skipping {file_path} - {new_path} already exists")

    return files_to_rename


def migrate_files(
    files_to_rename: List[Tuple[Path, Path]], dry_run: bool = False
) -> int:
    """Migrate files from old naming to new naming.

    Returns:
        Number of files successfully migrated
    """
    migrated_count = 0

    for old_path, new_path in files_to_rename:
        if dry_run:
            print(
                f"Would rename: {old_path.relative_to(project_root)} → {new_path.name}"
            )
        else:
            try:
                old_path.rename(new_path)
                print(
                    f"✅ Renamed: {old_path.relative_to(project_root)} → {new_path.name}"
                )
                migrated_count += 1
            except Exception as e:
                print(f"❌ Failed to rename {old_path}: {e}")

    return migrated_count


def main():
    """Main function to fix memory file naming."""
    parser = argparse.ArgumentParser(
        description="Fix memory file naming inconsistencies"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without actually renaming files",
    )
    args = parser.parse_args()

    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("🔍 Searching for memory directories...")
    memories_dirs = find_memory_directories()

    if not memories_dirs:
        print("No .claude-mpm/memories directories found")
        return 0

    print(f"Found {len(memories_dirs)} memory directories")

    all_files_to_rename = []

    for memories_dir in memories_dirs:
        files_to_rename = find_misnamed_files(memories_dir)
        if files_to_rename:
            print(f"\n📁 In {memories_dir.relative_to(project_root)}:")
            for old_path, new_path in files_to_rename:
                all_files_to_rename.append((old_path, new_path))

    if not all_files_to_rename:
        print("\n✅ No misnamed files found - all memory files use correct naming!")
        return 0

    print(f"\n📋 Found {len(all_files_to_rename)} file(s) to rename")

    if args.dry_run:
        print("\n🔄 DRY RUN MODE - No files will be renamed")
    else:
        print("\n🔄 Renaming files...")

    migrated_count = migrate_files(all_files_to_rename, args.dry_run)

    if not args.dry_run:
        print(f"\n✅ Successfully migrated {migrated_count} file(s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
