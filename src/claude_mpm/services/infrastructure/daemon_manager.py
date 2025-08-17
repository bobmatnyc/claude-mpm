from pathlib import Path

#!/usr/bin/env python3
"""
Daemon Management Service for Socket.IO Server
==============================================

Provides daemon management functionality for the Socket.IO server including
start, stop, restart, and status operations with proper process management.

This service handles:
- Process lifecycle management (start/stop/restart)
- PID file management
- Signal handling for graceful shutdown
- Conflict detection with other server instances
- Status monitoring and health checks
"""

import logging
import os
import signal
import subprocess
import sys
import time
from typing import Any, Dict, Optional

try:
    import psutil
except ImportError:
    # Auto-install psutil if not available
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

# from claude_mpm.core.base_service import BaseService
from claude_mpm.services.socketio.server.main import SocketIOServer

logger = logging.getLogger(__name__)


class SocketIODaemonManager:
    """
    Daemon management service for Socket.IO server.

    Provides comprehensive daemon lifecycle management including process
    monitoring, conflict detection, and graceful shutdown handling.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Initialize the daemon manager.

        Args:
            host: Host to bind the server to
            port: Port to bind the server to
        """
        # super().__init__()
        self.host = host
        self.port = port

        # Configuration paths
        self.config_dir = Path.home() / ".claude-mpm"
        self.pid_file = self.config_dir / "socketio-server.pid"
        self.log_file = self.config_dir / "socketio-server.log"

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def is_running(self) -> bool:
        """
        Check if the daemon server is currently running.

        Returns:
            True if server is running, False otherwise
        """
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            # Check if process exists and is running
            process = psutil.Process(pid)
            return process.is_running()

        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
            # Clean up stale PID file
            self.pid_file.unlink(missing_ok=True)
            return False

    def _check_port_conflict(self) -> Optional[Dict[str, Any]]:
        """
        Check for existing server on the target port.

        Returns:
            Server info if conflict detected, None otherwise
        """
        try:
            import requests

            response = requests.get(
                f"http://{self.host}:{self.port}/health", timeout=1.0
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def start(self) -> bool:
        """
        Start the Socket.IO server as a daemon.

        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running():
            logger.info("Socket.IO daemon server is already running")
            return False

        # Check for port conflicts
        conflict_info = self._check_port_conflict()
        if conflict_info and "server_id" in conflict_info:
            logger.warning(
                f"Port {self.port} already in use by: {conflict_info.get('server_id')}"
            )
            return False

        try:
            # Fork to create daemon process
            pid = os.fork()
            if pid > 0:
                # Parent process - save PID and exit
                with open(self.pid_file, "w") as f:
                    f.write(str(pid))
                logger.info(f"Socket.IO server started as daemon (PID: {pid})")
                return True

            # Child process - become daemon
            self._daemonize()
            self._run_server()

        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            return False

    def _daemonize(self) -> None:
        """Convert the current process into a daemon."""
        # Create new session
        os.setsid()
        os.umask(0)

        # Redirect stdout/stderr to log file
        with open(self.log_file, "a") as log:
            os.dup2(log.fileno(), sys.stdout.fileno())
            os.dup2(log.fileno(), sys.stderr.fileno())

    def _run_server(self) -> None:
        """Run the Socket.IO server in daemon mode."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Socket.IO server...")

        # Create and configure server
        server = SocketIOServer(host=self.host, port=self.port)

        # Setup signal handlers
        def signal_handler(signum, frame):
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received signal {signum}, shutting down..."
            )
            server.stop()
            self.pid_file.unlink(missing_ok=True)
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Start server and keep running
        server.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)

    def stop(self) -> bool:
        """
        Stop the daemon server.

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_running():
            logger.info("Socket.IO daemon server is not running")
            return False

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            logger.info(f"Stopping Socket.IO server (PID: {pid})")

            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)

            # Wait for graceful shutdown
            for _ in range(10):
                if not self.is_running():
                    logger.info("Socket.IO server stopped successfully")
                    self.pid_file.unlink(missing_ok=True)
                    return True
                time.sleep(0.5)

            # Force kill if still running
            logger.warning("Server didn't stop gracefully, forcing shutdown")
            os.kill(pid, signal.SIGKILL)
            self.pid_file.unlink(missing_ok=True)
            return True

        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return False

    def restart(self) -> bool:
        """
        Restart the daemon server.

        Returns:
            True if restarted successfully, False otherwise
        """
        logger.info("Restarting Socket.IO daemon server")
        self.stop()
        time.sleep(1)
        return self.start()

    def status(self) -> Dict[str, Any]:
        """
        Get detailed status information about the daemon.

        Returns:
            Dictionary containing status information
        """
        status_info = {
            "running": self.is_running(),
            "pid_file": str(self.pid_file),
            "log_file": str(self.log_file),
            "host": self.host,
            "port": self.port,
            "management_style": "daemon",
        }

        if status_info["running"]:
            with open(self.pid_file) as f:
                status_info["pid"] = int(f.read().strip())

            # Check port accessibility
            try:
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((self.host, self.port))
                sock.close()
                status_info["port_accessible"] = result == 0
            except:
                status_info["port_accessible"] = False

            # Check for conflicts
            conflict_info = self._check_port_conflict()
            if conflict_info and "server_id" in conflict_info:
                server_id = conflict_info.get("server_id")
                if server_id != "daemon-socketio":
                    status_info["conflict_detected"] = True
                    status_info["conflicting_server"] = server_id

        return status_info
