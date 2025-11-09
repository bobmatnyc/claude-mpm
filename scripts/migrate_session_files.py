#!/usr/bin/env python3
"""Migration script to move session files from pause/ subdirectory to sessions/ root.

WHY: Flatten directory structure for consistency - move from .claude-mpm/sessions/pause/
to .claude-mpm/sessions/ to simplify file organization.

WHAT THIS DOES:
1. Finds all session files in .claude-mpm/sessions/pause/
2. Moves them to .claude-mpm/sessions/
3. Updates any references in LATEST-SESSION.txt
4. Creates backup before migration
5. Removes empty pause/ directory after successful migration

USAGE:
    python scripts/migrate_session_files.py [--dry-run] [--project-path PATH]

OPTIONS:
    --dry-run       Show what would be moved without actually moving files
    --project-path  Path to project root (default: current directory)
    --backup        Create backup before migration (default: True)
    --no-backup     Skip backup creation
"""

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple


def find_session_files(pause_dir: Path) -> List[Path]:
    """Find all session files in pause directory.

    Args:
        pause_dir: Path to pause directory

    Returns:
        List of session file paths
    """
    if not pause_dir.exists():
        return []

    session_files = []

    # Find all session-related files
    for pattern in ["session-*.json", "session-*.yaml", "session-*.md",
                    ".session-*.sha256", "LATEST-SESSION.txt", "*.md"]:
        session_files.extend(list(pause_dir.glob(pattern)))

    return session_files


def create_backup(pause_dir: Path) -> Path:
    """Create backup of pause directory.

    Args:
        pause_dir: Path to pause directory

    Returns:
        Path to backup directory
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_dir = pause_dir.parent / f"pause_backup_{timestamp}"

    print(f"Creating backup: {backup_dir}")
    shutil.copytree(pause_dir, backup_dir)

    return backup_dir


def move_files(source_files: List[Path], target_dir: Path, dry_run: bool = False) -> Tuple[int, int]:
    """Move files from pause/ to sessions/.

    Args:
        source_files: List of files to move
        target_dir: Target directory
        dry_run: If True, only show what would be moved

    Returns:
        Tuple of (successful_moves, failed_moves)
    """
    successful = 0
    failed = 0

    for source_file in source_files:
        target_file = target_dir / source_file.name

        # Skip if target already exists
        if target_file.exists():
            print(f"  ⚠️  SKIP: {source_file.name} (already exists in target)")
            continue

        try:
            if dry_run:
                print(f"  [DRY RUN] Would move: {source_file.name}")
                successful += 1
            else:
                shutil.move(str(source_file), str(target_file))
                print(f"  ✅ Moved: {source_file.name}")
                successful += 1
        except Exception as e:
            print(f"  ❌ FAILED: {source_file.name} - {e}")
            failed += 1

    return successful, failed


def update_latest_session_txt(sessions_dir: Path, dry_run: bool = False):
    """Update references in LATEST-SESSION.txt.

    Args:
        sessions_dir: Path to sessions directory
        dry_run: If True, only show what would be updated
    """
    latest_file = sessions_dir / "LATEST-SESSION.txt"

    if not latest_file.exists():
        return

    try:
        content = latest_file.read_text()

        # Replace references to pause/ subdirectory
        updated_content = content.replace(
            ".claude-mpm/sessions/pause/",
            ".claude-mpm/sessions/"
        )

        if content != updated_content:
            if dry_run:
                print("  [DRY RUN] Would update LATEST-SESSION.txt references")
            else:
                latest_file.write_text(updated_content)
                print("  ✅ Updated LATEST-SESSION.txt references")
    except Exception as e:
        print(f"  ⚠️  Failed to update LATEST-SESSION.txt: {e}")


def migrate_session_files(
    project_path: Path,
    dry_run: bool = False,
    create_backup_flag: bool = True
) -> int:
    """Main migration function.

    Args:
        project_path: Path to project root
        dry_run: If True, only show what would be done
        create_backup_flag: If True, create backup before migration

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    sessions_dir = project_path / ".claude-mpm" / "sessions"
    pause_dir = sessions_dir / "pause"

    print("=" * 80)
    print("Session Files Migration Tool")
    print("=" * 80)
    print(f"\nProject: {project_path}")
    print(f"Source:  {pause_dir}")
    print(f"Target:  {sessions_dir}")

    if dry_run:
        print("\n🔍 DRY RUN MODE - No files will be modified")

    print("\n" + "-" * 80)

    # Check if pause directory exists
    if not pause_dir.exists():
        print(f"\n✅ No migration needed - pause directory does not exist")
        return 0

    # Find all session files
    session_files = find_session_files(pause_dir)

    if not session_files:
        print(f"\n✅ No session files found in pause directory")
        if not dry_run:
            # Remove empty pause directory
            try:
                pause_dir.rmdir()
                print(f"  ✅ Removed empty pause directory")
            except Exception as e:
                print(f"  ⚠️  Could not remove pause directory: {e}")
        return 0

    print(f"\n📁 Found {len(session_files)} files to migrate:")
    for f in session_files:
        print(f"  - {f.name}")

    # Create backup if requested
    if create_backup_flag and not dry_run:
        print("\n📦 Creating backup...")
        backup_dir = create_backup(pause_dir)
        print(f"  ✅ Backup created: {backup_dir}")

    # Move files
    print(f"\n🚀 Moving files to {sessions_dir.name}/...")
    successful, failed = move_files(session_files, sessions_dir, dry_run)

    # Update LATEST-SESSION.txt
    print("\n📝 Updating references...")
    update_latest_session_txt(sessions_dir, dry_run)

    # Summary
    print("\n" + "=" * 80)
    print("Migration Summary")
    print("=" * 80)
    print(f"  Total files:      {len(session_files)}")
    print(f"  Successfully moved: {successful}")
    print(f"  Failed:            {failed}")

    # Remove empty pause directory
    if not dry_run and successful > 0:
        try:
            # Check if directory is empty
            remaining_files = list(pause_dir.glob("*"))
            if not remaining_files:
                pause_dir.rmdir()
                print(f"\n  ✅ Removed empty pause directory")
            else:
                print(f"\n  ⚠️  Pause directory not empty ({len(remaining_files)} files remain)")
        except Exception as e:
            print(f"\n  ⚠️  Could not remove pause directory: {e}")

    if dry_run:
        print("\n🔍 DRY RUN COMPLETE - Run without --dry-run to perform migration")
    else:
        print("\n✅ MIGRATION COMPLETE")

    print("=" * 80 + "\n")

    return 0 if failed == 0 else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate session files from pause/ to sessions/ root",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be moved
  python scripts/migrate_session_files.py --dry-run

  # Perform migration with backup
  python scripts/migrate_session_files.py

  # Migrate specific project
  python scripts/migrate_session_files.py --project-path /path/to/project

  # Migrate without backup (not recommended)
  python scripts/migrate_session_files.py --no-backup
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be moved without actually moving files"
    )

    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path.cwd(),
        help="Path to project root (default: current directory)"
    )

    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create backup before migration (default)"
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup creation"
    )

    args = parser.parse_args()

    # Resolve project path
    project_path = args.project_path.resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        return 1

    # Determine backup flag
    create_backup_flag = args.backup and not args.no_backup

    # Run migration
    return migrate_session_files(
        project_path=project_path,
        dry_run=args.dry_run,
        create_backup_flag=create_backup_flag
    )


if __name__ == "__main__":
    sys.exit(main())
