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


def _run_remove_unsupported_hooks_migration() -> bool:
    """Remove v2.1.47+ hook events from settings on older Claude Code installs."""
    from .migrate_remove_unsupported_hooks import migrate_all_settings

    return migrate_all_settings()


def _run_binary_consolidation_migration() -> bool:
    """Migrate .mcp.json to consolidated 'claude-mpm mcp serve' format."""
    from .migrate_binary_consolidation import run_migration

    return run_migration()


def _run_core_skills_to_user_level_migration() -> bool:
    """Move CORE mpm-* skills to user level, remove project-level duplicates."""
    from .migrate_core_skills_to_user_level import run_migration

    return run_migration()


def _run_core_agents_to_user_level_migration() -> bool:
    """Move CORE agents to user level, remove project-level duplicates."""
    from .migrate_core_agents_to_user_level import run_migration

    return run_migration()


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
        description="Update Co-Authored-By to Claude MPM <https://github.com/bobmatnyc/claude-mpm>",
        run=_run_coauthor_email_migration,
    ),
    Migration(
        id="5.9.48_remove_unsupported_hooks",
        version="5.9.48",
        description="Remove unsupported v2.1.47+ hook events (WorktreeCreate, WorktreeRemove, TeammateIdle, TaskCompleted, ConfigChange) from Claude settings on older Claude Code installations",
        run=_run_remove_unsupported_hooks_migration,
    ),
    Migration(
        id="5.12.0_binary_consolidation",
        version="5.12.0",
        description="Migrate .mcp.json to consolidated 'claude-mpm mcp serve' format",
        run=_run_binary_consolidation_migration,
    ),
    Migration(
        id="6.1.0_core_skills_to_user_level",
        version="6.1.0",
        description="Move CORE mpm-* skills to user level, remove project-level duplicates",
        run=_run_core_skills_to_user_level_migration,
    ),
    Migration(
        id="6.2.0_core_agents_to_user_level",
        version="6.2.0",
        description="Move CORE agents to user level, remove project-level duplicates",
        run=_run_core_agents_to_user_level_migration,
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
