#!/usr/bin/env python3
"""
Cache Directory Migration Script
==================================

Migrates agent cache from legacy `cache/agents/` to canonical `cache/remote-agents/`.

WHY: Research confirmed that `cache/remote-agents/` is the canonical cache location
with 26 active code references, while `cache/agents/` is legacy with only 7 references.
This migration consolidates to a single cache directory for consistency.

DESIGN DECISIONS:
- Safe migration: Creates backup before any changes
- Idempotent: Safe to run multiple times
- Merge strategy: Preserves newer files when conflicts exist
- Verification: Validates migration success before cleanup

USAGE:
    python scripts/migrate_cache_to_remote_agents.py [--dry-run] [--force]

OPTIONS:
    --dry-run    Preview migration without making changes
    --force      Skip confirmation prompts
"""

import argparse
import hashlib
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()
    with file_path.open("rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def files_identical(file1: Path, file2: Path) -> bool:
    """Check if two files are identical by comparing hashes.

    Args:
        file1: First file path
        file2: Second file path

    Returns:
        True if files have identical content
    """
    try:
        return get_file_hash(file1) == get_file_hash(file2)
    except Exception:
        return False


def discover_agent_files(cache_dir: Path) -> List[Path]:
    """Discover all agent files in cache directory (including nested).

    Args:
        cache_dir: Cache directory to scan

    Returns:
        List of agent file paths relative to cache_dir
    """
    agent_files = []

    if not cache_dir.exists():
        return agent_files

    for file_path in cache_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in {".md", ".json"}:
            # Skip special files
            if file_path.name in ["README.md", ".gitignore", ".etag-cache.json"]:
                continue
            agent_files.append(file_path.relative_to(cache_dir))

    return sorted(agent_files)


def create_backup(old_cache: Path, backup_dir: Path) -> bool:
    """Create backup of old cache before migration.

    Args:
        old_cache: Source directory to backup
        backup_dir: Destination backup directory

    Returns:
        True if backup successful
    """
    try:
        if old_cache.exists():
            print(f"📦 Creating backup: {backup_dir}")
            shutil.copytree(old_cache, backup_dir, dirs_exist_ok=True)
            print("✅ Backup created successfully")
            return True
        return True
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return False


def merge_caches(
    old_cache: Path, new_cache: Path, dry_run: bool = False
) -> Dict[str, List[str]]:
    """Merge old cache into new cache with conflict resolution.

    Strategy:
    - If file only in old: Copy to new
    - If file in both and identical: Skip (already migrated)
    - If file in both and different: Keep newer file (warn about conflict)

    Args:
        old_cache: Legacy cache directory (cache/agents/)
        new_cache: Canonical cache directory (cache/remote-agents/)
        dry_run: Preview migration without making changes

    Returns:
        Dictionary with migration results:
        {
            "copied": ["file1.md", ...],        # Newly copied files
            "skipped": ["file2.md", ...],       # Already identical
            "conflicts": ["file3.md", ...],     # Different versions found
            "errors": ["file4.md: error", ...]  # Copy failures
        }
    """
    results = {
        "copied": [],
        "skipped": [],
        "conflicts": [],
        "errors": [],
    }

    old_files = discover_agent_files(old_cache)

    if not old_files:
        return results

    print(f"\n📋 Found {len(old_files)} file(s) in legacy cache")

    for relative_path in old_files:
        old_file = old_cache / relative_path
        new_file = new_cache / relative_path

        try:
            if not new_file.exists():
                # File only in old cache - copy to new
                if not dry_run:
                    new_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(old_file, new_file)
                results["copied"].append(str(relative_path))
                print(f"  ➡️  {relative_path}")

            elif files_identical(old_file, new_file):
                # Files are identical - already migrated
                results["skipped"].append(str(relative_path))
                print(f"  ✓  {relative_path} (already migrated)")

            else:
                # Files differ - keep newer version
                old_mtime = old_file.stat().st_mtime
                new_mtime = new_file.stat().st_mtime

                if old_mtime > new_mtime:
                    # Old file is newer - copy to new (preserve newer version)
                    if not dry_run:
                        shutil.copy2(old_file, new_file)
                    results["conflicts"].append(str(relative_path))
                    print(
                        f"  ⚠️  {relative_path} (conflict - using newer version from old cache)"
                    )
                else:
                    # New file is newer - keep existing
                    results["conflicts"].append(str(relative_path))
                    print(
                        f"  ⚠️  {relative_path} (conflict - keeping newer version in new cache)"
                    )

        except Exception as e:
            error_msg = f"{relative_path}: {e}"
            results["errors"].append(error_msg)
            print(f"  ❌ {error_msg}")

    return results


def move_cache(old_cache: Path, new_cache: Path, dry_run: bool = False) -> bool:
    """Simple move operation when new cache doesn't exist.

    Args:
        old_cache: Legacy cache directory
        new_cache: Canonical cache directory
        dry_run: Preview migration without making changes

    Returns:
        True if move successful
    """
    try:
        print("\n📦 Moving cache from:")
        print(f"   {old_cache}")
        print(f"   → {new_cache}")

        if not dry_run:
            new_cache.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_cache), str(new_cache))

        print("✅ Cache moved successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to move cache: {e}")
        return False


