"""
Monitor command implementation for claude-mpm.

WHY: This module provides CLI commands for managing the Socket.IO monitoring server,
allowing users to start, stop, restart, and check status of the monitoring infrastructure.
The monitor command now delegates to the unified dashboard service for consolidated operation.

DESIGN DECISIONS:
- Delegate to dashboard command for unified service architecture
- Use BaseCommand for consistent CLI patterns
- Maintain backward compatibility with existing Socket.IO server management
- Support multiple output formats (json, yaml, table, text)
"""

from typing import Optional

from ...constants import MonitorCommands
from ..shared import BaseCommand, CommandResult
from .dashboard import DashboardCommand


class MonitorCommand(BaseCommand):
    """Monitor command that delegates to the unified dashboard service."""

    def __init__(self):
        super().__init__("monitor")
        # Create dashboard command instance for delegation
        self.dashboard_command = DashboardCommand()

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        # Monitor command allows no subcommand (defaults to status)
        if hasattr(args, "monitor_command") and args.monitor_command:
            valid_commands = [cmd.value for cmd in MonitorCommands]
            if args.monitor_command not in valid_commands:
                return f"Unknown monitor command: {args.monitor_command}. Valid commands: {', '.join(valid_commands)}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the monitor command by delegating to dashboard service."""
        try:
            self.logger.info("Monitor command delegating to unified dashboard service")

            # Handle default case (no subcommand) - default to status
            if not hasattr(args, "monitor_command") or not args.monitor_command:
                return self._status_dashboard(args)

            # Map monitor commands to dashboard commands
            if args.monitor_command == MonitorCommands.START.value:
                return self._start_dashboard(args)
            if args.monitor_command == MonitorCommands.STOP.value:
                return self._stop_dashboard(args)
            if args.monitor_command == MonitorCommands.RESTART.value:
                return self._restart_dashboard(args)
            if args.monitor_command == MonitorCommands.STATUS.value:
                return self._status_dashboard(args)
            if args.monitor_command == MonitorCommands.PORT.value:
                return self._start_dashboard_on_port(args)

            return CommandResult.error_result(
                f"Unknown monitor command: {args.monitor_command}"
            )

        except Exception as e:
            self.logger.error(f"Error executing monitor command: {e}", exc_info=True)
            return CommandResult.error_result(f"Error executing monitor command: {e}")

    def _start_dashboard(self, args) -> CommandResult:
        """Start the dashboard service (unified HTTP + Socket.IO)."""
        self.logger.info("Starting unified dashboard service (HTTP + Socket.IO)")
        # Set default port to 8765 for unified service and background mode
        if not hasattr(args, "port") or args.port is None:
            args.port = 8765
        # Monitor command defaults to background mode for better UX
        if not hasattr(args, "background"):
            args.background = True

        return self.dashboard_command._start_dashboard(args)

    def _stop_dashboard(self, args) -> CommandResult:
        """Stop the dashboard service."""
        self.logger.info("Stopping unified dashboard service")
        # Use default port if not specified
        if not hasattr(args, "port") or args.port is None:
            args.port = 8765

        return self.dashboard_command._stop_dashboard(args)

    def _restart_dashboard(self, args) -> CommandResult:
        """Restart the dashboard service."""
        self.logger.info("Restarting unified dashboard service")

        # Stop first
        stop_result = self._stop_dashboard(args)
        if not stop_result.success:
            self.logger.warning("Failed to stop service for restart, proceeding anyway")

        # Wait a moment
        import time

        time.sleep(1)

        # Start again
        return self._start_dashboard(args)

    def _status_dashboard(self, args) -> CommandResult:
        """Get dashboard service status."""
        return self.dashboard_command._status_dashboard(args)

    def _start_dashboard_on_port(self, args) -> CommandResult:
        """Start dashboard service on specific port."""
        self.logger.info(
            f"Starting dashboard service on port {getattr(args, 'port', 8765)}"
        )
        # Ensure background mode for port-specific starts
        if not hasattr(args, "background"):
            args.background = True

        return self.dashboard_command._start_dashboard(args)


def manage_monitor(args):
    """
    Main entry point for monitor command.

    The monitor command now delegates to the unified dashboard service for consolidated operation.
    Both dashboard and monitor commands now use the same underlying service on port 8765.
    """
    command = MonitorCommand()
    error = command.validate_args(args)

    if error:
        command.logger.error(error)
        print(f"Error: {error}")
        return 1

    result = command.run(args)

    if result.success:
        if result.message:
            print(result.message)
        if result.data and getattr(args, "verbose", False):
            import json

            print(json.dumps(result.data, indent=2))
        return 0
    if result.message:
        print(f"Error: {result.message}")
    return 1


# All legacy functions have been removed.
# The monitor command now delegates to the unified dashboard service.
# This consolidation provides a single service that handles both HTTP (port 8765)
# and Socket.IO (also on port 8765) rather than separate services on different ports.
