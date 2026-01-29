"""
Migration registry for version-based migrations.

Migrations are registered by version and run automatically on first startup
of that version. Each migration runs once and is tracked in state file.
"""

from collections.abc import Callable
from typing import NamedTuple


class Migration(NamedTuple):
    """A migration definition."""

    id: str  # Unique identifier (e.g., "5.6.91_async_hooks")
    version: str  # Version this migration applies to
    description: str  # Human-readable description
    run: Callable[[], bool]  # Function that returns True on success


def _run_async_hooks_migration() -> bool:
    """Run the async hooks migration."""
    from .migrate_async_hooks import migrate_all_settings

    return migrate_all_settings()


def _run_coauthor_email_migration() -> bool:
    """Run the co-author email migration."""
    from .migrate_coauthor_email import migrate_coauthor_email

    return migrate_coauthor_email()


# Registry of all migrations, ordered by version
MIGRATIONS: list[Migration] = [
    Migration(
        id="5.6.91_async_hooks",
        version="5.6.91",
        description="Migrate hooks to async execution mode",
        run=_run_async_hooks_migration,
    ),
    Migration(
        id="5.6.95_coauthor_email",
        version="5.6.95",
        description="Update Co-Authored-By to Claude MPM <claude-mpm@matsuoka.com>",
        run=_run_coauthor_email_migration,
    ),
]


def get_migrations_for_version(version: str) -> list[Migration]:
    """Get all migrations that should run for a given version.

    Args:
        version: The target version (e.g., "5.6.91")

    Returns:
        List of migrations for that version
    """
    return [m for m in MIGRATIONS if m.version == version]


def get_all_migrations() -> list[Migration]:
    """Get all registered migrations."""
    return MIGRATIONS.copy()