def verify_migration(
    new_cache: Path, expected_files: List[str]
) -> Tuple[bool, List[str]]:
    """Verify migration success by checking files in new cache.

    Args:
        new_cache: Canonical cache directory
        expected_files: List of file paths that should exist

    Returns:
        Tuple of (success, missing_files)
    """
    missing = []

    for file_path in expected_files:
        if not (new_cache / file_path).exists():
            missing.append(file_path)

    return len(missing) == 0, missing


def create_migration_marker(cache_root: Path) -> bool:
    """Create marker file to prevent re-migration.

    Args:
        cache_root: Parent cache directory

    Returns:
        True if marker created successfully
    """
    try:
        marker_file = cache_root / ".migrated_to_remote_agents"
        marker_file.write_text(
            f"Migration completed: {datetime.now().isoformat()}\n"
            f"Legacy cache/agents/ migrated to cache/remote-agents/\n"
        )
        return True
    except Exception as e:
        print(f"⚠️  Warning: Could not create migration marker: {e}")
        return False


def main():
    """Main migration entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate agent cache from cache/agents/ to cache/remote-agents/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts",
    )

    args = parser.parse_args()

    # Define paths
    home = Path.home()
    old_cache = home / ".claude-mpm" / "cache" / "agents"
    new_cache = home / ".claude-mpm" / "cache" / "remote-agents"
    cache_root = home / ".claude-mpm" / "cache"
    backup_dir = (
        cache_root / f"agents.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    migration_marker = cache_root / ".migrated_to_remote_agents"

    print("=" * 70)
    print("CLAUDE MPM CACHE MIGRATION")
    print("=" * 70)
    print(f"\nMigrating from: {old_cache}")
    print(f"            to: {new_cache}")

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")

    # Check if already migrated
    if migration_marker.exists():
        print("\n✅ Migration already completed:")
        print(f"   Marker file: {migration_marker}")
        print("\n💡 If you want to re-migrate, delete the marker file and run again:")
        print(f"   rm {migration_marker}")
        return 0

    # Check if old cache exists
    if not old_cache.exists():
        print("\n✅ No legacy cache found at:")
        print(f"   {old_cache}")
        print("\nNothing to migrate. This system is already using the canonical cache.")
        return 0

    # Check for agent files in old cache
    old_files = discover_agent_files(old_cache)
    if not old_files:
        print("\n✅ Legacy cache is empty")
        print(f"   {old_cache}")
        print("\nNothing to migrate.")
        return 0

    # Show what will be migrated
    print("\n📊 Migration Summary:")
    print(f"   Files to migrate: {len(old_files)}")
    print(f"   New cache exists: {new_cache.exists()}")

    # Confirmation prompt (unless forced or dry-run)
    if not args.force and not args.dry_run:
        print("\n⚠️  This will migrate your agent cache to the canonical location.")
        print("   A backup will be created before any changes are made.")
        response = input("\nProceed with migration? [y/N]: ").strip().lower()
        if response not in ["y", "yes"]:
            print("\n❌ Migration cancelled by user")
            return 1

    # Create backup (skip for dry-run)
    if not args.dry_run:
        if not create_backup(old_cache, backup_dir):
            print("\n❌ Migration aborted: Backup failed")
            return 1

    # Perform migration
    if new_cache.exists():
        # Merge strategy: both caches exist
        print("\n📦 Both caches exist - merging with conflict resolution...")
        results = merge_caches(old_cache, new_cache, dry_run=args.dry_run)

        print("\n📊 Migration Results:")
        print(f"   Copied: {len(results['copied'])}")
        print(f"   Skipped (identical): {len(results['skipped'])}")
        print(f"   Conflicts resolved: {len(results['conflicts'])}")
        print(f"   Errors: {len(results['errors'])}")

        if results["errors"]:
            print("\n❌ Migration completed with errors:")
            for error in results["errors"]:
                print(f"   - {error}")
            return 1

    else:
        # Simple move: new cache doesn't exist
        print("\n📦 New cache doesn't exist - performing simple move...")
        if not move_cache(old_cache, new_cache, dry_run=args.dry_run):
            print("\n❌ Migration failed")
            return 1

    # Verify migration (skip for dry-run)
    if not args.dry_run:
        print("\n🔍 Verifying migration...")
        success, missing = verify_migration(new_cache, [str(f) for f in old_files])

        if not success:
            print(f"❌ Verification failed - {len(missing)} file(s) missing:")
            for file_path in missing:
                print(f"   - {file_path}")
            print(f"\n💡 Backup preserved at: {backup_dir}")
            return 1

        print("✅ Verification successful - all files migrated")

        # Create migration marker
        create_migration_marker(cache_root)

        # Final summary
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETE")
        print("=" * 70)
        print(f"\nNew cache location: {new_cache}")
        print(f"Backup location: {backup_dir}")
        print("\n💡 Next steps:")
        print("   1. Verify agents work correctly")
        print("   2. Run: claude-mpm agents list --system")
        print("   3. If everything works, you can safely remove:")
        print(f"      rm -rf {old_cache}")
        print(f"      rm -rf {backup_dir}")

    else:
        print("\n🔍 DRY RUN COMPLETE - No changes were made")
        print("\n💡 Run without --dry-run to perform the migration:")
        print(f"   python {sys.argv[0]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
