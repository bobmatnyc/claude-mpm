"""
Dashboard command implementation for claude-mpm.

WHY: This module provides CLI commands for managing the web dashboard interface,
allowing users to start, stop, check status, and open the dashboard in a browser.

DESIGN DECISIONS:
- Use UnifiedMonitorDaemon for integrated dashboard and monitoring
- Support both foreground and background operation modes
- Integrate with EventBus for real-time event streaming
- Provide browser auto-opening functionality
"""

import signal
import sys
from typing import Optional

from ...constants import DashboardCommands
from ...services.cli.unified_dashboard_manager import UnifiedDashboardManager
from ...services.monitor.daemon import UnifiedMonitorDaemon
from ...services.port_manager import PortManager
from ..shared import BaseCommand, CommandResult


class DashboardCommand(BaseCommand):
    """Dashboard command for managing the web dashboard interface."""

    def __init__(self):
        super().__init__("dashboard")
        self.dashboard_manager = UnifiedDashboardManager(self.logger)
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
        use_stable = getattr(args, "stable", True)  # Default to stable server

        self.logger.info(
            f"Starting dashboard on {host}:{port} (background: {background}, stable: {use_stable})"
        )

        # Check if dashboard is already running
        if self.dashboard_manager.is_dashboard_running(port):
            dashboard_url = self.dashboard_manager.get_dashboard_url(port)
            return CommandResult.success_result(
                f"Dashboard already running at {dashboard_url}",
                data={"url": dashboard_url, "port": port},
            )

        if background:
            # Use the unified dashboard manager for background mode
            success, browser_opened = self.dashboard_manager.start_dashboard(
                port=port, background=True, open_browser=True
            )
            if success:
                dashboard_url = self.dashboard_manager.get_dashboard_url(port)
                return CommandResult.success_result(
                    f"Dashboard started at {dashboard_url}",
                    data={
                        "url": dashboard_url,
                        "port": port,
                        "browser_opened": browser_opened,
                    },
                )
            return CommandResult.error_result("Failed to start dashboard in background")

        # Run in foreground mode using unified monitor daemon
        try:
            self.logger.info("Starting unified monitor daemon with dashboard...")
            print(f"Starting unified dashboard and monitor on {host}:{port}...")
            print("Press Ctrl+C to stop the server")
            print(
                "\n✅ Using unified daemon - includes dashboard, monitoring, and EventBus integration\n"
            )

            # Create and start the unified monitor daemon
            daemon = UnifiedMonitorDaemon(host=host, port=port, daemon_mode=False)

            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                print("\nShutting down unified monitor daemon...")
                daemon.stop()
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Start the daemon (blocking in foreground mode)
            success = daemon.start()
            if success:
                return CommandResult.success_result("Unified monitor daemon stopped")
            return CommandResult.error_result("Failed to start unified monitor daemon")

        except KeyboardInterrupt:
            print("\nUnified monitor daemon stopped by user")
            return CommandResult.success_result("Unified monitor daemon stopped")
        except Exception as e:
            self.logger.error(f"Unified monitor daemon failed: {e}")
            error_msg = f"Failed to start unified monitor daemon: {e}\n\n"
            error_msg += "💡 Troubleshooting tips:\n"
            error_msg += f"  - Check if port {port} is already in use\n"
            error_msg += "  - Use --debug flag for more details\n"
            error_msg += "  - Check that all dependencies are installed\n"
            return CommandResult.error_result(error_msg)

    def _stop_dashboard(self, args) -> CommandResult:
        """Stop the dashboard server."""
        port = getattr(args, "port", 8765)

        self.logger.info(f"Stopping dashboard on port {port}")

        if not self.dashboard_manager.is_dashboard_running(port):
            return CommandResult.success_result(f"No dashboard running on port {port}")

        if self.dashboard_manager.stop_dashboard(port):
            return CommandResult.success_result(f"Dashboard stopped on port {port}")

        return CommandResult.error_result(f"Failed to stop dashboard on port {port}")

    def _status_dashboard(self, args) -> CommandResult:
        """Check dashboard server status."""
        verbose = getattr(args, "verbose", False)
        show_ports = getattr(args, "show_ports", False)

        # Check default port first
        default_port = 8765
        dashboard_running = self.dashboard_manager.is_dashboard_running(default_port)

        status_data = {
            "running": dashboard_running,
            "default_port": default_port,
        }

        if dashboard_running:
            status_data["url"] = self.dashboard_manager.get_dashboard_url(default_port)

        # Check all ports if requested
        if show_ports:
            port_status = {}
            for port in range(8765, 8786):
                is_running = self.dashboard_manager.is_dashboard_running(port)
                port_status[port] = {
                    "running": is_running,
                    "url": (
                        self.dashboard_manager.get_dashboard_url(port)
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
        if not self.dashboard_manager.is_dashboard_running(port):
            self.logger.info("Dashboard not running, starting it first...")
            # Start dashboard in background
            success, browser_opened = self.dashboard_manager.start_dashboard(
                port=port, background=True, open_browser=True
            )
            if success:
                dashboard_url = self.dashboard_manager.get_dashboard_url(port)
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
        dashboard_url = self.dashboard_manager.get_dashboard_url(port)
        if self.dashboard_manager.open_browser(dashboard_url):
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
