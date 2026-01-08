"""CLI commands for auto-generating todos from hook errors.

WHY this is needed:
- Convert hook errors into actionable todos for the PM
- Enable PM to delegate error resolution to appropriate agents
- Reduce manual todo creation overhead
- Maintain error visibility in the PM's workflow

DESIGN DECISION: Minimal POC approach
- Read from existing hook_errors.json (no new storage)
- Output in format compatible with PM TodoWrite
- Simple CLI for list/inject operations
- PM handles resolution by delegating to agents
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import click

from claude_mpm.core.hook_error_memory import get_hook_error_memory


def format_error_as_todo(error_key: str, error_data: Dict[str, Any]) -> Dict[str, str]:
    """Convert hook error to todo format compatible with PM TodoWrite.

    Args:
        error_key: Unique error identifier
        error_data: Error information from HookErrorMemory

    Returns:
        Dictionary with todo fields (content, activeForm, status)
    """
    error_type = error_data["type"]
    hook_type = error_data["hook_type"]
    details = error_data["details"]
    count = error_data["count"]

    # Create concise todo content
    content = f"Fix {hook_type} hook error: {error_type}"
    if details:
        content += f" ({details[:50]}{'...' if len(details) > 50 else ''})"

    # Add occurrence info if multiple failures
    if count > 1:
        content += f" [{count} occurrences]"

    # Active form for in-progress display
    active_form = f"Fixing {hook_type} hook error"

    return {
        "content": content,
        "activeForm": active_form,
        "status": "pending",
        "metadata": {
            "error_key": error_key,
            "error_type": error_type,
            "hook_type": hook_type,
            "details": details,
            "count": count,
            "first_seen": error_data.get("first_seen", ""),
            "last_seen": error_data.get("last_seen", ""),
        },
    }


def get_autotodos() -> List[Dict[str, Any]]:
    """Get all hook errors formatted as todos.

    Returns:
        List of todo dictionaries ready for PM injection
    """
    error_memory = get_hook_error_memory()
    todos = []

    for error_key, error_data in error_memory.errors.items():
        # Only include errors with 2+ occurrences (persistent issues)
        if error_data["count"] >= 2:
            todo = format_error_as_todo(error_key, error_data)
            todos.append(todo)

    return todos


@click.group(name="autotodos")
def autotodos_group():
    """Auto-generate todos from hook errors.

    This command converts hook errors into actionable todos that can be
    injected into the PM's todo list for delegation and resolution.
    """


@autotodos_group.command(name="list")
@click.option(
    "--format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format (table or json)",
)
def list_autotodos(format):
    """List all auto-generated todos from hook errors.

    Shows pending hook errors formatted as todos that can be acted upon
    by the PM.

    Examples:
        claude-mpm autotodos list
        claude-mpm autotodos list --format json
    """
    todos = get_autotodos()

    if not todos:
        click.echo("✅ No pending hook errors. All clear!")
        return

    if format == "json":
        # JSON output for programmatic use
        click.echo(json.dumps(todos, indent=2))
    else:
        # Table output for human readability
        click.echo("\n" + "=" * 80)
        click.echo("Auto-Generated Todos from Hook Errors")
        click.echo("=" * 80)

        for i, todo in enumerate(todos, 1):
            metadata = todo.get("metadata", {})
            click.echo(f"\n{i}. {todo['content']}")
            click.echo(f"   Status: {todo['status']}")
            click.echo(f"   Hook: {metadata.get('hook_type', 'Unknown')}")
            click.echo(f"   Error Type: {metadata.get('error_type', 'Unknown')}")
            click.echo(f"   First Seen: {metadata.get('first_seen', 'Unknown')}")
            click.echo(f"   Last Seen: {metadata.get('last_seen', 'Unknown')}")

        click.echo("\n" + "=" * 80)
        click.echo(f"Total: {len(todos)} pending todo(s)")
        click.echo("\nTo inject into PM session: claude-mpm autotodos inject")


@autotodos_group.command(name="inject")
@click.option(
    "--output",
    type=click.Path(),
    help="Output file path (default: stdout)",
)
def inject_autotodos(output):
    """Inject auto-generated todos in PM-compatible format.

    Outputs todos in a format that can be injected into the PM's
    session as system reminders.

    Examples:
        claude-mpm autotodos inject
        claude-mpm autotodos inject --output todos.json
    """
    todos = get_autotodos()

    if not todos:
        click.echo("✅ No pending hook errors to inject.", err=True)
        return

    # Format as system reminder for PM
    pm_message = {
        "type": "autotodos",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "todos": todos,
        "message": f"Found {len(todos)} hook error(s) requiring attention. "
        "Consider delegating to appropriate agents for resolution.",
    }

    output_json = json.dumps(pm_message, indent=2)

    if output:
        # Write to file
        output_path = Path(output)
        output_path.write_text(output_json)
        click.echo(f"✅ Injected {len(todos)} todo(s) to {output_path}", err=True)
    else:
        # Write to stdout for piping
        click.echo(output_json)


@autotodos_group.command(name="clear")
@click.option(
    "--error-key",
    help="Clear specific error by key",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clear_autotodos(error_key, yes):
    """Clear hook errors after resolution.

    This removes resolved errors from the autotodos list by clearing
    the underlying hook error memory.

    Examples:
        claude-mpm autotodos clear
        claude-mpm autotodos clear --error-key "command_not_found:PreToolUse:..."
        claude-mpm autotodos clear -y  # Skip confirmation
    """
    error_memory = get_hook_error_memory()

    if error_key:
        # Clear specific error
        if error_key not in error_memory.errors:
            click.echo(f"❌ Error key not found: {error_key}")
            return

        if not yes:
            error_data = error_memory.errors[error_key]
            message = f"Clear error: {error_data['type']} in {error_data['hook_type']}?"
            if not click.confirm(message):
                click.echo("Cancelled.")
                return

        # Remove specific error
        del error_memory.errors[error_key]
        error_memory._save_errors()
        click.echo(f"✅ Cleared error: {error_key}")
    else:
        # Clear all errors
        count = len(error_memory.errors)
        if count == 0:
            click.echo("No errors to clear.")
            return

        if not yes:
            message = f"Clear all {count} error(s)?"
            if not click.confirm(message):
                click.echo("Cancelled.")
                return

        error_memory.clear_errors()
        click.echo(f"✅ Cleared {count} error(s).")


@autotodos_group.command(name="status")
def show_autotodos_status():
    """Show autotodos status and statistics.

    Quick overview of pending hook errors and autotodos.

    Example:
        claude-mpm autotodos status
    """
    todos = get_autotodos()
    error_memory = get_hook_error_memory()
    summary = error_memory.get_error_summary()

    click.echo("\n📊 AutoTodos Status")
    click.echo("=" * 80)

    click.echo(f"Total Errors: {summary['total_errors']}")
    click.echo(f"Pending Todos: {len(todos)} (errors with 2+ occurrences)")
    click.echo(f"Unique Errors: {summary['unique_errors']}")

    if summary.get("errors_by_hook"):
        click.echo("\n🎣 Errors by Hook Type:")
        for hook_type, count in summary["errors_by_hook"].items():
            click.echo(f"   {hook_type}: {count}")

    # Memory file path from error_memory instance, not summary
    click.echo(f"\n📁 Memory File: {error_memory.memory_file}")

    if todos:
        click.echo("\n⚠️  Action Required:")
        click.echo(f"   {len(todos)} hook error(s) need attention")
        click.echo("\nCommands:")
        click.echo("  claude-mpm autotodos list      # View pending todos")
        click.echo("  claude-mpm autotodos inject    # Inject into PM session")
        click.echo("  claude-mpm autotodos clear     # Clear after resolution")
    else:
        click.echo("\n✅ No pending todos. All hook errors are resolved!")


# Register the command group
def register_commands(cli):
    """Register autotodos commands with CLI.

    Args:
        cli: Click CLI group to register commands with
    """
    cli.add_command(autotodos_group)
