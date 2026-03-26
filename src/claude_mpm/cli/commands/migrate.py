"""
Migrate command implementation for claude-mpm.

Provides a manual 'claude-mpm migrate' command that runs all pending
configuration migrations with verbose output. Primarily used for:
- Previewing changes with --dry-run
- Running migrations on a specific project directory
- Re-running migrations after a failed startup migration
"""

import argparse
from pathlib import Path

from ..shared import BaseCommand, CommandResult


class MigrateCommand(BaseCommand):
    """Run pending configuration migrations."""

    def __init__(self):
        super().__init__("migrate")

    def validate_args(self, args) -> str | None:
        """Validate command arguments."""
        project_dir = getattr(args, "project_dir", None)
        if project_dir and not Path(project_dir).is_dir():
            return f"Directory does not exist: {project_dir}"
        return None

    def run(self, args) -> CommandResult:
        """Execute all pending migrations with verbose output."""
        dry_run = getattr(args, "dry_run", False)
        project_dir = getattr(args, "project_dir", None)

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

        # Run binary consolidation migration
        print("1. Binary consolidation (.mcp.json)")
        print("   Migrates old binary/module invocations to 'claude-mpm mcp serve'")
        try:
            from ...migrations.migrate_binary_consolidation import migrate_mcp_json

            result = migrate_mcp_json(project_path, dry_run=dry_run)

            if result["migrated"]:
                for name, desc in result["migrated"]:
                    action = "Would migrate" if dry_run else "Migrated"
                    print(f"   {action}: '{name}' ({desc})")
                if result.get("backup_path"):
                    print(f"   Backup: {result['backup_path']}")
                total_applied += len(result["migrated"])
            elif result["errors"]:
                for error in result["errors"]:
                    print(f"   Error: {error}")
                total_errors += len(result["errors"])
            else:
                print("   Already up to date")

            if result["skipped"]:
                print(f"   Skipped (already migrated): {', '.join(result['skipped'])}")
            if result["unchanged"]:
                print(f"   Unchanged (non-MPM): {', '.join(result['unchanged'])}")

        except Exception as e:
            print(f"   Error: {e}")
            total_errors += 1

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
            "Use --dry-run to preview changes without modifying files."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying any files",
    )
    parser.add_argument(
        "--project-dir",
        type=str,
        default=None,
        help="Project directory to migrate (default: current directory)",
    )


def manage_migrate(args) -> int:
    """Main entry point for migrate command."""
    command = MigrateCommand()
    result = command.execute(args)
    return result.exit_code
