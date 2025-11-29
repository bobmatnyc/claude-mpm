#!/usr/bin/env python3
"""Migrate ETag cache from JSON to SQLite.

This script migrates the legacy JSON-based ETag cache to the new SQLite-based
agent sync state database. It's designed to be safe and idempotent.

Usage:
    python scripts/migrate_etag_cache_to_sqlite.py [--dry-run] [--cache-dir PATH]

Examples:
    # Preview migration without making changes
    python scripts/migrate_etag_cache_to_sqlite.py --dry-run

    # Run migration with default cache directory
    python scripts/migrate_etag_cache_to_sqlite.py

    # Run migration with custom cache directory
    python scripts/migrate_etag_cache_to_sqlite.py --cache-dir /path/to/cache
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from claude_mpm.services.agents.sources.agent_sync_state import AgentSyncState

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def migrate_etag_cache(cache_dir: Path, dry_run: bool = False) -> dict:
    """Migrate ETag cache from JSON to SQLite.

    Args:
        cache_dir: Directory containing .etag-cache.json
        dry_run: If True, only show what would be migrated

    Returns:
        Dictionary with migration results:
        {
            "found": 10,           # Entries in old cache
            "migrated": 8,         # Successfully migrated
            "failed": 2,           # Failed migrations
            "dry_run": False,
            "backup_path": "..."   # Path to backup (if not dry run)
        }
    """
    etag_cache_file = cache_dir / ".etag-cache.json"

    if not etag_cache_file.exists():
        logger.warning(f"No ETag cache found at {etag_cache_file}")
        return {
            "found": 0,
            "migrated": 0,
            "failed": 0,
            "dry_run": dry_run,
            "error": "Cache file not found",
        }

    # Load old cache
    try:
        with etag_cache_file.open() as f:
            old_cache = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in ETag cache: {e}")
        return {
            "found": 0,
            "migrated": 0,
            "failed": 0,
            "dry_run": dry_run,
            "error": f"Invalid JSON: {e}",
        }

    logger.info(f"Found {len(old_cache)} entries in old ETag cache")

    if dry_run:
        logger.info("DRY RUN - would migrate:")
        for url, metadata in old_cache.items():
            etag = metadata.get("etag", "N/A")
            last_modified = metadata.get("last_modified", "N/A")
            logger.info(f"  {url}")
            logger.info(f"    ETag: {etag}")
            logger.info(f"    Last Modified: {last_modified}")

        return {"found": len(old_cache), "migrated": 0, "failed": 0, "dry_run": True}

    # Initialize new system
    sync_state = AgentSyncState()

    # Register default source (GitHub remote)
    source_id = "github-remote"
    source_url = "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main"

    # Check if source already exists
    existing_source = sync_state.get_source_info(source_id)
    if not existing_source:
        sync_state.register_source(source_id=source_id, url=source_url, enabled=True)
        logger.info(f"Registered source: {source_id}")
    else:
        logger.info(f"Source already exists: {source_id}")

    # Migrate entries
    migrated = 0
    failed = 0

    for url, metadata in old_cache.items():
        try:
            etag = metadata.get("etag")
            if etag:
                sync_state.update_source_sync_metadata(source_id=source_id, etag=etag)
                migrated += 1
                logger.debug(f"Migrated: {url}")
            else:
                logger.warning(f"No ETag for {url}, skipping")
                failed += 1
        except Exception as e:
            logger.error(f"Failed to migrate {url}: {e}")
            failed += 1

    logger.info(f"Migrated {migrated} ETag entries to SQLite")

    # Backup old cache
    backup_file = etag_cache_file.with_suffix(".json.backup")
    etag_cache_file.rename(backup_file)
    logger.info(f"Backed up old cache to {backup_file}")

    return {
        "found": len(old_cache),
        "migrated": migrated,
        "failed": failed,
        "dry_run": False,
        "backup_path": str(backup_file),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Migrate ETag cache from JSON to SQLite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview migration
  %(prog)s --dry-run

  # Run migration with default cache directory
  %(prog)s

  # Run migration with custom cache directory
  %(prog)s --cache-dir /path/to/cache
        """,
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".claude-mpm" / "cache" / "remote-agents",
        help="Cache directory (default: ~/.claude-mpm/cache/remote-agents/)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run migration
    logger.info("=" * 60)
    logger.info("ETag Cache Migration Tool")
    logger.info("=" * 60)
    logger.info(f"Cache directory: {args.cache_dir}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 60)

    result = migrate_etag_cache(args.cache_dir, dry_run=args.dry_run)

    # Print summary
    logger.info("=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    logger.info(f"Entries found: {result['found']}")
    logger.info(f"Entries migrated: {result['migrated']}")
    logger.info(f"Entries failed: {result['failed']}")

    if not args.dry_run and result.get("backup_path"):
        logger.info(f"Backup created: {result['backup_path']}")

    if result.get("error"):
        logger.error(f"Error: {result['error']}")
        return 1

    logger.info("=" * 60)

    if args.dry_run:
        logger.info("Dry run complete - no changes made")
    else:
        logger.info("Migration complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
