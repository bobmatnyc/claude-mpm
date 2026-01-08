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

from claude_mpm.services.delegation_detector import get_delegation_detector
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


def format_delegation_event_as_todo(event: Dict[str, Any]) -> Dict[str, str]:
    """Convert event log delegation event to todo format compatible with PM TodoWrite.

    Args:
        event: Event from event log with payload containing delegation details

    Returns:
        Dictionary with todo fields (content, activeForm, status)
    """
    payload = event.get("payload", {})
    pattern_type = payload.get("pattern_type", "Task")
    suggested_todo = payload.get("suggested_todo", "")
    action = payload.get("action", "")
    original_text = payload.get("original_text", "")

    # Create concise todo content
    content = f"[Delegation] {suggested_todo}"

    # Active form for in-progress display
    active_form = f"Delegating: {action[:30]}..."

    return {
        "content": content,
        "activeForm": active_form,
        "status": "pending",
        "metadata": {
            "event_id": event.get("id", ""),
            "event_type": event.get("event_type", ""),
            "pattern_type": pattern_type,
            "suggested_todo": suggested_todo,
            "action": action,
            "original_text": original_text,
            "timestamp": event.get("timestamp", ""),
        },
    }


def get_autotodos() -> List[Dict[str, Any]]:
    """Get all pending hook error events formatted as todos.

    DESIGN DECISION: Only autotodo.error events are returned
    - autotodo.error = Script/coding failures → PM should delegate fix
    - pm.violation = Delegation anti-patterns → PM behavior error (not todo)

    Returns:
        List of todo dictionaries ready for PM injection
    """
    event_log = get_event_log()
    todos = []

    # Get all pending autotodo.error events (script failures)
    pending_error_events = event_log.list_events(
        event_type="autotodo.error", status="pending"
    )

    for event in pending_error_events:
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

    Quick overview of pending hook errors, PM violations, and autotodos.

    Example:
        claude-mpm autotodos status
    """
    event_log = get_event_log()
    stats = event_log.get_stats()
    todos = get_autotodos()
    violations = event_log.list_events(event_type="pm.violation", status="pending")

    click.echo("\n📊 AutoTodos Status")
    click.echo("=" * 80)

    click.echo(f"Total Events: {stats['total_events']}")
    click.echo(f"Pending Todos (script errors): {len(todos)}")
    click.echo(f"Pending Violations (PM errors): {len(violations)}")
    click.echo(f"Total Pending Events: {stats['by_status']['pending']}")
    click.echo(f"Resolved Events: {stats['by_status']['resolved']}")

    if stats.get("by_type"):
        click.echo("\n📋 Events by Type:")
        for event_type, count in stats["by_type"].items():
            click.echo(f"   {event_type}: {count}")

    click.echo(f"\n📁 Event Log: {stats['log_file']}")

    if todos or violations:
        click.echo("\n⚠️  Action Required:")
        if todos:
            click.echo(f"   {len(todos)} script error(s) need delegation")
        if violations:
            click.echo(f"   {len(violations)} PM violation(s) need correction")
        click.echo("\nCommands:")
        click.echo(
            "  claude-mpm autotodos list         # View pending todos (script errors)"
        )
        click.echo("  claude-mpm autotodos violations   # View PM violations")
        click.echo("  claude-mpm autotodos inject       # Inject todos into PM session")
        click.echo("  claude-mpm autotodos clear        # Clear after resolution")
    else:
        click.echo("\n✅ No pending todos or violations. All clear!")


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
    "--event-type",
    type=click.Choice(["error", "violation", "all"], case_sensitive=False),
    default="all",
    help="Type of events to clear (default: all)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clear_autotodos(event_id, event_type, yes):
    """Clear hook errors and PM violations after resolution.

    This marks resolved events in the event log, removing them from
    the autotodos and violations lists.

    Examples:
        claude-mpm autotodos clear                        # Clear all pending
        claude-mpm autotodos clear --event-type error     # Clear only errors
        claude-mpm autotodos clear --event-type violation # Clear only violations
        claude-mpm autotodos clear --event-id ID          # Clear specific event
        claude-mpm autotodos clear -y                     # Skip confirmation
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
        # Determine which event types to clear
        if event_type == "error":
            event_types = ["autotodo.error"]
        elif event_type == "violation":
            event_types = ["pm.violation"]
        else:  # all
            event_types = ["autotodo.error", "pm.violation"]

        # Count pending events
        total_count = 0
        for et in event_types:
            pending = event_log.list_events(event_type=et, status="pending")
            total_count += len(pending)

        if total_count == 0:
            click.echo("No pending events to clear.")
            return

        if not yes:
            message = f"Clear all {total_count} pending event(s)?"
            if not click.confirm(message):
                click.echo("Cancelled.")
                return

        # Mark all as resolved
        total_cleared = 0
        for et in event_types:
            cleared = event_log.mark_all_resolved(event_type=et)
            total_cleared += cleared

        click.echo(f"✅ Cleared {total_cleared} event(s).")


