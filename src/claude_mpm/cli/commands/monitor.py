"""
Monitor command implementation for claude-mpm.

WHY: This module provides CLI commands for managing the Socket.IO monitoring server,
allowing users to start, stop, restart, and check status of the monitoring infrastructure.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Leverage shared utilities for argument parsing and output formatting
- Maintain backward compatibility with existing Socket.IO server management
- Support multiple output formats (json, yaml, table, text)
"""

import subprocess
import sys
from typing import Optional

from ...constants import MonitorCommands
from ...core.logger import get_logger
from ..shared import BaseCommand, CommandResult


class MonitorCommand(BaseCommand):
    """Monitor command using shared utilities."""

    def __init__(self):
        super().__init__("monitor")

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        # Monitor command allows no subcommand (defaults to status)
        if hasattr(args, "monitor_command") and args.monitor_command:
            valid_commands = [cmd.value for cmd in MonitorCommands]
            if args.monitor_command not in valid_commands:
                return f"Unknown monitor command: {args.monitor_command}. Valid commands: {', '.join(valid_commands)}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the monitor command."""
        try:
            # Import ServerManager
            from ...scripts.socketio_server_manager import ServerManager

            server_manager = ServerManager()

            # Handle default case (no subcommand)
            if not hasattr(args, "monitor_command") or not args.monitor_command:
                # Default to status
                success = self._status_server(args, server_manager)
                if success:
                    return CommandResult.success_result(
                        "Monitor status retrieved successfully"
                    )
                return CommandResult.error_result("Failed to retrieve monitor status")

            # Route to specific subcommand handlers
            command_map = {
                MonitorCommands.START.value: self._start_server,
                MonitorCommands.STOP.value: self._stop_server,
                MonitorCommands.RESTART.value: self._restart_server,
                MonitorCommands.STATUS.value: self._status_server,
                MonitorCommands.PORT.value: self._port_server,
            }

            if args.monitor_command in command_map:
                success = command_map[args.monitor_command](args, server_manager)
                if success:
                    return CommandResult.success_result(
                        f"Monitor {args.monitor_command} completed successfully"
                    )
                return CommandResult.error_result(
                    f"Monitor {args.monitor_command} failed"
                )
            return CommandResult.error_result(
                f"Unknown monitor command: {args.monitor_command}"
            )

        except Exception as e:
            self.logger.error(f"Error executing monitor command: {e}", exc_info=True)
            return CommandResult.error_result(f"Error executing monitor command: {e}")

    def _start_server(self, args, server_manager) -> bool:
        """Start the monitoring server."""
        return _start_server(args, server_manager)

    def _stop_server(self, args, server_manager) -> bool:
        """Stop the monitoring server."""
        return _stop_server(args, server_manager)

    def _restart_server(self, args, server_manager) -> bool:
        """Restart the monitoring server."""
        return _restart_server(args, server_manager)

    def _status_server(self, args, server_manager) -> bool:
        """Get monitoring server status."""
        return _status_server(args, server_manager)

    def _port_server(self, args, server_manager) -> bool:
        """Start/restart server on specific port."""
        return _port_server(args, server_manager)


