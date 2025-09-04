"""
Unified Monitor Daemon for Claude MPM
=====================================

WHY: This is the main daemon process that provides a single, stable way to
launch all monitoring functionality. It combines HTTP dashboard serving,
Socket.IO event handling, real AST analysis, and Claude Code hook ingestion.

DESIGN DECISIONS:
- Single process replaces multiple competing server implementations
- Daemon-ready with proper lifecycle management
- Real AST analysis using CodeTreeAnalyzer
- Single port (8765) for all functionality
- Built on proven aiohttp + socketio foundation
"""

import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from ...core.logging_config import get_logger
from .management.health import HealthMonitor
from .management.lifecycle import DaemonLifecycle
from .server import UnifiedMonitorServer


class UnifiedMonitorDaemon:
    """Unified daemon process for all Claude MPM monitoring functionality.

    WHY: Provides a single, stable entry point for launching monitoring services.
    Replaces the multiple competing server implementations with one cohesive daemon.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        daemon_mode: bool = False,
        pid_file: Optional[str] = None,
        log_file: Optional[str] = None,
    ):
        """Initialize the unified monitor daemon.

        Args:
            host: Host to bind to
            port: Port to bind to
            daemon_mode: Whether to run as background daemon
            pid_file: Path to PID file for daemon mode
            log_file: Path to log file for daemon mode
        """
        self.host = host
        self.port = port
        self.daemon_mode = daemon_mode
        self.logger = get_logger(__name__)

        # Daemon management
        self.lifecycle = DaemonLifecycle(
            pid_file=pid_file or self._get_default_pid_file(), log_file=log_file
        )

        # Core server
        self.server = UnifiedMonitorServer(host=host, port=port)

        # Health monitoring
        self.health_monitor = HealthMonitor(port=port)

        # State
        self.running = False
        self.shutdown_event = threading.Event()

    def _get_default_pid_file(self) -> str:
        """Get default PID file path."""
        project_root = Path.cwd()
        claude_mpm_dir = project_root / ".claude-mpm"
        claude_mpm_dir.mkdir(exist_ok=True)
        return str(claude_mpm_dir / "monitor-daemon.pid")

    def start(self) -> bool:
        """Start the unified monitor daemon.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            if self.daemon_mode:
                return self._start_daemon()
            return self._start_foreground()
        except Exception as e:
            self.logger.error(f"Failed to start unified monitor daemon: {e}")
            return False

    def _start_daemon(self) -> bool:
        """Start as background daemon process."""
        self.logger.info("Starting unified monitor daemon in background mode")

        # Check if already running
        if self.lifecycle.is_running():
            existing_pid = self.lifecycle.get_pid()
            self.logger.warning(f"Daemon already running with PID {existing_pid}")
            return False

        # Daemonize the process
        success = self.lifecycle.daemonize()
        if not success:
            return False

        # Start the server in daemon mode
        return self._run_server()

    def _start_foreground(self) -> bool:
        """Start in foreground mode."""
        self.logger.info(f"Starting unified monitor daemon on {self.host}:{self.port}")

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

        # Start the server
        return self._run_server()

    def _run_server(self) -> bool:
        """Run the main server loop."""
        try:
            # Start health monitoring
            self.health_monitor.start()

            # Start the unified server
            success = self.server.start()
            if not success:
                self.logger.error("Failed to start unified monitor server")
                return False

            self.running = True
            self.logger.info("Unified monitor daemon started successfully")

            # Keep running until shutdown
            if self.daemon_mode:
                # In daemon mode, run until shutdown signal
                while self.running and not self.shutdown_event.is_set():
                    time.sleep(1)
            else:
                # In foreground mode, run until interrupted
                try:
                    while self.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    self.logger.info("Received keyboard interrupt, shutting down...")

            return True

        except Exception as e:
            self.logger.error(f"Error running unified monitor daemon: {e}")
            return False
        finally:
            self._cleanup()

    def stop(self) -> bool:
        """Stop the unified monitor daemon.

        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            self.logger.info("Stopping unified monitor daemon")

            # Signal shutdown
            self.running = False
            self.shutdown_event.set()

            # Stop server
            if self.server:
                self.server.stop()

            # Stop health monitoring
            if self.health_monitor:
                self.health_monitor.stop()

            # Cleanup daemon files
            if self.daemon_mode:
                self.lifecycle.cleanup()

            self.logger.info("Unified monitor daemon stopped")
            return True

        except Exception as e:
            self.logger.error(f"Error stopping unified monitor daemon: {e}")
            return False

    def restart(self) -> bool:
        """Restart the unified monitor daemon.

        Returns:
            True if restarted successfully, False otherwise
        """
        self.logger.info("Restarting unified monitor daemon")

        # Stop first
        if not self.stop():
            return False

        # Wait a moment
        time.sleep(2)

        # Start again
        return self.start()

    def status(self) -> dict:
        """Get daemon status information.

        Returns:
            Dictionary with status information
        """
        is_running = self.lifecycle.is_running() if self.daemon_mode else self.running
        pid = self.lifecycle.get_pid() if self.daemon_mode else os.getpid()

        status = {
            "running": is_running,
            "pid": pid,
            "host": self.host,
            "port": self.port,
            "daemon_mode": self.daemon_mode,
            "health": (
                self.health_monitor.get_status() if self.health_monitor else "unknown"
            ),
        }

        if self.server:
            status.update(self.server.get_status())

        return status

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _cleanup(self):
        """Cleanup resources."""
        try:
            if self.server:
                self.server.stop()

            if self.health_monitor:
                self.health_monitor.stop()

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