@autotodos_group.command(name="violations")
@click.option(
    "--format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format (table or json)",
)
def list_pm_violations(format):
    """List PM delegation violations.

    Shows instances where PM asked user to do something manually
    instead of delegating to an agent. These are PM behavior errors
    that should be corrected, not todos to delegate.

    Examples:
        claude-mpm autotodos violations
        claude-mpm autotodos violations --format json
    """
    event_log = get_event_log()
    violations = event_log.list_events(event_type="pm.violation", status="pending")

    if not violations:
        click.echo("✅ No PM violations detected. All delegation patterns are correct!")
        return

    if format == "json":
        # JSON output for programmatic use
        click.echo(json.dumps(violations, indent=2))
    else:
        # Table output for human readability
        click.echo("\n" + "=" * 80)
        click.echo("PM Delegation Violations")
        click.echo("=" * 80)
        click.echo("\n⚠️  PM asked user to do these manually instead of delegating:\n")

        for i, violation in enumerate(violations, 1):
            payload = violation.get("payload", {})
            click.echo(f"{i}. Pattern: {payload.get('pattern_type', 'Unknown')}")
            click.echo(f"   Original: \"{payload.get('original_text', '')}\"")
            click.echo(f"   Should delegate: {payload.get('suggested_action', '')}")
            click.echo(f"   Severity: {payload.get('severity', 'unknown')}")
            click.echo(f"   Timestamp: {violation.get('timestamp', 'Unknown')}")
            click.echo()

        click.echo("=" * 80)
        click.echo(f"Total: {len(violations)} violation(s) detected")
        click.echo("\n💡 These are PM behavior errors - PM should delegate these tasks")
        click.echo("   to appropriate agents instead of asking user to do them.")
        click.echo("\nTo clear: claude-mpm autotodos clear --event-type violation")


@autotodos_group.command(name="scan")
@click.argument("text", required=False)
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True),
    help="Scan text from file instead of argument",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format (table or json)",
)
@click.option(
    "--save",
    is_flag=True,
    help="Save detections to event log as PM violations",
)
def scan_delegation_patterns(text, file, format, save):
    """Scan text for delegation anti-patterns.

    Detects when PM asks user to do something manually instead of
    delegating to an agent. Helps enforce the delegation principle.

    Examples:
        claude-mpm autotodos scan "Make sure .env.local is in .gitignore"
        claude-mpm autotodos scan -f response.txt
        claude-mpm autotodos scan -f response.txt --save
        echo "You'll need to run npm install" | claude-mpm autotodos scan
    """
    detector = get_delegation_detector()

    # Read text from file, argument, or stdin
    if file:
        text = Path(file).read_text()
    elif not text:
        # Read from stdin
        import sys

        text = sys.stdin.read()

    if not text or not text.strip():
        click.echo("Error: No text provided to scan.", err=True)
        click.echo("\nUsage:", err=True)
        click.echo("  claude-mpm autotodos scan 'text to scan'", err=True)
        click.echo("  claude-mpm autotodos scan -f file.txt", err=True)
        click.echo("  echo 'text' | claude-mpm autotodos scan", err=True)
        return

    # Detect delegation patterns
    detections = detector.detect_user_delegation(text)

    if not detections:
        click.echo("✅ No delegation anti-patterns detected!")
        return

    # Save to event log if requested
    if save:
        event_log = get_event_log()
        for detection in detections:
            # Format as PM violation payload
            payload = {
                "violation_type": "delegation_anti_pattern",
                "pattern_type": detection["pattern_type"],
                "original_text": detection["original_text"],
                "suggested_action": detection["suggested_todo"],
                "action": detection["action"],
                "source": "delegation_detector",
                "severity": "warning",
                "message": f"PM asked user to do something manually: {detection['original_text'][:80]}...",
            }
            event_log.append_event(
                event_type="pm.violation", payload=payload, status="pending"
            )
        click.echo(f"\n✅ Saved {len(detections)} violation(s) to event log")

    # Output results
    if format == "json":
        # JSON output for programmatic use
        click.echo(json.dumps(detections, indent=2))
    else:
        # Table output for human readability
        click.echo("\n" + "=" * 80)
        click.echo("Delegation Anti-Patterns Detected")
        click.echo("=" * 80)
        click.echo(
            "\n⚠️  PM is asking user to do these manually instead of delegating:\n"
        )

        for i, detection in enumerate(detections, 1):
            click.echo(f"{i}. Pattern: {detection['pattern_type']}")
            click.echo(f"   Original: \"{detection['original_text']}\"")
            click.echo(f"   Suggested Todo: {detection['suggested_todo']}")
            click.echo(f"   Action: {detection['action']}")
            click.echo()

        click.echo("=" * 80)
        click.echo(f"Total: {len(detections)} anti-pattern(s) detected")
        click.echo("\n💡 Tip: PM should delegate these tasks to appropriate agents")
        click.echo("   instead of asking the user to do them manually.")

        if not save:
            click.echo("\n   Use --save to add these as autotodos for PM to see.")


# Register the command group
def register_commands(cli):
    """Register autotodos commands with CLI.

    Args:
        cli: Click CLI group to register commands with
    """
    cli.add_command(autotodos_group)
