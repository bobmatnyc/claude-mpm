"""
Migration runner for version-based migrations.

Tracks completed migrations and runs pending ones on startup.
State is stored in ~/.claude-mpm/migrations.json
"""

import json
import logging
from pathlib import Path

from .registry import MIGRATIONS, Migration

logger = logging.getLogger(__name__)

# State file location
STATE_FILE = Path.home() / ".claude-mpm" / "migrations.json"


def _load_state() -> dict:
    """Load migration state from disk.

    Returns:
        State dict with 'completed' list and 'last_version'
    """
    if not STATE_FILE.exists():
        return {"completed": [], "last_version": None}

    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"completed": [], "last_version": None}


def _save_state(state: dict) -> None:
    """Save migration state to disk.

    Args:
        state: State dict to save
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_pending_migrations() -> list[Migration]:
    """Get migrations that should run this startup.

    Includes:
      * One-shot migrations that haven't been recorded in the completed list.
      * All ``run_always`` migrations regardless of completion state.

    ``run_always`` migrations are expected to be cheap and idempotent — see
    :class:`Migration` for the contract.
    """
    state = _load_state()
    completed = set(state.get("completed", []))

    return [m for m in MIGRATIONS if m.run_always or m.id not in completed]


def mark_migration_complete(migration_id: str, version: str) -> None:
    """Mark a migration as completed.

    Args:
        migration_id: The migration ID to mark complete
        version: The current version
    """
    state = _load_state()

    if "completed" not in state:
        state["completed"] = []

    if migration_id not in state["completed"]:
        state["completed"].append(migration_id)

    state["last_version"] = version
    _save_state(state)


def run_pending_migrations(current_version: str | None = None) -> int:
    """Run all pending migrations.

    This is the main entry point called on startup. It's designed to be
    fast for already-migrated installs (just a file check).

    Args:
        current_version: Current package version (for state tracking)

    Returns:
        Number of migrations run
    """
    pending = get_pending_migrations()

    if not pending:
        return 0

    # Get version if not provided
    if current_version is None:
        try:
            from .. import __version__

            current_version = __version__
        except ImportError:
            current_version = "unknown"

    count = 0
    for migration in pending:
        # run_always migrations are silent probes (e.g., daemon autodetect):
        # avoid noisy output on every startup.
        #
        # For all other migrations, we only emit user-facing output when a
        # migration actually APPLIES a change (run() returns True). Many
        # migrations are "scan-and-repair-if-present" probes (e.g.
        # fix_mcp_command_args, fix_trusty_memory_bridge) that return False on a
        # clean system and are re-run every launch. Printing "Running
        # migration..." up front — or "Migration skipped" on a clean no-op —
        # produced cosmetic noise on every startup (issue #595). We therefore
        # log/print only on the applied path; a clean no-op (False) is silent
        # except for a debug trace. Genuine errors (run() raises) stay visible.
        verbose = not migration.run_always

        try:
            success = migration.run()
            if success:
                if not migration.run_always:
                    # Only persist completion for one-shot migrations.
                    mark_migration_complete(migration.id, current_version)
                logger.info(f"Migration applied: {migration.description}")
                if verbose:
                    print(f"🔄 Migration applied: {migration.description}")
                    print(f"✅ Migration complete: {migration.id}")
                count += 1
            else:
                # No-op clean scan: nothing to fix. Keep a debug trace only —
                # no user-facing stdout (issue #595).
                logger.debug(f"Migration returned False (no-op): {migration.id}")
        except Exception as e:
            # Always surface failures, even for run_always migrations.
            logger.error(f"Migration failed: {migration.id}: {e}")
            if verbose:
                print(f"❌ Migration failed: {migration.id}: {e}")
            # Continue with other migrations

    return count


def get_migration_status() -> dict:
    """Get current migration status for diagnostics.

    Returns:
        Dict with completed, pending, and last_version info
    """
    state = _load_state()
    pending = get_pending_migrations()

    return {
        "completed": state.get("completed", []),
        "pending": [m.id for m in pending],
        "last_version": state.get("last_version"),
        "total_registered": len(MIGRATIONS),
    }
