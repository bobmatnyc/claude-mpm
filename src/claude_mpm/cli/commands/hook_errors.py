"""CLI commands for managing hook error memory.

WHY this command is needed:
- Users need visibility into what hooks are failing
- Must be able to clear error memory to retry failed hooks
- Provides diagnostics for troubleshooting
- Makes error memory accessible without manual file editing
"""

import json
from pathlib import Path

import click

from claude_mpm.core.hook_error_memory import get_hook_error_memory


@click.group(name="hook-errors")
def hook_errors_group():
    """Manage hook error memory and diagnostics.

    The hook error memory system tracks failing hooks to prevent
    repeated execution of known-failing operations.
    """


@hook_errors_group.command(name="list")
@click.option(
    "--format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format (table or json)",
)
@click.option(
    "--hook-type",
    help="Filter by hook type (e.g., PreToolUse, PostToolUse)",
)
def list_errors(format, hook_type):
    """List all recorded hook errors.

    Shows errors that have been detected during hook execution,
    including failure counts and last seen timestamps.

    Examples:
        claude-mpm hook-errors list
        claude-mpm hook-errors list --format json
        claude-mpm hook-errors list --hook-type PreToolUse
    """
    error_memory = get_hook_error_memory()

    # Filter errors if hook type specified
    errors = error_memory.errors
    if hook_type:
        errors = {
            key: data for key, data in errors.items() if data["hook_type"] == hook_type
        }

    if not errors:
        if hook_type:
            click.echo(f"No errors recorded for hook type: {hook_type}")
        else:
            click.echo("No errors recorded. Hook system is healthy! ✅")
        return

    if format == "json":
        # JSON output
        click.echo(json.dumps(errors, indent=2))
    else:
        # Table output
        click.echo("\n" + "=" * 80)
        click.echo("Hook Error Memory Report")
        click.echo("=" * 80)

        for key, data in errors.items():
            click.echo(f"\n🔴 Error: {data['type']}")
            click.echo(f"   Hook Type: {data['hook_type']}")
            click.echo(f"   Details: {data['details']}")
            click.echo(f"   Match: {data['match']}")
            click.echo(f"   Count: {data['count']} occurrences")
            click.echo(f"   First Seen: {data['first_seen']}")
            click.echo(f"   Last Seen: {data['last_seen']}")

        click.echo("\n" + "=" * 80)
        click.echo(f"Total unique errors: {len(errors)}")
        click.echo(f"Memory file: {error_memory.memory_file}")
        click.echo("\nTo clear errors: claude-mpm hook-errors clear")


@hook_errors_group.command(name="summary")
def show_summary():
    """Show summary statistics of hook errors.

    Provides overview of error counts by type and hook type.

    Example:
        claude-mpm hook-errors summary
    """
    error_memory = get_hook_error_memory()
    summary = error_memory.get_error_summary()

    if summary["total_errors"] == 0:
        click.echo("No errors recorded. Hook system is healthy! ✅")
        return

    click.echo("\n" + "=" * 80)
    click.echo("Hook Error Summary")
    click.echo("=" * 80)
    click.echo("\n📊 Statistics:")
    click.echo(f"   Total Errors: {summary['total_errors']}")
    click.echo(f"   Unique Errors: {summary['unique_errors']}")

    if summary["errors_by_type"]:
        click.echo("\n🔍 Errors by Type:")
        for error_type, count in summary["errors_by_type"].items():
            click.echo(f"   {error_type}: {count}")

    if summary["errors_by_hook"]:
        click.echo("\n🎣 Errors by Hook Type:")
        for hook_type, count in summary["errors_by_hook"].items():
            click.echo(f"   {hook_type}: {count}")

    click.echo(f"\n📁 Memory File: {summary['memory_file']}")
    click.echo("\nFor detailed list: claude-mpm hook-errors list")


