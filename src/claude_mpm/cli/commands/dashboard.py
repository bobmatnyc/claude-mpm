"""
Dashboard command implementation for claude-mpm.

WHY: This module provides CLI commands for managing the web dashboard interface,
allowing users to start, stop, check status, and open the dashboard in a browser.

DESIGN DECISIONS:
- Use DashboardLauncher service for consistent dashboard management
- Support both foreground and background operation modes
- Integrate with SocketIO server for real-time event streaming
- Provide browser auto-opening functionality
"""

import signal
import sys
import time
from typing import Optional

from ...constants import DashboardCommands
from ...services.cli.dashboard_launcher import DashboardLauncher
from ...services.port_manager import PortManager
from ...services.socketio.dashboard_server import DashboardServer
from ..shared import BaseCommand, CommandResult


class DashboardCommand(BaseCommand):
    """Dashboard command for managing the web dashboard interface."""

    def __init__(self):
        super().__init__("dashboard")
        self.dashboard_launcher = DashboardLauncher(self.logger)
        self.port_manager = PortManager()
        self.server = None

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        if hasattr(args, "dashboard_command") and args.dashboard_command:
            valid_commands = [cmd.value for cmd in DashboardCommands]
            if args.dashboard_command not in valid_commands:
                return f"Unknown dashboard command: {args.dashboard_command}. Valid commands: {', '.join(valid_commands)}"
        return None

    def run(self, args) -> CommandResult:
        """Execute the dashboard command."""
        try:
            # Handle default case (no subcommand) - default to status
            if not hasattr(args, "dashboard_command") or not args.dashboard_command:
                return self._status_dashboard(args)

            # Route to specific subcommand handlers
            command_map = {
                DashboardCommands.START.value: self._start_dashboard,
                DashboardCommands.STOP.value: self._stop_dashboard,
                DashboardCommands.STATUS.value: self._status_dashboard,
                DashboardCommands.OPEN.value: self._open_dashboard,
            }

            if args.dashboard_command in command_map:
                return command_map[args.dashboard_command](args)

            return CommandResult.error_result(
                f"Unknown dashboard command: {args.dashboard_command}"
            )

        except Exception as e:
            self.logger.error(f"Error executing dashboard command: {e}", exc_info=True)
            return CommandResult.error_result(f"Error executing dashboard command: {e}")

    def _start_dashboard(self, args) -> CommandResult:
        """Start the dashboard server."""
        port = getattr(args, "port", 8765)
        host = getattr(args, "host", "localhost")
        background = getattr(args, "background", False)

        self.logger.info(
            f"Starting dashboard on {host}:{port} (background: {background})"
        )

        # Check if dashboard is already running
        if self.dashboard_launcher.is_dashboard_running(port):
            dashboard_url = self.dashboard_launcher.get_dashboard_url(port)
            return CommandResult.success_result(
                f"Dashboard already running at {dashboard_url}",
                data={"url": dashboard_url, "port": port},
            )

        if background:
            # Use the dashboard launcher for background mode
            success, browser_opened = self.dashboard_launcher.launch_dashboard(
                port=port, monitor_mode=True
            )
            if success:
                dashboard_url = self.dashboard_launcher.get_dashboard_url(port)
                return CommandResult.success_result(
                    f"Dashboard started at {dashboard_url}",
                    data={
                        "url": dashboard_url,
                        "port": port,
                        "browser_opened": browser_opened,
                    },
                )
            return CommandResult.error_result("Failed to start dashboard in background")
        # Run in foreground mode - directly start the SocketIO server
        try:
            print(f"Starting dashboard server on {host}:{port}...")
            print("Press Ctrl+C to stop the server")

            # Create and start the Dashboard server (with monitor client)
            self.server = DashboardServer(host=host, port=port)

            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                print("\nShutting down dashboard server...")
                if self.server:
                    self.server.stop_sync()
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Start the server (this starts in background thread)
            self.server.start_sync()

            # Keep the main thread alive while server is running
            # The server runs in a background thread, so we need to block here
            try:
                while self.server.is_running():
                    time.sleep(1)
            except KeyboardInterrupt:
                # Ctrl+C pressed, stop the server
                pass

            # Server has stopped or user interrupted
            if self.server:
                self.server.stop_sync()

            return CommandResult.success_result("Dashboard server stopped")

        except KeyboardInterrupt:
            print("\nDashboard server stopped by user")
            return CommandResult.success_result("Dashboard server stopped")
        except Exception as e:
            return CommandResult.error_result(f"Failed to start dashboard: {e}")

    def _stop_dashboard(self, args) -> CommandResult:
        """Stop the dashboard server."""
        port = getattr(args, "port", 8765)

        self.logger.info(f"Stopping dashboard on port {port}")

        if not self.dashboard_launcher.is_dashboard_running(port):
            return CommandResult.success_result(f"No dashboard running on port {port}")

        if self.dashboard_launcher.stop_dashboard(port):
            return CommandResult.success_result(f"Dashboard stopped on port {port}")

        return CommandResult.error_result(f"Failed to stop dashboard on port {port}")

    def _status_dashboard(self, args) -> CommandResult:
        """Check dashboard server status."""
        verbose = getattr(args, "verbose", False)
        show_ports = getattr(args, "show_ports", False)

        # Check default port first
        default_port = 8765
        dashboard_running = self.dashboard_launcher.is_dashboard_running(default_port)

        status_data = {
            "running": dashboard_running,
            "default_port": default_port,
        }

        if dashboard_running:
            status_data["url"] = self.dashboard_launcher.get_dashboard_url(default_port)

        # Check all ports if requested
        if show_ports:
            port_status = {}
            for port in range(8765, 8786):
                is_running = self.dashboard_launcher.is_dashboard_running(port)
                port_status[port] = {
                    "running": is_running,
                    "url": (
                        self.dashboard_launcher.get_dashboard_url(port)
                        if is_running
                        else None
                    ),
                }
            status_data["ports"] = port_status

        # Get active instances from port manager
        self.port_manager.cleanup_dead_instances()
        active_instances = self.port_manager.list_active_instances()
        if active_instances:
            status_data["active_instances"] = active_instances

        if verbose:
            # Add more detailed information
            import socket

            status_data["hostname"] = socket.gethostname()
            status_data["can_bind"] = self._check_port_available(default_port)

        # Format output message
        if dashboard_running:
            message = f"Dashboard is running at {status_data['url']}"
        else:
            message = "Dashboard is not running"

        return CommandResult.success_result(message, data=status_data)

    def _open_dashboard(self, args) -> CommandResult:
        """Open the dashboard in a browser, starting it if necessary."""
        port = getattr(args, "port", 8765)

        # Check if dashboard is running
        if not self.dashboard_launcher.is_dashboard_running(port):
            self.logger.info("Dashboard not running, starting it first...")
            # Start dashboard in background
            success, browser_opened = self.dashboard_launcher.launch_dashboard(
                port=port, monitor_mode=True
            )
            if success:
                dashboard_url = self.dashboard_launcher.get_dashboard_url(port)
                return CommandResult.success_result(
                    f"Dashboard started and opened at {dashboard_url}",
                    data={
                        "url": dashboard_url,
                        "port": port,
                        "browser_opened": browser_opened,
                    },
                )
            return CommandResult.error_result("Failed to start and open dashboard")
        # Dashboard already running, just open browser
        dashboard_url = self.dashboard_launcher.get_dashboard_url(port)
        if self.dashboard_launcher._open_browser(dashboard_url):
            return CommandResult.success_result(
                f"Opened dashboard at {dashboard_url}",
                data={"url": dashboard_url, "port": port},
            )
        return CommandResult.success_result(
            f"Dashboard running at {dashboard_url} (could not auto-open browser)",
            data={"url": dashboard_url, "port": port},
        )

    def _check_port_available(self, port: int) -> bool:
        """Check if a port is available for binding."""
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return True
        except OSError:
            return False


def manage_dashboard(args) -> int:
    """
    Main entry point for dashboard command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    command = DashboardCommand()
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
