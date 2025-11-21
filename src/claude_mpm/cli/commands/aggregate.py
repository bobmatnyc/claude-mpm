from pathlib import Path

"""CLI commands for the Event Aggregator service.

WHY: Provides command-line interface for managing the event aggregator service
that captures Socket.IO events and saves them as structured session documents.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Leverage shared utilities for argument parsing and output formatting
- Maintain backward compatibility with existing event aggregator integration
- Support multiple output formats (json, yaml, table, text)
"""

import json
import sys
from typing import Optional

from ...core.enums import OutputFormat
from ...core.logger import get_logger
from ...services.event_aggregator import (
    aggregator_status,
    get_aggregator,
    start_aggregator,
    stop_aggregator,
)
from ..shared import BaseCommand, CommandResult

logger = get_logger("cli.aggregate")


class AggregateCommand(BaseCommand):
    """Aggregate command using shared utilities."""

    def __init__(self):
        super().__init__("aggregate")

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        if not hasattr(args, "aggregate_subcommand") or not args.aggregate_subcommand:
            return "No aggregate subcommand specified"

        valid_commands = ["start", "stop", "status", "sessions", "view", "export"]
        if args.aggregate_subcommand not in valid_commands:
            return f"Unknown aggregate command: {args.aggregate_subcommand}. Valid commands: {', '.join(valid_commands)}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the aggregate command."""
        try:
            # Route to specific subcommand handlers
            command_map = {
                "start": self._start_command,
                "stop": self._stop_command,
                "status": self._status_command,
                "sessions": self._sessions_command,
                "view": self._view_command,
                "export": self._export_command,
            }

            if args.aggregate_subcommand in command_map:
                exit_code = command_map[args.aggregate_subcommand](args)
                if exit_code == 0:
                    return CommandResult.success_result(
                        f"Aggregate {args.aggregate_subcommand} completed successfully"
                    )
                return CommandResult.error_result(
                    f"Aggregate {args.aggregate_subcommand} failed", exit_code=exit_code
                )
            return CommandResult.error_result(
                f"Unknown aggregate command: {args.aggregate_subcommand}"
            )

        except Exception as e:
            self.logger.error(f"Error executing aggregate command: {e}", exc_info=True)
            return CommandResult.error_result(f"Error executing aggregate command: {e}")

    def _start_command(self, args) -> int:
        """Start the event aggregator service."""
        return start_command_legacy(args)

    def _stop_command(self, args) -> int:
        """Stop the event aggregator service."""
        return stop_command_legacy(args)

    def _status_command(self, args) -> int:
        """Show status of the event aggregator service."""
        return status_command_legacy(args)

    def _sessions_command(self, args) -> int:
        """List captured sessions."""
        return sessions_command_legacy(args)

    def _view_command(self, args) -> int:
        """View details of a specific session."""
        return view_command_legacy(args)

    def _export_command(self, args) -> int:
        """Export a session to a file."""
        return export_command_legacy(args)


