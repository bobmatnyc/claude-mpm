#!/usr/bin/env python3
"""
SocketIO Daemon Script for Claude MPM.

This script provides a command-line interface to the unified monitor daemon
that runs the Socket.IO server for event broadcasting and dashboard functionality.

WHY: The pyproject.toml references this as an entry point for claude-mpm-socketio,
providing a dedicated command for managing the Socket.IO daemon process.
"""

import argparse
import os
import signal
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.monitor.daemon import UnifiedMonitorDaemon
from claude_mpm.services.port_manager import PortManager

# Default paths
DEFAULT_PID_FILE = Path.home() / ".claude-mpm" / "socketio-server.pid"
DEFAULT_LOG_FILE = Path.home() / ".claude-mpm" / "logs" / "socketio" / "daemon.log"
DEFAULT_PORT = 8765

logger = get_logger(__name__)


def is_running(pid_file: Path) -> bool:
    """Check if daemon is running."""
    if not pid_file.exists():
        return False

    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())

        # Check if process exists
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        # Process doesn't exist or invalid PID
        if pid_file.exists():
            pid_file.unlink()
        return False


def start_server(port: int = DEFAULT_PORT, daemon: bool = True) -> bool:
    """Start the Socket.IO server."""
    pid_file = DEFAULT_PID_FILE
    log_file = DEFAULT_LOG_FILE

    # Ensure directories exist
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    if is_running(pid_file):
        logger.info("Socket.IO daemon is already running")
        return False

    # Use PortManager to find available port
    port_manager = PortManager()
    actual_port = port_manager.find_available_port(preferred_port=port)

    if actual_port != port:
        logger.info(f"Port {port} is in use, using port {actual_port} instead")

    # Create and start daemon
    monitor_daemon = UnifiedMonitorDaemon(
        host="localhost",
        port=actual_port,
        daemon_mode=daemon,
        pid_file=str(pid_file),
        log_file=str(log_file),
    )

    success = monitor_daemon.start()

    if success:
        logger.info(f"Socket.IO daemon started on port {actual_port}")
        # Save the port for clients to discover
        port_file = pid_file.parent / "socketio-port"
        with open(port_file, "w") as f:
            f.write(str(actual_port))
    else:
        logger.error("Failed to start Socket.IO daemon")

    return success


def stop_server() -> bool:
    """Stop the Socket.IO server."""
    pid_file = DEFAULT_PID_FILE

    if not is_running(pid_file):
        logger.info("Socket.IO daemon is not running")
        return False

    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())

        # Send SIGTERM for graceful shutdown
        os.kill(pid, signal.SIGTERM)

        # Wait for process to terminate
        for _ in range(10):
            if not is_running(pid_file):
                break
            time.sleep(0.5)

        # Force kill if still running
        if is_running(pid_file):
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)

        # Clean up files
        if pid_file.exists():
            pid_file.unlink()

        port_file = pid_file.parent / "socketio-port"
        if port_file.exists():
            port_file.unlink()

        logger.info("Socket.IO daemon stopped")
        return True

    except Exception as e:
        logger.error(f"Error stopping daemon: {e}")
        return False


def restart_server(port: int = DEFAULT_PORT) -> bool:
    """Restart the Socket.IO server."""
    logger.info("Restarting Socket.IO daemon...")

    # Stop if running
    if is_running(DEFAULT_PID_FILE):
        stop_server()
        time.sleep(1)  # Brief pause between stop and start

    # Start again
    return start_server(port=port)


def status_server() -> bool:
    """Check status of Socket.IO server."""
    pid_file = DEFAULT_PID_FILE
    port_file = pid_file.parent / "socketio-port"

    if is_running(pid_file):
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())

            port = DEFAULT_PORT
            if port_file.exists():
                with open(port_file) as f:
                    port = int(f.read().strip())

            print(f"Socket.IO daemon is running (PID: {pid}, Port: {port})")
            return True
        except Exception as e:
            print(f"Socket.IO daemon status unknown: {e}")
            return False
    else:
        print("Socket.IO daemon is not running")
        return False


def main():
    """Main entry point for socketio daemon management."""
    parser = argparse.ArgumentParser(description="Manage Claude MPM Socket.IO daemon")

    parser.add_argument(
        "command", choices=["start", "stop", "restart", "status"], help="Daemon command"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to run on (default: {DEFAULT_PORT})",
    )

    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run in foreground instead of daemon mode",
    )

    args = parser.parse_args()

    # Execute command
    if args.command == "start":
        success = start_server(port=args.port, daemon=not args.foreground)
        sys.exit(0 if success else 1)

    elif args.command == "stop":
        success = stop_server()
        sys.exit(0 if success else 1)

    elif args.command == "restart":
        success = restart_server(port=args.port)
        sys.exit(0 if success else 1)

    elif args.command == "status":
        success = status_server()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
