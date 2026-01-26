"""Migrations for claude-mpm configuration updates.

Version-based migrations run automatically on first startup of a new version.
Each migration runs once and is tracked in ~/.claude-mpm/migrations.json.

Usage:
    # Run migrations manually
    python -m claude_mpm.migrations.migrate_async_hooks

    # Check migration status
    from claude_mpm.migrations.runner import get_migration_status
    print(get_migration_status())
"""

from .runner import get_migration_status, run_pending_migrations

__all__ = ["get_migration_status", "run_pending_migrations"]
