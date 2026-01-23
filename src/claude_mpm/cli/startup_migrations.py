"""
Startup migrations for claude-mpm.

This module provides a migration registry pattern for automatically fixing
configuration issues on first startup after an update. Migrations run once
and are tracked in ~/.claude-mpm/migrations.yaml.

Design Principles:
- Non-blocking: Failures log warnings but don't stop startup
- Idempotent: Safe to run multiple times (check before migrate)
- Tracked: Each migration runs only once per installation
- Early: Runs before agent sync in startup sequence
"""

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

from ..core.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class Migration:
    """Definition of a startup migration."""

    id: str
    description: str
    check: Callable[[], bool]  # Returns True if migration is needed
    migrate: Callable[[], bool]  # Returns True if migration succeeded


def _get_migrations_file() -> Path:
    """Get path to migrations tracking file."""
    return Path.home() / ".claude-mpm" / "migrations.yaml"


def _load_completed_migrations() -> dict:
    """Load completed migrations from tracking file.

    Returns:
        Dictionary with completed migrations data.
    """
    migrations_file = _get_migrations_file()
    if not migrations_file.exists():
        return {"migrations": []}

    try:
        with open(migrations_file) as f:
            data = yaml.safe_load(f) or {}
            return data if "migrations" in data else {"migrations": []}
    except Exception as e:
        logger.debug(f"Failed to load migrations file: {e}")
        return {"migrations": []}


def _save_completed_migration(migration_id: str) -> None:
    """Save a completed migration to tracking file.

    Args:
        migration_id: The ID of the completed migration.
    """
    migrations_file = _get_migrations_file()
    migrations_file.parent.mkdir(parents=True, exist_ok=True)

    data = _load_completed_migrations()

    # Add new migration entry
    data["migrations"].append(
        {"id": migration_id, "completed_at": datetime.now(timezone.utc).isoformat()}
    )

    try:
        with open(migrations_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False)
    except Exception as e:
        logger.warning(f"Failed to save migration tracking: {e}")


def _is_migration_completed(migration_id: str) -> bool:
    """Check if a migration has already been completed.

    Args:
        migration_id: The ID of the migration to check.

    Returns:
        True if the migration has been completed.
    """
    data = _load_completed_migrations()
    completed_ids = [m.get("id") for m in data.get("migrations", [])]
    return migration_id in completed_ids


# =============================================================================
# Migration: v5.6.76-cache-dir-rename
# =============================================================================


def _check_cache_dir_rename_needed() -> bool:
    """Check if cache directory rename is needed.

    Returns:
        True if ~/.claude-mpm/cache/remote-agents/ exists.
    """
    old_cache_dir = Path.home() / ".claude-mpm" / "cache" / "remote-agents"
    return old_cache_dir.exists()


def _migrate_cache_dir_rename() -> bool:
    """Rename remote-agents cache directory to agents.

    This migration:
    1. Moves ~/.claude-mpm/cache/remote-agents/ contents to ~/.claude-mpm/cache/agents/
    2. Removes the old remote-agents directory
    3. Updates configuration.yaml if it references the old path

    Returns:
        True if migration succeeded.
    """
    old_cache_dir = Path.home() / ".claude-mpm" / "cache" / "remote-agents"
    new_cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"

    try:
        # Step 1: Move directory contents
        if old_cache_dir.exists():
            # Ensure parent directory exists
            new_cache_dir.parent.mkdir(parents=True, exist_ok=True)

            if new_cache_dir.exists():
                # Merge: move contents from old to new
                for item in old_cache_dir.iterdir():
                    dest = new_cache_dir / item.name
                    if not dest.exists():
                        shutil.move(str(item), str(dest))
                # Remove old directory after moving contents
                shutil.rmtree(old_cache_dir, ignore_errors=True)
            else:
                # Simple rename if new dir doesn't exist
                shutil.move(str(old_cache_dir), str(new_cache_dir))

            logger.debug(
                f"Moved cache directory from {old_cache_dir} to {new_cache_dir}"
            )

        # Step 2: Update configuration.yaml if needed
        _update_configuration_cache_path()

        return True

    except Exception as e:
        logger.warning(f"Cache directory migration failed: {e}")
        return False


def _update_configuration_cache_path() -> None:
    """Update configuration.yaml to use new cache path if it references old path."""
    config_file = Path.home() / ".claude-mpm" / "configuration.yaml"
    if not config_file.exists():
        return

    try:
        with open(config_file) as f:
            content = f.read()

        old_path_pattern = "/.claude-mpm/cache/remote-agents"
        new_path_pattern = "/.claude-mpm/cache/agents"

        if old_path_pattern in content:
            updated_content = content.replace(old_path_pattern, new_path_pattern)
            with open(config_file, "w") as f:
                f.write(updated_content)
            logger.debug("Updated configuration.yaml cache_dir path")

    except Exception as e:
        logger.debug(f"Failed to update configuration.yaml: {e}")


# =============================================================================
# Migration Registry
# =============================================================================

MIGRATIONS: list[Migration] = [
    Migration(
        id="v5.6.76-cache-dir-rename",
        description="Rename remote-agents cache dir to agents",
        check=_check_cache_dir_rename_needed,
        migrate=_migrate_cache_dir_rename,
    ),
]


def run_migrations() -> None:
    """Run all pending startup migrations.

    This function:
    1. Iterates through the migration registry
    2. Skips already-completed migrations
    3. Checks if each migration is needed
    4. Runs the migration if needed
    5. Tracks completed migrations

    Errors are logged but do not stop startup.
    """
    for migration in MIGRATIONS:
        try:
            # Skip if already completed
            if _is_migration_completed(migration.id):
                continue

            # Check if migration is needed
            if not migration.check():
                # Mark as completed even if not needed (condition doesn't apply)
                _save_completed_migration(migration.id)
                continue

            # Run the migration
            print(f"⚙️  Running startup migration: {migration.description}")
            logger.info(f"Running startup migration: {migration.id}")

            success = migration.migrate()

            if success:
                _save_completed_migration(migration.id)
                logger.info(f"Migration {migration.id} completed successfully")
            else:
                logger.warning(f"Migration {migration.id} failed")

        except Exception as e:
            # Non-blocking: log and continue
            logger.warning(f"Migration {migration.id} error: {e}")
            continue