def aggregate_command(args):
    """
    Main entry point for aggregate command.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = AggregateCommand()
    result = command.execute(args)

    # Print result if structured output format is requested
    if hasattr(args, "format") and str(args.format).lower() in (
        OutputFormat.JSON,
        OutputFormat.YAML,
    ):
        command.print_result(result, args)

    return result.exit_code


def aggregate_command_legacy(args):
    """Legacy aggregate command dispatcher.

    WHY: This contains the original aggregate_command logic, preserved during migration
    to BaseCommand pattern. Will be gradually refactored into the AggregateCommand class.
    """
    subcommand = args.aggregate_subcommand

    if subcommand == "start":
        return start_command_legacy(args)
    if subcommand == "stop":
        return stop_command_legacy(args)
    if subcommand == "status":
        return status_command_legacy(args)
    if subcommand == "sessions":
        return sessions_command_legacy(args)
    if subcommand == "view":
        return view_command_legacy(args)
    if subcommand == "export":
        return export_command_legacy(args)
    print(f"Unknown subcommand: {subcommand}", file=sys.stderr)
    return 1


def start_command_legacy(args):
    """Start the event aggregator service.

    WHY: Starts capturing events from the Socket.IO dashboard server
    for building complete session documents.
    """
    print("Starting Event Aggregator service...")

    # Check if Socket.IO server is running
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", 8765))
            if result != 0:
                print("Warning: Socket.IO server not detected on port 8765")
                print("The aggregator requires the dashboard server to be running.")
                print("Start it with: claude-mpm monitor")
                if not args.force:
                    return 1
    except Exception as e:
        logger.error(f"Error checking server status: {e}")

    # Start the aggregator
    if start_aggregator():
        print("✅ Event Aggregator started successfully")
        print("Capturing events from localhost:8765")
        print("Sessions will be saved to: .claude-mpm/sessions/")

        # Show initial status
        status = aggregator_status()
        print("\nStatus:")
        print(f"  Connected: {status['connected']}")
        print(f"  Active sessions: {status['active_sessions']}")

        if args.daemon:
            print(
                "\nAggregator running in background. Use 'claude-mpm aggregate stop' to stop it."
            )
        else:
            print("\nPress Ctrl+C to stop the aggregator...")
            try:
                # Keep running until interrupted
                import time

                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping aggregator...")
                stop_aggregator()

        return 0
    print("❌ Failed to start Event Aggregator")
    print("Check that python-socketio is installed: pip install python-socketio")
    return 1


def stop_command_legacy(args):
    """Stop the event aggregator service.

    WHY: Gracefully stops the aggregator and saves any active sessions.
    """
    print("Stopping Event Aggregator service...")

    # Get status before stopping
    status = aggregator_status()
    active_sessions = status.get("active_sessions", 0)

    if active_sessions > 0:
        print(f"Saving {active_sessions} active session(s)...")

    stop_aggregator()
    print("✅ Event Aggregator stopped")

    # Show final statistics
    if status["total_events"] > 0:
        print("\nStatistics:")
        print(f"  Total events captured: {status['total_events']}")
        print(f"  Sessions completed: {status['sessions_completed']}")
        print("  Events by type:")
        for event_type, count in sorted(
            status["events_by_type"].items(), key=lambda x: x[1], reverse=True
        )[:5]:
            print(f"    {event_type}: {count}")

    return 0


def status_command_legacy(args):
    """Show status of the event aggregator service.

    WHY: Provides visibility into what the aggregator is doing and
    what it has captured.
    """
    status = aggregator_status()

    print("Event Aggregator Status")
    print("=" * 50)
    print(f"Running: {status['running']}")
    print(f"Connected: {status['connected']}")
    print(f"Server: {status['server']}")
    print(f"Save directory: {status['save_directory']}")
    print()
    print(f"Active sessions: {status['active_sessions']}")
    if status["active_session_ids"]:
        for sid in status["active_session_ids"]:
            print(f"  - {sid}")
    print()
    print(f"Sessions completed: {status['sessions_completed']}")
    print(f"Total events captured: {status['total_events']}")

    if status["events_by_type"]:
        print("\nTop event types:")
        for event_type, count in sorted(
            status["events_by_type"].items(), key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"  {event_type:30s} {count:6d}")

    return 0


def sessions_command_legacy(args):
    """List captured sessions.

    WHY: Shows what sessions have been captured for analysis.
    """
    aggregator = get_aggregator()
    sessions = aggregator.list_sessions(limit=args.limit)

    if not sessions:
        print("No sessions found")
        return 0

    print(f"Recent Sessions (showing {len(sessions)} of {args.limit} max)")
    print("=" * 80)

    for session in sessions:
        print(f"\n📁 {session['file']}")
        print(f"   Session ID: {session['session_id']}")
        print(f"   Start: {session['start_time']}")
        print(f"   End: {session['end_time']}")
        print(f"   Events: {session['events']}")
        print(f"   Delegations: {session['delegations']}")
        print(f"   Prompt: {session['initial_prompt']}")

    print("\nUse 'claude-mpm aggregate view <session_id>' to view details")

    return 0


def view_command_legacy(args):
    """View details of a specific session.

    WHY: Allows detailed inspection of what happened during a session.
    """
    aggregator = get_aggregator()

    # Load the session
    session = aggregator.load_session(args.session_id)

    if not session:
        print(f"Session not found: {args.session_id}")
        print("Use 'claude-mpm aggregate sessions' to list available sessions")
        return 1

    print(f"Session: {session.session_id}")
    print("=" * 80)
    print(f"Start: {session.start_time}")
    print(f"End: {session.end_time or 'In progress'}")
    print(f"Working directory: {session.working_directory}")
    print(f"Launch method: {session.launch_method}")

    if session.git_branch:
        print(f"Git branch: {session.git_branch}")

    print("\nInitial prompt:")
    print("-" * 40)
    if session.initial_prompt:
        print(session.initial_prompt[:500])
        if len(session.initial_prompt) > 500:
            print("...")
    else:
        print("(No prompt captured)")

    print("\nMetrics:")
    print("-" * 40)
    metrics = session.metrics
    print(f"Total events: {metrics.total_events}")
    print(f"Delegations: {metrics.total_delegations}")
    print(f"Tool calls: {metrics.total_tool_calls}")
    print(f"File operations: {metrics.total_file_operations}")

    if metrics.session_duration_ms:
        duration_sec = metrics.session_duration_ms / 1000
        print(f"Duration: {duration_sec:.1f} seconds")

    if metrics.agents_used:
        print(f"\nAgents used: {', '.join(sorted(metrics.agents_used))}")

    if metrics.tools_used:
        print(f"\nTools used: {', '.join(sorted(metrics.tools_used))}")

    if metrics.files_modified:
        print(f"\nFiles modified ({len(metrics.files_modified)}):")
        for filepath in sorted(metrics.files_modified)[:10]:
            print(f"  - {filepath}")
        if len(metrics.files_modified) > 10:
            print(f"  ... and {len(metrics.files_modified) - 10} more")

    if session.delegations:
        print(f"\nDelegations ({len(session.delegations)}):")
        print("-" * 40)
        for i, delegation in enumerate(session.delegations, 1):
            print(f"\n{i}. {delegation.agent_type}")
            print(f"   Task: {delegation.task_description[:100]}")
            if delegation.prompt:
                print(f"   Prompt: {delegation.prompt[:100]}...")
            print(f"   Tools: {len(delegation.tool_operations)}")
            print(f"   Files: {len(delegation.file_changes)}")
            if delegation.duration_ms:
                print(f"   Duration: {delegation.duration_ms / 1000:.1f}s")
            print(f"   Status: {'✅ Success' if delegation.success else '❌ Failed'}")
            if delegation.error:
                print(f"   Error: {delegation.error}")

    if args.show_events:
        print(f"\nEvents ({len(session.events)}):")
        print("-" * 40)
        for event in session.events[: args.event_limit]:
            print(f"{event.timestamp} [{event.category.value:10s}] {event.event_type}")
            if args.verbose:
                print(f"  Agent: {event.agent_context or 'N/A'}")
                if event.correlation_id:
                    print(f"  Correlation: {event.correlation_id}")

    if session.final_response and not args.no_response:
        print("\nFinal response:")
        print("-" * 40)
        print(session.final_response[:1000])
        if len(session.final_response) > 1000:
            print("...")

    return 0


def export_command_legacy(args):
    """Export a session to a file.

    WHY: Allows sessions to be exported for external analysis or sharing.
    """
    aggregator = get_aggregator()

    # Load the session
    session = aggregator.load_session(args.session_id)

    if not session:
        print(f"Session not found: {args.session_id}")
        return 1

    # Determine output file
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"session_{session.session_id[:8]}_export.json")

    # Export based on format
    if str(args.format).lower() == OutputFormat.JSON:
        # Full JSON export
        with output_path.open("w") as f:
            json.dump(session.to_dict(), f, indent=2)
        print(f"✅ Exported session to {output_path}")

    elif args.format == "summary":
        # Summary export
        summary = {
            "session_id": session.session_id,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "working_directory": session.working_directory,
            "initial_prompt": session.initial_prompt,
            "final_response": session.final_response,
            "metrics": session.metrics.to_dict(),
            "delegations_summary": [
                {
                    "agent": d.agent_type,
                    "task": d.task_description,
                    "duration_ms": d.duration_ms,
                    "success": d.success,
                    "tools_used": len(d.tool_operations),
                    "files_changed": len(d.file_changes),
                }
                for d in session.delegations
            ],
        }

        with output_path.open("w") as f:
            json.dump(summary, f, indent=2)
        print(f"✅ Exported session summary to {output_path}")

    elif args.format == "events":
        # Events-only export
        events_data = [e.to_dict() for e in session.events]

        with output_path.open("w") as f:
            json.dump(events_data, f, indent=2)
        print(f"✅ Exported {len(events_data)} events to {output_path}")

    return 0


def add_aggregate_parser(subparsers):
    """Add the aggregate command parser.

    WHY: Integrates the aggregator commands into the main CLI system.
    """
    aggregate_parser = subparsers.add_parser(
        "aggregate", help="Manage event aggregator for capturing agent sessions"
    )

    aggregate_subparsers = aggregate_parser.add_subparsers(
        dest="aggregate_subcommand", help="Aggregator subcommands"
    )

    # Start command
    start_parser = aggregate_subparsers.add_parser(
        "start", help="Start the event aggregator service"
    )
    start_parser.add_argument(
        "--daemon", "-d", action="store_true", help="Run in background as daemon"
    )
    start_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Start even if Socket.IO server not detected",
    )

    # Stop command
    aggregate_subparsers.add_parser("stop", help="Stop the event aggregator service")

    # Status command
    aggregate_subparsers.add_parser(
        "status", help="Show aggregator status and statistics"
    )

    # Sessions command
    sessions_parser = aggregate_subparsers.add_parser(
        "sessions", help="List captured sessions"
    )
    sessions_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        help="Maximum number of sessions to show (default: 10)",
    )

    # View command
    view_parser = aggregate_subparsers.add_parser(
        "view", help="View details of a specific session"
    )
    view_parser.add_argument("session_id", help="Session ID or prefix to view")
    view_parser.add_argument(
        "--show-events", "-e", action="store_true", help="Show event list"
    )
    view_parser.add_argument(
        "--event-limit",
        type=int,
        default=50,
        help="Maximum events to show (default: 50)",
    )
    view_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose event details"
    )
    view_parser.add_argument(
        "--no-response", action="store_true", help="Don't show final response"
    )

    # Export command
    export_parser = aggregate_subparsers.add_parser(
        "export", help="Export a session to file"
    )
    export_parser.add_argument("session_id", help="Session ID or prefix to export")
    export_parser.add_argument("--output", "-o", help="Output file path")
    export_parser.add_argument(
        "--format",
        "-f",
        choices=["json", "summary", "events"],
        default=OutputFormat.JSON,
        help="Export format (default: json)",
    )

    aggregate_parser.set_defaults(func=aggregate_command)