@hook_errors_group.command(name="clear")
@click.option(
    "--hook-type",
    help="Clear errors only for specific hook type",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clear_errors(hook_type, yes):
    """Clear hook error memory to allow retry.

    This removes error records, allowing previously failing hooks
    to be executed again. Use this after fixing the underlying issue.

    Examples:
        claude-mpm hook-errors clear
        claude-mpm hook-errors clear --hook-type PreToolUse
        claude-mpm hook-errors clear -y  # Skip confirmation
    """
    error_memory = get_hook_error_memory()

    # Count errors to be cleared
    if hook_type:
        count = sum(
            1 for data in error_memory.errors.values() if data["hook_type"] == hook_type
        )
        scope = f"for hook type '{hook_type}'"
    else:
        count = len(error_memory.errors)
        scope = "all hook types"

    if count == 0:
        click.echo(f"No errors to clear {scope}.")
        return

    # Confirm if not using -y flag
    if not yes:
        message = f"Clear {count} error(s) {scope}?"
        if not click.confirm(message):
            click.echo("Cancelled.")
            return

    # Clear errors
    error_memory.clear_errors(hook_type)

    click.echo(f"✅ Cleared {count} error(s) {scope}.")
    click.echo("\nHooks will be retried on next execution.")


@hook_errors_group.command(name="diagnose")
@click.argument("hook_type", required=False)
def diagnose_errors(hook_type):
    """Diagnose hook errors and suggest fixes.

    Provides detailed diagnostics and actionable suggestions for
    resolving hook errors.

    Arguments:
        HOOK_TYPE: Optional hook type to diagnose (e.g., PreToolUse)

    Examples:
        claude-mpm hook-errors diagnose
        claude-mpm hook-errors diagnose PreToolUse
    """
    error_memory = get_hook_error_memory()

    # Filter errors if hook type specified
    errors = error_memory.errors
    if hook_type:
        errors = {
            key: data for key, data in errors.items() if data["hook_type"] == hook_type
        }

    if not errors:
        if hook_type:
            click.echo(f"No errors to diagnose for hook type: {hook_type}")
        else:
            click.echo("No errors to diagnose. Hook system is healthy! ✅")
        return

    click.echo("\n" + "=" * 80)
    click.echo("Hook Error Diagnostics")
    click.echo("=" * 80)

    for key, data in errors.items():
        click.echo(f"\n🔴 Error: {data['type']}")
        click.echo(f"   Hook: {data['hook_type']}")
        click.echo(f"   Count: {data['count']} failures")

        # Generate and show fix suggestion
        error_info = {
            "type": data["type"],
            "details": data["details"],
            "match": data["match"],
        }
        suggestion = error_memory.suggest_fix(error_info)

        click.echo("\n" + "-" * 80)
        click.echo(suggestion)
        click.echo("-" * 80)

    click.echo("\n" + "=" * 80)
    click.echo("After fixing issues, clear errors to retry:")
    click.echo("  claude-mpm hook-errors clear")


@hook_errors_group.command(name="status")
def show_status():
    """Show hook error memory status.

    Quick overview of hook error system state.

    Example:
        claude-mpm hook-errors status
    """
    error_memory = get_hook_error_memory()
    summary = error_memory.get_error_summary()

    click.echo("\n📊 Hook Error Memory Status")
    click.echo("=" * 80)

    if summary["total_errors"] == 0:
        click.echo("✅ Status: Healthy (no errors recorded)")
    else:
        click.echo(f"⚠️  Status: {summary['total_errors']} error(s) recorded")
        click.echo(f"   Unique errors: {summary['unique_errors']}")

        # Show which hooks are affected
        if summary["errors_by_hook"]:
            affected_hooks = list(summary["errors_by_hook"].keys())
            click.echo(f"   Affected hooks: {', '.join(affected_hooks)}")

    click.echo(f"\n📁 Memory file: {summary['memory_file']}")
    click.echo(f"   Exists: {Path(summary['memory_file']).exists()}")

    click.echo("\nCommands:")
    click.echo("  claude-mpm hook-errors list      # View detailed errors")
    click.echo("  claude-mpm hook-errors diagnose  # Get fix suggestions")
    click.echo("  claude-mpm hook-errors clear     # Clear and retry")


# Register the command group
def register_commands(cli):
    """Register hook error commands with CLI.

    Args:
        cli: Click CLI group to register commands with
    """
    cli.add_command(hook_errors_group)
