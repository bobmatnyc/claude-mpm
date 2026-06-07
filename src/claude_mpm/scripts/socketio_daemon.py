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
from claude_mpm.services.monitor.daemon_manager import DaemonManager
from claude_mpm.services.port_manager import PortManager

# Default port and log path.
# NOTE: There is intentionally NO module-level DEFAULT_PID_FILE constant because
# PID files are port-keyed and must be computed per-call via _pid_file_for_port().
# A fixed module-level path caused stop/status/restart to always look at port 8765
# even when the daemon was started on a different port (issue #695).
DEFAULT_PORT = 8765
DEFAULT_LOG_FILE = Path.home() / ".claude-mpm" / "logs" / "socketio" / "daemon.log"

logger = get_logger(__name__)


def _pid_file_for_port(port: int) -> Path:
    """Return the canonical PID-file path for a given port.

    WHAT: Delegates to DaemonManager.get_pid_file_for_port so the wrapper and
          the running daemon share a single path resolver and CANNOT drift apart.
    WHY:  The previous implementation returned ~/.claude-mpm/socketio-server-{port}.pid
          while the actual running daemon (re-exec'd by DaemonManager) wrote
          <project>/.claude-mpm/monitor-daemon-{port}.pid.  That mismatch caused
          start to time out (post-start poll watched the wrong file) and
          status/stop/restart to report "not running" for a provably live daemon
          (issue #695).  Wiring both sides to DaemonManager.get_pid_file_for_port
          makes a future rename break both callers at once.
    """
    return DaemonManager.get_pid_file_for_port(port)


def is_running(pid_file: Path) -> bool:
    """Check if daemon is running."""
    if not pid_file.exists():
        return False

    try:
        with pid_file.open() as f:
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
    # PID file is port-keyed so multiple instances on different ports don't collide.
    pid_file = _pid_file_for_port(port)
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
        # Recompute PID file for the actual port in use
        pid_file = _pid_file_for_port(actual_port)

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
        with port_file.open("w") as f:
            f.write(str(actual_port))
    else:
        logger.error("Failed to start Socket.IO daemon")

    return success


def stop_server(port: int = DEFAULT_PORT) -> bool:
    """Stop the Socket.IO server.

    NOTE: Callers MUST pass the actual port the daemon is running on; if omitted
    the default 8765 is assumed, which silently reads the wrong PID file for any
    other port — exactly the mismatch that caused issue #695.
    """
    pid_file = _pid_file_for_port(port)

    if not is_running(pid_file):
        logger.info("Socket.IO daemon is not running")
        return False

    try:
        with pid_file.open() as f:
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
    """Restart the Socket.IO server.

    NOTE: Callers MUST pass the actual port; defaulting to 8765 will operate on
    the wrong PID file for any other port (issue #695).
    """
    logger.info("Restarting Socket.IO daemon...")

    # Stop if running (use port-keyed PID file, not the hardcoded default)
    if is_running(_pid_file_for_port(port)):
        stop_server(port=port)
        time.sleep(1)  # Brief pause between stop and start

    # Start again
    return start_server(port=port)


def status_server(port: int = DEFAULT_PORT) -> bool:
    """Check status of Socket.IO server.

    NOTE: Callers MUST pass the actual port; defaulting to 8765 will check the
    wrong PID file for any other port (issue #695).
    """
    pid_file = _pid_file_for_port(port)
    port_file = pid_file.parent / "socketio-port"

    if is_running(pid_file):
        try:
            with pid_file.open() as f:
                pid = int(f.read().strip())

            # Prefer the advertised port from the port-discovery file; fall back to
            # the port we were asked about (which is already correct for this pid_file).
            actual_port = port
            if port_file.exists():
                with port_file.open() as f:
                    actual_port = int(f.read().strip())

            print(f"Socket.IO daemon is running (PID: {pid}, Port: {actual_port})")
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
        success = stop_server(port=args.port)
        sys.exit(0 if success else 1)

    elif args.command == "restart":
        success = restart_server(port=args.port)
        sys.exit(0 if success else 1)

    elif args.command == "status":
        success = status_server(port=args.port)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
