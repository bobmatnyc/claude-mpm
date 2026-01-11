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
            click.echo(f"No errors recorded for hook type: {hook_type}", err=True)
        else:
            click.echo("No errors recorded. Hook system is healthy! ✅", err=True)
        return

    if format == "json":
        # JSON output
        click.echo(json.dumps(errors, indent=2), err=True)
    else:
        # Table output
        click.echo("\n" + "=" * 80, err=True)
        click.echo("Hook Error Memory Report", err=True)
        click.echo("=" * 80, err=True)

        for key, data in errors.items():
            click.echo(f"\n🔴 Error: {data['type']}", err=True)
            click.echo(f"   Hook Type: {data['hook_type']}", err=True)
            click.echo(f"   Details: {data['details']}", err=True)
            click.echo(f"   Match: {data['match']}", err=True)
            click.echo(f"   Count: {data['count']} occurrences", err=True)
            click.echo(f"   First Seen: {data['first_seen']}", err=True)
            click.echo(f"   Last Seen: {data['last_seen']}", err=True)

        click.echo("\n" + "=" * 80, err=True)
        click.echo(f"Total unique errors: {len(errors)}", err=True)
        click.echo(f"Memory file: {error_memory.memory_file}", err=True)
        click.echo("\nTo clear errors: claude-mpm hook-errors clear", err=True)


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
        click.echo("No errors recorded. Hook system is healthy! ✅", err=True)
        return

    click.echo("\n" + "=" * 80, err=True)
    click.echo("Hook Error Summary", err=True)
    click.echo("=" * 80, err=True)
    click.echo("\n📊 Statistics:", err=True)
    click.echo(f"   Total Errors: {summary['total_errors']}", err=True)
    click.echo(f"   Unique Errors: {summary['unique_errors']}", err=True)

    if summary["errors_by_type"]:
        click.echo("\n🔍 Errors by Type:", err=True)
        for error_type, count in summary["errors_by_type"].items():
            click.echo(f"   {error_type}: {count}", err=True)

    if summary["errors_by_hook"]:
        click.echo("\n🎣 Errors by Hook Type:", err=True)
        for hook_type, count in summary["errors_by_hook"].items():
            click.echo(f"   {hook_type}: {count}", err=True)

    click.echo(f"\n📁 Memory File: {summary['memory_file']}", err=True)
    click.echo("\nFor detailed list: claude-mpm hook-errors list", err=True)


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
        click.echo(f"No errors to clear {scope}.", err=True)
        return

    # Confirm if not using -y flag
    if not yes:
        message = f"Clear {count} error(s) {scope}?"
        if not click.confirm(message):
            click.echo("Cancelled.", err=True)
            return

    # Clear errors
    error_memory.clear_errors(hook_type)

    click.echo(f"✅ Cleared {count} error(s) {scope}.", err=True)
    click.echo("\nHooks will be retried on next execution.", err=True)


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
            click.echo(f"No errors to diagnose for hook type: {hook_type}", err=True)
        else:
            click.echo("No errors to diagnose. Hook system is healthy! ✅", err=True)
        return

    click.echo("\n" + "=" * 80, err=True)
    click.echo("Hook Error Diagnostics", err=True)
    click.echo("=" * 80, err=True)

    for key, data in errors.items():
        click.echo(f"\n🔴 Error: {data['type']}", err=True)
        click.echo(f"   Hook: {data['hook_type']}", err=True)
        click.echo(f"   Count: {data['count']} failures", err=True)

        # Generate and show fix suggestion
        error_info = {
            "type": data["type"],
            "details": data["details"],
            "match": data["match"],
        }
        suggestion = error_memory.suggest_fix(error_info)

        click.echo("\n" + "-" * 80, err=True)
        click.echo(suggestion, err=True)
        click.echo("-" * 80, err=True)

    click.echo("\n" + "=" * 80, err=True)
    click.echo("After fixing issues, clear errors to retry:", err=True)
    click.echo("  claude-mpm hook-errors clear", err=True)


@hook_errors_group.command(name="status")
def show_status():
    """Show hook error memory status.

    Quick overview of hook error system state.

    Example:
        claude-mpm hook-errors status
    """
    error_memory = get_hook_error_memory()
    summary = error_memory.get_error_summary()

    click.echo("\n📊 Hook Error Memory Status", err=True)
    click.echo("=" * 80, err=True)

    if summary["total_errors"] == 0:
        click.echo("✅ Status: Healthy (no errors recorded)", err=True)
    else:
        click.echo(f"⚠️  Status: {summary['total_errors']} error(s) recorded", err=True)
        click.echo(f"   Unique errors: {summary['unique_errors']}", err=True)

        # Show which hooks are affected
        if summary["errors_by_hook"]:
            affected_hooks = list(summary["errors_by_hook"].keys())
            click.echo(f"   Affected hooks: {', '.join(affected_hooks)}", err=True)

    click.echo(f"\n📁 Memory file: {summary['memory_file']}", err=True)
    click.echo(f"   Exists: {Path(summary['memory_file']).exists()}", err=True)

    click.echo("\nCommands:", err=True)
    click.echo("  claude-mpm hook-errors list      # View detailed errors", err=True)
    click.echo("  claude-mpm hook-errors diagnose  # Get fix suggestions", err=True)
    click.echo("  claude-mpm hook-errors clear     # Clear and retry", err=True)


# Register the command group
def register_commands(cli):
    """Register hook error commands with CLI.

    Args:
        cli: Click CLI group to register commands with
    """
    cli.add_command(hook_errors_group)
