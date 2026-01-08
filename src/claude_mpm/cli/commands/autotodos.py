"""CLI commands for auto-generating todos from hook errors.

WHY this is needed:
- Convert hook errors into actionable todos for the PM
- Enable PM to delegate error resolution to appropriate agents
- Reduce manual todo creation overhead
- Maintain error visibility in the PM's workflow

DESIGN DECISION: Event-driven architecture
- Read from event log instead of hook_errors.json
- Event log provides clean separation between detection and consumption
- Supports multiple consumers (CLI, dashboard, notifications)
- Persistent storage with pending/resolved status tracking
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import click

from claude_mpm.services.event_log import get_event_log


def format_error_event_as_todo(event: Dict[str, Any]) -> Dict[str, str]:
    """Convert event log error event to todo format compatible with PM TodoWrite.

    Args:
        event: Event from event log with payload containing error details

    Returns:
        Dictionary with todo fields (content, activeForm, status)
    """
    payload = event.get("payload", {})
    error_type = payload.get("error_type", "unknown")
    hook_type = payload.get("hook_type", "unknown")
    details = payload.get("details", "")
    full_message = payload.get("full_message", "")

    # Create concise todo content
    content = f"Fix {hook_type} hook error: {error_type}"
    if details:
        content += f" ({details[:50]}{'...' if len(details) > 50 else ''})"

    # Active form for in-progress display
    active_form = f"Fixing {hook_type} hook error"

    return {
        "content": content,
        "activeForm": active_form,
        "status": "pending",
        "metadata": {
            "event_id": event.get("id", ""),
            "event_type": event.get("event_type", ""),
            "error_type": error_type,
            "hook_type": hook_type,
            "details": details,
            "full_message": full_message,
            "suggested_fix": payload.get("suggested_fix", ""),
            "timestamp": event.get("timestamp", ""),
        },
    }


def get_autotodos() -> List[Dict[str, Any]]:
    """Get all pending hook error events formatted as todos.

    Returns:
        List of todo dictionaries ready for PM injection
    """
    event_log = get_event_log()
    todos = []

    # Get all pending autotodo.error events
    pending_events = event_log.list_events(
        event_type="autotodo.error", status="pending"
    )

    for event in pending_events:
        todo = format_error_event_as_todo(event)
        todos.append(todo)

    return todos


@click.group(name="autotodos")
def autotodos_group():
    """Auto-generate todos from hook errors.

    This command converts hook errors into actionable todos that can be
    injected into the PM's todo list for delegation and resolution.

    Uses event-driven architecture - reads from event log instead of
    directly from hook error memory.
    """


@autotodos_group.command(name="status")
def show_autotodos_status():
    """Show autotodos status and statistics.

    Quick overview of pending hook errors and autotodos.

    Example:
        claude-mpm autotodos status
    """
    event_log = get_event_log()
    stats = event_log.get_stats()
    todos = get_autotodos()

    click.echo("\n📊 AutoTodos Status")
    click.echo("=" * 80)

    click.echo(f"Total Events: {stats['total_events']}")
    click.echo(f"Pending Todos: {len(todos)}")
    click.echo(f"Pending Events: {stats['by_status']['pending']}")
    click.echo(f"Resolved Events: {stats['by_status']['resolved']}")

    if stats.get("by_type"):
        click.echo("\n📋 Events by Type:")
        for event_type, count in stats["by_type"].items():
            click.echo(f"   {event_type}: {count}")

    click.echo(f"\n📁 Event Log: {stats['log_file']}")

    if todos:
        click.echo("\n⚠️  Action Required:")
        click.echo(f"   {len(todos)} hook error(s) need attention")
        click.echo("\nCommands:")
        click.echo("  claude-mpm autotodos list      # View pending todos")
        click.echo("  claude-mpm autotodos inject    # Inject into PM session")
        click.echo("  claude-mpm autotodos clear     # Clear after resolution")
    else:
        click.echo("\n✅ No pending todos. All hook errors are resolved!")


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
            click.echo(f"   Timestamp: {metadata.get('timestamp', 'Unknown')}")

            # Show suggested fix if available
            suggested_fix = metadata.get("suggested_fix", "")
            if suggested_fix:
                # Show first line of suggestion
                first_line = suggested_fix.split("\n")[0]
                click.echo(f"   Suggestion: {first_line}")

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
    "--event-id",
    help="Clear specific event by ID",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clear_autotodos(event_id, yes):
    """Clear hook errors after resolution.

    This marks resolved errors in the event log, removing them from
    the autotodos list.

    Examples:
        claude-mpm autotodos clear                 # Clear all pending
        claude-mpm autotodos clear --event-id ID   # Clear specific event
        claude-mpm autotodos clear -y              # Skip confirmation
    """
    event_log = get_event_log()

    if event_id:
        # Clear specific event
        if not yes:
            message = f"Clear event: {event_id}?"
            if not click.confirm(message):
                click.echo("Cancelled.")
                return

        # Mark as resolved
        if event_log.mark_resolved(event_id):
            click.echo(f"✅ Cleared event: {event_id}")
        else:
            click.echo(f"❌ Event not found: {event_id}")
    else:
        # Clear all pending autotodo.error events
        pending_events = event_log.list_events(
            event_type="autotodo.error", status="pending"
        )
        count = len(pending_events)

        if count == 0:
            click.echo("No pending events to clear.")
            return

        if not yes:
            message = f"Clear all {count} pending event(s)?"
            if not click.confirm(message):
                click.echo("Cancelled.")
                return

        # Mark all as resolved
        cleared = event_log.mark_all_resolved(event_type="autotodo.error")
        click.echo(f"✅ Cleared {cleared} event(s).")


# Register the command group
def register_commands(cli):
    """Register autotodos commands with CLI.

    Args:
        cli: Click CLI group to register commands with
    """
    cli.add_command(autotodos_group)