def manage_monitor(args):
    """
    Main entry point for monitor command.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = MonitorCommand()
    result = command.execute(args)

    # Print result if structured output format is requested
    if hasattr(args, "format") and args.format in ["json", "yaml"]:
        command.print_result(result, args)

    return result.exit_code


def manage_monitor_legacy(args):
    """
    Legacy monitor command dispatcher.

    WHY: This contains the original manage_monitor logic, preserved during migration
    to BaseCommand pattern. Will be gradually refactored into the MonitorCommand class.

    DESIGN DECISION: When no subcommand is provided, we show the server status
    as the default action, giving users a quick overview of the monitoring system.

    Args:
        args: Parsed command line arguments with monitor_command attribute
    """
    logger = get_logger("cli")

    try:
        # Import ServerManager from socketio_server_manager.py
        from ...scripts.socketio_server_manager import ServerManager

        server_manager = ServerManager()

        if not args.monitor_command:
            # No subcommand - show status as default
            # WHY: Status is the most common operation users want when running monitor without args
            args.verbose = False  # Set default for verbose flag
            success = _status_server(args, server_manager)
            return 0 if success else 1

        if args.monitor_command == MonitorCommands.START.value:
            success = _start_server(args, server_manager)
            return 0 if success else 1

        if args.monitor_command == MonitorCommands.STOP.value:
            success = _stop_server(args, server_manager)
            return 0 if success else 1

        if args.monitor_command == MonitorCommands.RESTART.value:
            success = _restart_server(args, server_manager)
            return 0 if success else 1

        if args.monitor_command == MonitorCommands.STATUS.value:
            success = _status_server(args, server_manager)
            return 0 if success else 1

        if args.monitor_command == MonitorCommands.PORT.value:
            success = _port_server(args, server_manager)
            return 0 if success else 1

        logger.error(f"Unknown monitor command: {args.monitor_command}")
        print(f"Unknown monitor command: {args.monitor_command}")
        print("Available commands: start, stop, restart, status, port")
        return 1

    except ImportError as e:
        logger.error(f"Server manager not available: {e}")
        print("Error: Socket.IO server manager not available")
        print("This may indicate a missing dependency or installation issue.")
        return 1
    except Exception as e:
        logger.error(f"Error managing monitor: {e}")
        print(f"Error: {e}")
        return 1

    return 0


def _port_server(args, server_manager):
    """
    Start or restart the Socket.IO monitoring server on a specific port.

    WHY: Users need to be able to start/restart the monitoring server on a specific
    port, either if no server is running (start) or if a server is already running
    on a different port (restart). Enhanced with smart process detection to reclaim
    ports from debug processes.

    Args:
        args: Command arguments with required port and optional host, force, reclaim flags
        server_manager: ServerManager instance

    Returns:
        bool: True if server started/restarted successfully, False otherwise
    """
    port = args.port
    host = getattr(args, "host", "localhost")
    force = getattr(args, "force", False)
    reclaim = getattr(args, "reclaim", True)

    print(f"Managing Socket.IO monitoring server on port {port}...")
    print(f"Target: {host}:{port}")
    print()

    try:
        # Import PortManager to check port status
        from ...services.port_manager import PortManager

        port_manager = PortManager()

        # Get detailed port status
        port_status = port_manager.get_port_status(port)

        # Check if port is in use
        if not port_status["available"]:
            process_info = port_status.get("process")
            if process_info:
                print(f"⚠️ Port {port} is in use:")
                print(f"  Process: {process_info['name']} (PID: {process_info['pid']})")

                if process_info["is_ours"]:
                    if process_info["is_debug"]:
                        print("  Type: Debug/Test script (can be reclaimed)")
                        if reclaim:
                            print("  Action: Attempting to reclaim port...")
                            if port_manager.kill_process_on_port(port, force=force):
                                print(f"  ✅ Successfully reclaimed port {port}")
                            else:
                                print(f"  ❌ Failed to reclaim port {port}")
                                return False
                    elif process_info["is_daemon"]:
                        print("  Type: Daemon process")
                        if force:
                            print(
                                "  Action: Force killing daemon (--force flag used)..."
                            )
                            if port_manager.kill_process_on_port(port, force=True):
                                print(f"  ✅ Successfully killed daemon on port {port}")
                            else:
                                print(f"  ❌ Failed to kill daemon on port {port}")
                                return False
                        else:
                            print("  ❌ Cannot start: Daemon already running")
                            print(f"  Recommendation: {port_status['recommendation']}")
                            return False
                else:
                    print("  Type: External process")
                    print(f"  ❌ Cannot start: {port_status['recommendation']}")
                    return False
                print()

        # Check if there are any running servers
        running_servers = server_manager.list_running_servers()

        # Check if server is already running on this port after reclaim
        server_on_port = any(server.get("port") == port for server in running_servers)

        if server_on_port:
            print(f"Server already running on port {port}. Restarting...")
            success = server_manager.restart_server(port=port)
            action = "restarted"
        else:
            # Check if servers are running on other ports
            if running_servers:
                print("Servers running on other ports:")
                for server in running_servers:
                    server_port = server.get("port")
                    server_id = server.get("server_id", "unknown")
                    print(f"  • Server '{server_id}' on port {server_port}")
                print()
                print(f"Starting new server on port {port}...")
            else:
                print("No servers currently running. Starting new server...")

            success = server_manager.start_server(
                port=port, host=host, server_id="monitor-server"
            )
            action = "started"

        if success:
            print()
            print(f"Monitor server {action} successfully on port {port}")
            print()
            print("Server management commands:")
            print("  Status:  ps aux | grep socketio")
            print(f"  Stop:    claude-mpm monitor stop --port {port}")
            print(f"  Restart: claude-mpm monitor restart --port {port}")
            print()
            print(f"WebSocket URL: ws://{host}:{port}")
        else:
            print(f"Failed to {action.replace('ed', '')} server on port {port}")
            print()
            print("Troubleshooting:")
            print(f"  • Check if port {port} is available: lsof -i :{port}")
            print(f"  • Try a different port: claude-mpm monitor port {port + 1}")
            print("  • Check system resources: free -h && df -h")

        return success

    except Exception as e:
        print(f"Error managing server on port {port}: {e}")
        print()
        print("Troubleshooting:")
        print(f"  • Verify port {port} is valid and available")
        print("  • Check system resources and permissions")
        print("  • Try manual start/stop operations")
        return False


def _start_server(args, server_manager):
    """
    Start the Socket.IO monitoring server.

    WHY: Users need to start the monitoring server to enable real-time monitoring
    of Claude MPM sessions and websocket connections. Enhanced with smart process
    detection to automatically reclaim ports from debug scripts.

    Args:
        args: Command arguments with optional port, host, force, and reclaim flags
        server_manager: ServerManager instance

    Returns:
        bool: True if server started successfully, False otherwise
    """
    port = getattr(args, "port", None)
    host = getattr(args, "host", "localhost")
    force = getattr(args, "force", False)
    reclaim = getattr(args, "reclaim", True)

    print("Starting Socket.IO monitoring server...")

    try:
        # Import PortManager for smart port selection
        from ...services.port_manager import PortManager

        port_manager = PortManager()

        # If no port specified, find an available one with smart reclaim
        if port is None:
            port = port_manager.find_available_port(reclaim=reclaim)
            if port is None:
                print("❌ No available ports found")
                print(
                    "Try specifying a port with --port or use --force to reclaim daemon ports"
                )
                return False
            print(f"Selected port: {port}")
        else:
            # Check if specified port needs reclaiming
            port_status = port_manager.get_port_status(port)
            if not port_status["available"]:
                process_info = port_status.get("process")
                if process_info:
                    print(
                        f"⚠️ Port {port} is in use by {process_info['name']} (PID: {process_info['pid']})"
                    )

                    if process_info["is_ours"] and (process_info["is_debug"] or force):
                        if reclaim:
                            print(f"Attempting to reclaim port {port}...")
                            if not port_manager.kill_process_on_port(port, force=force):
                                print(f"❌ Failed to reclaim port {port}")
                                return False
                            print(f"✅ Successfully reclaimed port {port}")
                        else:
                            print(
                                f"❌ Port {port} unavailable and --no-reclaim specified"
                            )
                            return False
                    else:
                        print(
                            f"❌ Cannot reclaim port: {port_status['recommendation']}"
                        )
                        return False

        print(f"Target: {host}:{port}")
        print()

        success = server_manager.start_server(
            port=port, host=host, server_id="monitor-server"
        )

        if success:
            print()
            print("Monitor server management commands:")
            print("  Status: claude-mpm monitor status")
            print("  Stop:   claude-mpm monitor stop")
            print("  Restart: claude-mpm monitor restart")
            print()
            print(f"WebSocket URL: ws://{host}:{port}")

        return success

    except Exception as e:
        print(f"Failed to start monitoring server: {e}")
        print()
        print("Troubleshooting:")
        print(f"  • Check if port {port} is available: lsof -i :{port}")
        print(f"  • Try a different port: claude-mpm monitor start --port {port + 1}")
        print("  • Check system resources: free -h && df -h")
        return False


def _stop_server(args, server_manager):
    """
    Stop the Socket.IO monitoring server.

    WHY: Users need to stop the monitoring server when it's no longer needed
    or when troubleshooting connection issues.

    Args:
        args: Command arguments with optional port
        server_manager: ServerManager instance

    Returns:
        bool: True if server stopped successfully, False otherwise
    """
    port = getattr(args, "port", None)

    print("Stopping Socket.IO monitoring server...")

    try:
        # If no port specified, try to find running servers and stop them
        if port is None:
            running_servers = server_manager.list_running_servers()
            if not running_servers:
                print("No running servers found to stop")
                return True

            # Stop the first server (or all if multiple)
            success = True
            for server in running_servers:
                server_port = server.get("port")
                server_id = server.get("server_id", "unknown")
                print(f"Stopping server '{server_id}' on port {server_port}...")

                if not server_manager.stop_server(port=server_port):
                    print(f"Failed to stop server on port {server_port}")
                    success = False

            return success
        # Stop specific server on given port
        success = server_manager.stop_server(port=port)

        if success:
            print(f"Monitor server stopped on port {port}")
        else:
            print(f"Failed to stop server on port {port}")
            print()
            print("Troubleshooting:")
            print("  • Check if server is running: claude-mpm monitor status")
            print(f"  • Try force kill: kill $(lsof -ti :{port})")

        return success

    except Exception as e:
        print(f"Error stopping server: {e}")
        return False


def _status_server(args, server_manager):
    """
    Check the status of Socket.IO monitoring servers.

    WHY: Users need to check if the monitoring server is running, what port
    it's using, and other diagnostic information without starting/stopping it.
    Enhanced to show what processes are using ports.

    Args:
        args: Command arguments with optional verbose flag
        server_manager: ServerManager instance

    Returns:
        bool: True if status check succeeded, False otherwise
    """
    verbose = getattr(args, "verbose", False)
    show_ports = getattr(args, "show_ports", False)

    print("Checking Socket.IO monitoring server status...")
    print()

    try:
        # Check for daemon server using socketio_daemon.py
        daemon_script = server_manager.daemon_script
        if daemon_script and daemon_script.exists():
            # Try to get status from daemon
            result = subprocess.run(
                [sys.executable, str(daemon_script), "status"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout:
                # Daemon provided status information
                print(result.stdout)

                if verbose:
                    # Show additional information
                    print("\nAdditional Details:")
                    print("─" * 40)

                    # List all running servers from ServerManager
                    running_servers = server_manager.list_running_servers()
                    if running_servers:
                        print(f"Found {len(running_servers)} running server(s):")
                        for server in running_servers:
                            server_port = server.get("port", "unknown")
                            server_id = server.get("server_id", "unknown")
                            server_pid = server.get("pid", "unknown")
                            print(f"  • Server '{server_id}'")
                            print(f"    Port: {server_port}")
                            print(f"    PID: {server_pid}")
                    else:
                        print("No additional servers found via ServerManager")

                return True

        # Fall back to ServerManager's list_running_servers
        running_servers = server_manager.list_running_servers()

        if not running_servers:
            print("❌ No Socket.IO monitoring servers are currently running")
            print()
            print("To start a server:")
            print("  claude-mpm monitor start")
            print("  claude-mpm monitor start --port 8765")
            return True

        # Import PortManager for enhanced status
        from ...services.port_manager import PortManager

        port_manager = PortManager()

        # Display server information
        print(f"✅ Found {len(running_servers)} running server(s):")
        print()

        for server in running_servers:
            server_port = server.get("port", "unknown")
            server_id = server.get("server_id", "unknown")
            server_pid = server.get("pid", "unknown")
            server_host = server.get("host", "localhost")

            print(f"Server: {server_id}")
            print(f"  • PID: {server_pid}")
            print(f"  • Port: {server_port}")
            print(f"  • Host: {server_host}")
            print(f"  • WebSocket URL: ws://{server_host}:{server_port}")

            # Show port status if verbose
            if verbose and server_port != "unknown":
                port_status = port_manager.get_port_status(int(server_port))
                if port_status.get("process"):
                    process = port_status["process"]
                    print(
                        f"  • Process Type: {'Debug' if process['is_debug'] else 'Daemon' if process['is_daemon'] else 'Regular'}"
                    )

            if verbose:
                # Check if port is actually listening
                try:
                    import socket

                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    result = sock.connect_ex((server_host, server_port))
                    sock.close()
                    if result == 0:
                        print("  • Status: ✅ Listening")
                    else:
                        print("  • Status: ⚠️ Not responding on port")
                except Exception as e:
                    print(f"  • Status: ❌ Error checking: {e}")

            print()

        # Show port range status if requested
        if show_ports or verbose:
            print("\nPort Range Status (8765-8785):")
            print("─" * 40)
            for check_port in range(8765, 8771):  # Show first 6 ports
                status = port_manager.get_port_status(check_port)
                if status["available"]:
                    print(f"  Port {check_port}: ✅ Available")
                else:
                    process = status.get("process")
                    if process:
                        if process["is_ours"]:
                            if process["is_debug"]:
                                print(
                                    f"  Port {check_port}: 🔧 Debug script (PID: {process['pid']})"
                                )
                            elif process["is_daemon"]:
                                print(
                                    f"  Port {check_port}: 🚀 Daemon (PID: {process['pid']})"
                                )
                            else:
                                print(
                                    f"  Port {check_port}: 📦 Our process (PID: {process['pid']})"
                                )
                        else:
                            print(
                                f"  Port {check_port}: ⛔ External ({process['name']})"
                            )
                    else:
                        print(f"  Port {check_port}: ❓ In use (unknown process)")
            print()

        print("Server management commands:")
        print("  Stop all:    claude-mpm monitor stop")
        print("  Restart:     claude-mpm monitor restart")
        print("  Reclaim:     claude-mpm monitor start --force  # Kill debug scripts")
        if len(running_servers) == 1:
            port = running_servers[0].get("port", 8765)
            print(f"  Stop this:   claude-mpm monitor stop --port {port}")

        return True

    except Exception as e:
        print(f"Error checking server status: {e}")
        print()
        print("Try manual checks:")
        print("  • Process list: ps aux | grep socketio")
        print("  • Port usage: lsof -i :8765")
        return False


def _restart_server(args, server_manager):
    """
    Restart the Socket.IO monitoring server.

    WHY: Users need to restart the monitoring server to apply configuration
    changes or recover from error states.

    Args:
        args: Command arguments with optional port
        server_manager: ServerManager instance

    Returns:
        bool: True if server restarted successfully, False otherwise
    """
    port = getattr(args, "port", None)

    print("Restarting Socket.IO monitoring server...")

    try:
        # If no port specified, find running servers to restart
        if port is None:
            running_servers = server_manager.list_running_servers()
            if not running_servers:
                print(
                    "No running servers found. Starting new server on default port..."
                )
                return _start_server(args, server_manager)

            # Restart the first server found
            server = running_servers[0]
            port = server.get("port", 8765)

        print(f"Using port {port} for restart...")

        # Use ServerManager's restart method
        success = server_manager.restart_server(port=port)

        if success:
            print(f"Monitor server restarted successfully on port {port}")
            print()
            print("Server management commands:")
            print("  Status: claude-mpm monitor status")
            print(f"  Stop:   claude-mpm monitor stop --port {port}")
            print(f"  Start:  claude-mpm monitor start --port {port}")
        else:
            print(f"Failed to restart server on port {port}")
            print()
            print("Troubleshooting:")
            print("  • Try stopping and starting manually:")
            print(f"    claude-mpm monitor stop --port {port}")
            print(f"    claude-mpm monitor start --port {port}")
            print("  • Check server logs for errors")

        return success

    except Exception as e:
        print(f"Error restarting server: {e}")
        print()
        print("Fallback options:")
        print("  • Manual restart: stop then start")
        print("  • Check system resources and try again")
        return False
