"""
Migrate command implementation for claude-mpm.

Provides a manual 'claude-mpm migrate' command that runs all pending
configuration migrations with verbose output. Primarily used for:
- Listing migrations with applied/pending status (--list)
- Previewing changes with --dry-run
- Running migrations on a specific project directory
- Re-running migrations after a failed startup migration
"""

import argparse
from pathlib import Path

from ..shared import BaseCommand, CommandResult


class MigrateCommand(BaseCommand):
    """Run pending configuration migrations."""

    def __init__(self) -> None:
        super().__init__("migrate")

    def validate_args(self, args: object) -> str | None:
        """Validate command arguments."""
        project_dir = getattr(args, "project_dir", None)
        if project_dir and not Path(project_dir).is_dir():
            return f"Directory does not exist: {project_dir}"
        return None

    def _list_migrations(self) -> CommandResult:
        """Show all registered migrations with applied/pending status."""
        from ...migrations.registry import MIGRATIONS
        from ...migrations.runner import _load_state

        state = _load_state()
        completed = set(state.get("completed", []))

        print("\nRegistered migrations:\n")
        print(f"  {'ID':<45} {'VERSION':<10} {'STATUS':<10} DESCRIPTION")
        print(f"  {'-' * 44} {'-' * 9} {'-' * 9} {'-' * 40}")

        for migration in MIGRATIONS:
            if migration.id in completed:
                marker = "applied"
            else:
                marker = "pending"
            print(
                f"  {migration.id:<45} {migration.version:<10} {marker:<10} {migration.description}"
            )

        total = len(MIGRATIONS)
        n_applied = sum(1 for m in MIGRATIONS if m.id in completed)
        n_pending = total - n_applied
        print(f"\nTotal: {total} ({n_applied} applied, {n_pending} pending)")

        return CommandResult.success_result(
            f"Listed {total} migrations ({n_applied} applied, {n_pending} pending)"
        )

    def run(self, args: object) -> CommandResult:
        """Execute pending migrations with verbose output."""
        list_only = getattr(args, "list", False)
        dry_run = getattr(args, "dry_run", False)
        project_dir = getattr(args, "project_dir", None)

        if list_only:
            return self._list_migrations()

        if project_dir:
            project_path = Path(project_dir).resolve()
        else:
            project_path = Path.cwd()

        print(f"\nRunning migrations for: {project_path}")
        if dry_run:
            print("[DRY RUN MODE - no changes will be made]\n")
        else:
            print()

        total_applied = 0
        total_errors = 0

        # --- Registry-based migrations ---
        from ...migrations.runner import get_pending_migrations, mark_migration_complete

        try:
            from ... import __version__ as current_version
        except ImportError:
            current_version = "unknown"

        pending = get_pending_migrations()

        if not pending:
            print("Registry migrations: all up to date\n")
        else:
            print(f"Registry migrations: {len(pending)} pending\n")

        for i, migration in enumerate(pending, start=1):
            label = f"{i}. [{migration.id}] {migration.description}"
            print(label)

            if dry_run:
                print(f"   Would run migration: {migration.id}")
                total_applied += 1
                continue

            try:
                success = migration.run()
                if success:
                    mark_migration_complete(migration.id, current_version)
                    print("   Applied")
                    total_applied += 1
                else:
                    print("   Skipped (migration returned False)")
            except Exception as e:
                print(f"   Error: {e}")
                total_errors += 1

        # --- Legacy binary consolidation migration (backward compat) ---
        # This migration is already in the registry as 5.12.0_binary_consolidation,
        # but we also expose the detailed output that the old command provided.
        # Only run it here if it was not already handled above (i.e., it was already
        # in the completed list when we started).
        from ...migrations.runner import _load_state

        state = _load_state()
        legacy_id = "5.12.0_binary_consolidation"
        if legacy_id in state.get("completed", []):
            # Already applied via registry; show detailed status from the module
            print("\nBinary consolidation (.mcp.json): already applied via registry")
        # If it was pending it would have been run above; no extra work needed.

        # Summary
        print(f"\nSummary: {total_applied} migrated, {total_errors} errors")

        if total_errors > 0:
            return CommandResult.error_result("Some migrations failed")

        if total_applied == 0:
            return CommandResult.success_result("All configurations are up to date")

        return CommandResult.success_result(
            f"Successfully applied {total_applied} migration(s)"
        )


def add_migrate_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add migrate command to CLI parser.

    Args:
        subparsers: The subparser action object to add the command to.
    """
    parser = subparsers.add_parser(
        "migrate",
        help="Run pending configuration migrations",
        description=(
            "Run all pending configuration migrations with verbose output. "
            "Use --list to see all migrations with status. "
            "Use --dry-run to preview changes without modifying files."
        ),
    )

    parser.add_argument(
        "--list",
        action="store_true",
        default=False,
        help="List all migrations with applied/pending status",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying any files",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=False,
        help="Auto-apply with no prompts (for CI use)",
    )
    parser.add_argument(
        "--project-dir",
        type=str,
        default=None,
        help="Project directory to migrate (default: current directory)",
    )


def manage_migrate(args: object) -> int:
    """Main entry point for migrate command."""
    command = MigrateCommand()
    result = command.execute(args)
    return result.exit_code
