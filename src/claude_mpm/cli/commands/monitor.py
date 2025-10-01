"""
Monitor command implementation for claude-mpm.

WHY: This module provides CLI commands for managing the unified monitoring daemon,
providing a single stable way to launch all monitoring functionality including
HTTP dashboard, Socket.IO events, real AST analysis, and Claude Code hook ingestion.

DESIGN DECISIONS:
- Use UnifiedMonitorDaemon for single stable monitoring service
- Single port (8765) for all functionality
- Support both foreground and daemon modes
- Real AST analysis using CodeTreeAnalyzer
- Integrated dashboard and Socket.IO server
"""

from typing import Optional

from ...constants import MonitorCommands
from ...services.monitor.daemon import UnifiedMonitorDaemon
from ..shared import BaseCommand, CommandResult


class MonitorCommand(BaseCommand):
    """Monitor command for managing the unified monitoring daemon."""

    def __init__(self):
        super().__init__("monitor")
        self.daemon = None

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        # Monitor command allows no subcommand (defaults to status)
        if hasattr(args, "monitor_command") and args.monitor_command:
            valid_commands = [cmd.value for cmd in MonitorCommands]
            if args.monitor_command not in valid_commands:
                return f"Unknown monitor command: {args.monitor_command}. Valid commands: {', '.join(valid_commands)}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the monitor command using unified monitoring daemon."""
        try:
            self.logger.info("Monitor command using unified monitoring daemon")

            # Handle default case (no subcommand) - default to status
            if not hasattr(args, "monitor_command") or not args.monitor_command:
                return self._status_monitor(args)

            # Route to specific monitor commands
            if args.monitor_command == MonitorCommands.START.value:
                return self._start_monitor(args)
            if args.monitor_command == MonitorCommands.STOP.value:
                return self._stop_monitor(args)
            if args.monitor_command == MonitorCommands.RESTART.value:
                return self._restart_monitor(args)
            if args.monitor_command == MonitorCommands.STATUS.value:
                return self._status_monitor(args)

            return CommandResult.error_result(
                f"Unknown monitor command: {args.monitor_command}"
            )

        except Exception as e:
            self.logger.error(f"Error executing monitor command: {e}", exc_info=True)
            return CommandResult.error_result(f"Error executing monitor command: {e}")

    def _start_monitor(self, args) -> CommandResult:
        """Start the unified monitor daemon."""
        port = getattr(args, "port", None)
        if port is None:
            port = 8765  # Default to 8765 for unified monitor
        host = getattr(args, "host", "localhost")

        # Check for explicit foreground flag first, then background flag
        # Default to daemon/background mode if neither specified
        if getattr(args, "foreground", False):
            daemon_mode = False
        elif getattr(args, "background", None) is not None:
            daemon_mode = getattr(args, "background", False)
        else:
            # Default to daemon/background mode
            daemon_mode = True

        mode_str = "background/daemon" if daemon_mode else "foreground"
        self.logger.info(
            f"Starting unified monitor daemon on {host}:{port} (mode: {mode_str})"
        )

        # Create unified monitor daemon
        self.daemon = UnifiedMonitorDaemon(
            host=host, port=port, daemon_mode=daemon_mode
        )

        # Get force restart flag
        force_restart = getattr(args, "force", False)

        # Check if already running
        if self.daemon.lifecycle.is_running() and not force_restart:
            existing_pid = self.daemon.lifecycle.get_pid()
            return CommandResult.success_result(
                f"Unified monitor daemon already running with PID {existing_pid}",
                data={
                    "url": f"http://{host}:{port}",
                    "port": port,
                    "pid": existing_pid,
                },
            )

        # Start the daemon (with force restart if specified)
        if self.daemon.start(force_restart=force_restart):
            # For daemon mode, verify it actually started
            if daemon_mode:
                # Give it a moment to fully initialize
                import time

                time.sleep(0.5)

                # Check if it's actually running
                if not self.daemon.lifecycle.is_running():
                    return CommandResult.error_result(
                        "Monitor daemon failed to start. Check ~/.claude-mpm/monitor-daemon.log for details."
                    )

                # Get the actual PID
                actual_pid = self.daemon.lifecycle.get_pid()
                mode_info = f" in background (PID: {actual_pid})"
            else:
                mode_info = " in foreground"

            return CommandResult.success_result(
                f"Unified monitor daemon started on {host}:{port}{mode_info}",
                data={"url": f"http://{host}:{port}", "port": port, "mode": mode_str},
            )

        # Check if error was due to port already in use
        import socket

        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.connect((host, port))
            test_sock.close()
            return CommandResult.error_result(
                f"Port {port} is already in use. Try 'claude-mpm monitor stop' first or use a different port."
            )
        except Exception:
            pass

        return CommandResult.error_result(
            "Failed to start unified monitor daemon. Check ~/.claude-mpm/monitor-daemon.log for details."
        )

    def _stop_monitor(self, args) -> CommandResult:
        """Stop the unified monitor daemon."""
        # Don't log here - the daemon will log when it stops

        # Get parameters from args or use defaults
        port = getattr(args, "port", None)
        if port is None:
            port = 8765  # Default to 8765 for unified monitor
        host = getattr(args, "host", "localhost")

        # Create daemon instance to check status and stop
        # For stop, we need to know if it was started in daemon mode
        # We default to daemon mode since that's the usual case
        daemon_mode = True
        daemon = UnifiedMonitorDaemon(host=host, port=port, daemon_mode=daemon_mode)

        if not daemon.lifecycle.is_running():
            return CommandResult.success_result("No unified monitor daemon running")

        # Stop the daemon
        if daemon.stop():
            return CommandResult.success_result("Unified monitor daemon stopped")
        return CommandResult.error_result("Failed to stop unified monitor daemon")

    def _restart_monitor(self, args) -> CommandResult:
        """Restart the unified monitor daemon."""
        self.logger.info("Restarting unified monitor daemon")

        # Get parameters from args or use defaults
        port = getattr(args, "port", None)
        if port is None:
            port = 8765  # Default to 8765 for unified monitor
        host = getattr(args, "host", "localhost")

        # For restart, default to daemon mode (the usual use case)
        # unless explicitly running in foreground
        daemon_mode = not getattr(args, "foreground", False)

        # Create daemon instance with proper parameters
        daemon = UnifiedMonitorDaemon(host=host, port=port, daemon_mode=daemon_mode)

        # Restart the daemon
        if daemon.restart():
            return CommandResult.success_result(
                f"Unified monitor daemon restarted on {host}:{port}"
            )
        return CommandResult.error_result("Failed to restart unified monitor daemon")

    def _status_monitor(self, args) -> CommandResult:
        """Get unified monitor daemon status."""

        # Create daemon instance to check status
        daemon = UnifiedMonitorDaemon()
        status_data = daemon.status()

        # Format output message
        if status_data["running"]:
            message = f"Unified monitor daemon is running at http://{status_data['host']}:{status_data['port']}"
            if status_data.get("pid"):
                message += f" (PID: {status_data['pid']})"
        else:
            message = "Unified monitor daemon is not running"

        return CommandResult.success_result(message, data=status_data)


def manage_monitor(args):
    """
    Main entry point for monitor command.

    The monitor command manages the unified monitoring daemon that provides
    a single stable way to launch all monitoring functionality including
    HTTP dashboard, Socket.IO events, real AST analysis, and Claude Code hooks.
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
