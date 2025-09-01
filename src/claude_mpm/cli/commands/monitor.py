"""
Monitor command implementation for claude-mpm.

WHY: This module provides CLI commands for managing the lightweight monitoring server,
allowing users to start, stop, restart, and check status of the independent monitoring service.
The monitor service runs as a stable background service on port 8766 (configurable).

DESIGN DECISIONS:
- Use independent MonitorServer for decoupled architecture
- Monitor runs on port 8766, Dashboard runs on port 8765
- Support background mode by default for stable always-on operation
- Provide status checking and port configuration
- Maintain minimal dependencies and resource usage
"""

import signal
import sys
import time
from typing import Optional

from ...constants import MonitorCommands
from ...services.port_manager import PortManager
from ...services.socketio.monitor_server import MonitorServer
from ..shared import BaseCommand, CommandResult


class MonitorCommand(BaseCommand):
    """Monitor command for managing the independent monitoring server."""

    def __init__(self):
        super().__init__("monitor")
        self.port_manager = PortManager()
        self.server = None

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        # Monitor command allows no subcommand (defaults to status)
        if hasattr(args, "monitor_command") and args.monitor_command:
            valid_commands = [cmd.value for cmd in MonitorCommands]
            if args.monitor_command not in valid_commands:
                return f"Unknown monitor command: {args.monitor_command}. Valid commands: {', '.join(valid_commands)}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the monitor command using independent MonitorServer."""
        try:
            self.logger.info("Monitor command using independent monitoring server")

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
            if args.monitor_command == MonitorCommands.PORT.value:
                return self._start_monitor_on_port(args)

            return CommandResult.error_result(
                f"Unknown monitor command: {args.monitor_command}"
            )

        except Exception as e:
            self.logger.error(f"Error executing monitor command: {e}", exc_info=True)
            return CommandResult.error_result(f"Error executing monitor command: {e}")

    def _start_monitor(self, args) -> CommandResult:
        """Start the monitor server."""
        port = getattr(args, "port", 8766)  # Default to 8766 for monitor
        host = getattr(args, "host", "localhost")
        background = getattr(
            args, "background", True
        )  # Default to background for monitor

        self.logger.info(
            f"Starting monitor server on {host}:{port} (background: {background})"
        )

        # Check if monitor is already running
        if self._is_monitor_running(port):
            return CommandResult.success_result(
                f"Monitor server already running on {host}:{port}",
                data={"url": f"http://{host}:{port}", "port": port},
            )

        if background:
            # Start monitor server in background
            try:
                self.server = MonitorServer(host=host, port=port)
                if self.server.start_sync():
                    return CommandResult.success_result(
                        f"Monitor server started on {host}:{port}",
                        data={"url": f"http://{host}:{port}", "port": port},
                    )
                return CommandResult.error_result("Failed to start monitor server")
            except Exception as e:
                return CommandResult.error_result(
                    f"Failed to start monitor server: {e}"
                )
        else:
            # Run monitor in foreground mode
            try:
                print(f"Starting monitor server on {host}:{port}...")
                print("Press Ctrl+C to stop the server")

                self.server = MonitorServer(host=host, port=port)

                # Set up signal handlers for graceful shutdown
                def signal_handler(signum, frame):
                    print("\nShutting down monitor server...")
                    if self.server:
                        self.server.stop_sync()
                    sys.exit(0)

                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)

                # Start the server
                if not self.server.start_sync():
                    return CommandResult.error_result("Failed to start monitor server")

                # Keep the main thread alive while server is running
                try:
                    while self.server.is_running():
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass

                # Stop the server
                if self.server:
                    self.server.stop_sync()

                return CommandResult.success_result("Monitor server stopped")

            except KeyboardInterrupt:
                print("\nMonitor server stopped by user")
                return CommandResult.success_result("Monitor server stopped")
            except Exception as e:
                return CommandResult.error_result(
                    f"Failed to start monitor server: {e}"
                )

    def _stop_monitor(self, args) -> CommandResult:
        """Stop the monitor server."""
        port = getattr(args, "port", 8766)

        self.logger.info(f"Stopping monitor server on port {port}")

        if not self._is_monitor_running(port):
            return CommandResult.success_result(
                f"No monitor server running on port {port}"
            )

        # Try to stop our server instance if we have one
        if self.server and self.server.is_running():
            try:
                self.server.stop_sync()
                return CommandResult.success_result(
                    f"Monitor server stopped on port {port}"
                )
            except Exception as e:
                return CommandResult.error_result(f"Error stopping monitor server: {e}")

        # If we don't have a server instance, try port manager cleanup
        try:
            self.port_manager.cleanup_dead_instances()
            active_instances = self.port_manager.list_active_instances()

            # Look for instances on the target port
            for instance in active_instances:
                if (
                    instance.get("port") == port
                    and instance.get("service_type") == "monitor"
                ):
                    # Found an instance, but we can't stop it directly
                    # This would need to be implemented with a proper process manager
                    return CommandResult.error_result(
                        f"Monitor server found on port {port} but cannot be stopped "
                        "(no direct control - you may need to kill the process manually)"
                    )

            return CommandResult.success_result(
                f"No monitor server found on port {port}"
            )

        except Exception as e:
            return CommandResult.error_result(
                f"Error checking monitor server status: {e}"
            )

    def _restart_monitor(self, args) -> CommandResult:
        """Restart the monitor server."""
        self.logger.info("Restarting monitor server")

        # Stop first
        stop_result = self._stop_monitor(args)
        if not stop_result.success:
            self.logger.warning(
                "Failed to stop monitor server for restart, proceeding anyway"
            )

        # Wait a moment
        time.sleep(2)

        # Start again
        return self._start_monitor(args)

    def _status_monitor(self, args) -> CommandResult:
        """Get monitor server status."""
        port = getattr(args, "port", 8766)
        verbose = getattr(args, "verbose", False)
        show_ports = getattr(args, "show_ports", False)

        # Check if monitor is running
        monitor_running = self._is_monitor_running(port)

        status_data = {
            "running": monitor_running,
            "default_port": port,
            "service_type": "monitor",
        }

        if monitor_running:
            status_data["url"] = f"http://localhost:{port}"

        # Check all ports if requested
        if show_ports:
            port_status = {}
            for check_port in range(8766, 8776):  # Monitor port range
                is_running = self._is_monitor_running(check_port)
                port_status[check_port] = {
                    "running": is_running,
                    "url": f"http://localhost:{check_port}" if is_running else None,
                }
            status_data["ports"] = port_status

        # Get active instances from port manager
        self.port_manager.cleanup_dead_instances()
        active_instances = self.port_manager.list_active_instances()
        if active_instances:
            monitor_instances = [
                inst
                for inst in active_instances
                if inst.get("service_type") == "monitor"
            ]
            if monitor_instances:
                status_data["active_instances"] = monitor_instances

        if verbose and self.server:
            status_data["server_stats"] = self.server.get_stats()

        # Format output message
        if monitor_running:
            message = f"Monitor server is running at {status_data['url']}"
        else:
            message = "Monitor server is not running"

        return CommandResult.success_result(message, data=status_data)

    def _start_monitor_on_port(self, args) -> CommandResult:
        """Start monitor server on specific port."""
        port = getattr(args, "port", 8766)
        self.logger.info(f"Starting monitor server on port {port}")

        # Ensure background mode for port-specific starts
        if not hasattr(args, "background"):
            args.background = True

        return self._start_monitor(args)

    def _is_monitor_running(self, port: int) -> bool:
        """Check if monitor server is running on given port."""
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("localhost", port))
                return result == 0
        except Exception:
            return False


def manage_monitor(args):
    """
    Main entry point for monitor command.

    The monitor command manages an independent lightweight monitoring server on port 8766.
    This server runs separately from the dashboard (port 8765) and provides stable
    event collection and relay services.
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
