#!/usr/bin/env python3
"""
Migration script to update Co-Authored-By email from anthropic to claude-mpm.

This migration updates all template files to use:
  Co-Authored-By: Claude MPM <claude-mpm@matsuoka.com>

Instead of:
  Co-Authored-By: Claude <noreply@anthropic.com>
  Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
  Co-Authored-By: agent-improver <noreply@anthropic.com>
  Co-Authored-By: skills-manager <noreply@anthropic.com>

Usage:
    python -m claude_mpm.migrations.migrate_coauthor_email [--dry-run]
"""

import argparse
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Pattern to match various co-author formats with anthropic email
COAUTHOR_PATTERN = re.compile(
    r"Co-Authored-By:\s*[^<]*<[^>]*@anthropic\.com>",
    re.IGNORECASE,
)

# New co-author line
NEW_COAUTHOR = "Co-Authored-By: Claude MPM <claude-mpm@matsuoka.com>"


def get_package_root() -> Path:
    """Get the root of the claude_mpm package."""
    # This file is in src/claude_mpm/migrations/
    return Path(__file__).parent.parent


def find_files_to_update(root: Path) -> list[Path]:
    """Find all files that contain the old co-author pattern.

    Args:
        root: Root directory to search

    Returns:
        List of file paths containing the pattern
    """
    files_to_update = []

    # Search in relevant directories
    search_dirs = [
        root / "agents" / "templates",
        root / "skills" / "bundled",
        root / "services",
    ]

    # File extensions to check
    extensions = {".md", ".py", ".json", ".yaml", ".yml", ".txt"}

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for file_path in search_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in extensions:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if COAUTHOR_PATTERN.search(content):
                        files_to_update.append(file_path)
                except (OSError, UnicodeDecodeError):
                    continue

    return files_to_update


def update_file(file_path: Path, dry_run: bool = False) -> int:
    """Update co-author lines in a single file.

    Args:
        file_path: Path to the file
        dry_run: If True, only show what would be done

    Returns:
        Number of replacements made
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"  Failed to read {file_path}: {e}")
        return 0

    # Count matches before replacement
    matches = COAUTHOR_PATTERN.findall(content)
    if not matches:
        return 0

    # Replace all matches
    new_content = COAUTHOR_PATTERN.sub(NEW_COAUTHOR, content)

    if dry_run:
        logger.info(
            f"  [DRY RUN] Would update {len(matches)} occurrence(s) in {file_path.name}"
        )
        for match in matches[:3]:  # Show first 3 matches
            logger.info(f"    - {match} -> {NEW_COAUTHOR}")
        if len(matches) > 3:
            logger.info(f"    ... and {len(matches) - 3} more")
        return len(matches)

    # Write updated content
    try:
        file_path.write_text(new_content, encoding="utf-8")
        logger.info(f"  Updated {len(matches)} occurrence(s) in {file_path.name}")
        return len(matches)
    except OSError as e:
        logger.error(f"  Failed to write {file_path}: {e}")
        return 0


def migrate_coauthor_email(dry_run: bool = False) -> bool:
    """Run the co-author email migration.

    Args:
        dry_run: If True, only show what would be done

    Returns:
        True if migration was successful
    """
    root = get_package_root()
    logger.info(f"Searching for files in {root}")

    files = find_files_to_update(root)

    if not files:
        logger.info("No files found with old co-author pattern")
        return True

    logger.info(f"Found {len(files)} file(s) to update")

    if dry_run:
        logger.info("[DRY RUN MODE]")

    total_replacements = 0
    for file_path in files:
        replacements = update_file(file_path, dry_run=dry_run)
        total_replacements += replacements

    logger.info(f"\nTotal: {total_replacements} replacement(s) in {len(files)} file(s)")
    return True


def main() -> int:
    """Main entry point for CLI migration."""
    parser = argparse.ArgumentParser(
        description="Migrate Co-Authored-By email from anthropic to claude-mpm"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()

    success = migrate_coauthor_email(dry_run=args.dry_run)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
