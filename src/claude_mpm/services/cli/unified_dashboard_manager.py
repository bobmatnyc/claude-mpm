"""
Unified Dashboard Manager Service
=================================

WHY: This service provides a centralized way to manage dashboard functionality using
the UnifiedMonitorDaemon. It replaces the old DashboardLauncher and SocketIOManager
services with a cleaner implementation that uses the unified daemon architecture.

DESIGN DECISIONS:
- Uses UnifiedMonitorDaemon for all server functionality
- Provides the same interface as the old services for compatibility
- Handles browser opening, process management, and status checking
- Integrates with PortManager for port allocation
- Thread-safe daemon management
"""

import threading
import time
import webbrowser
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

import requests

from ...core.logging_config import get_logger
from ...services.monitor.daemon import UnifiedMonitorDaemon
from ...services.monitor.daemon_manager import DaemonManager
from ...services.port_manager import PortManager


@dataclass
class DashboardInfo:
    """Information about a running dashboard."""

    url: str
    port: int
    pid: Optional[int] = None
    status: str = "running"


class IUnifiedDashboardManager(ABC):
    """Interface for unified dashboard management."""

    @abstractmethod
    def start_dashboard(
        self, port: int = 8765, background: bool = False, open_browser: bool = True
    ) -> Tuple[bool, bool]:
        """Start the dashboard using unified daemon."""

    @abstractmethod
    def stop_dashboard(self, port: int = 8765) -> bool:
        """Stop the dashboard."""

    @abstractmethod
    def is_dashboard_running(self, port: int = 8765) -> bool:
        """Check if dashboard is running."""

    @abstractmethod
    def get_dashboard_url(self, port: int = 8765) -> str:
        """Get dashboard URL."""

    @abstractmethod
    def open_browser(self, url: str) -> bool:
        """Open URL in browser."""


class UnifiedDashboardManager(IUnifiedDashboardManager):
    """Unified dashboard manager using UnifiedMonitorDaemon."""

    def __init__(self, logger=None):
        """Initialize the unified dashboard manager."""
        self.logger = logger or get_logger("UnifiedDashboardManager")
        self.port_manager = PortManager()
        self._background_daemons = {}  # port -> daemon instance
        self._lock = threading.Lock()

    def start_dashboard(
        self,
        port: int = 8765,
        background: bool = False,
        open_browser: bool = True,
        force_restart: bool = False,
    ) -> Tuple[bool, bool]:
        """
        Start the dashboard using unified daemon.

        Args:
            port: Port to run dashboard on
            background: Whether to run in background mode
            open_browser: Whether to open browser automatically
            force_restart: If True, restart existing service if it's ours

        Returns:
            Tuple of (success, browser_opened)
        """
        try:
            # Create daemon instance to check service status
            daemon = UnifiedMonitorDaemon(
                host="localhost", port=port, daemon_mode=background
            )

            # Use daemon manager to check service ownership
            daemon_mgr = DaemonManager(port=port, host="localhost")
            is_ours, pid = daemon_mgr.is_our_service()

            if is_ours and not force_restart:
                # Our service is already running, just open browser if needed
                self.logger.info(
                    f"Our dashboard already running on port {port} (PID: {pid})"
                )
                browser_opened = False
                if open_browser:
                    browser_opened = self.open_browser(self.get_dashboard_url(port))
                return True, browser_opened
            if is_ours and force_restart:
                self.logger.info(
                    f"Force restarting our dashboard on port {port} (PID: {pid})"
                )
                # Don't cleanup here - let daemon.start(force_restart=True) handle it
                # This prevents race conditions where we kill the service we're trying to start
            elif self.is_dashboard_running(port) and not force_restart:
                # Different service is using the port - don't clean it up without force_restart
                self.logger.warning(
                    f"Port {port} is in use by a different service. Use force_restart to override."
                )
                return False, False

            self.logger.info(
                f"Starting unified dashboard on port {port} (background: {background}, force_restart: {force_restart})"
            )

            if background:
                # The daemon.start() method will handle cleanup when force_restart=True
                # We don't need pre-emptive cleanup here as it causes race conditions
                
                # Try to start daemon with retry on port conflicts
                max_retries = 3
                retry_count = 0
                success = False

                while retry_count < max_retries and not success:
                    if retry_count > 0:
                        # Only cleanup on retries, not on first attempt
                        self.logger.info(
                            f"Retry {retry_count}/{max_retries}: Cleaning up port {port}"
                        )
                        daemon_mgr = DaemonManager(port=port, host="localhost")
                        if not daemon_mgr.cleanup_port_conflicts():
                            self.logger.error(f"Cleanup failed on retry {retry_count}")
                            break
                        time.sleep(3)  # Longer wait for cleanup to complete

                    # Start daemon in background mode with force restart
                    # The daemon.start() method handles its own cleanup when force_restart=True
                    success = daemon.start(force_restart=force_restart)

                    if not success and retry_count < max_retries - 1:
                        # Check if it's a port conflict
                        if not self.port_manager.is_port_available(port):
                            self.logger.warning(
                                f"Port {port} still in use, will retry cleanup"
                            )
                            retry_count += 1
                        else:
                            # Different kind of failure, don't retry
                            self.logger.error(
                                "Daemon start failed for reason other than port conflict"
                            )
                            break
                    else:
                        break

                if success:
                    with self._lock:
                        self._background_daemons[port] = daemon

                    # Wait for daemon to be ready
                    if self._wait_for_dashboard(port, timeout=10):
                        browser_opened = False
                        if open_browser:
                            browser_opened = self.open_browser(
                                self.get_dashboard_url(port)
                            )
                        return True, browser_opened
                    self.logger.error("Dashboard daemon started but not responding")
                    return False, False
                self.logger.error("Failed to start dashboard daemon")
                return False, False
            # For foreground mode, the caller should handle the daemon directly
            # This is used by the CLI command that runs in foreground
            self.logger.info("Foreground mode should be handled by caller")
            return True, False

        except Exception as e:
            self.logger.error(f"Error starting dashboard: {e}")
            return False, False

    def stop_dashboard(self, port: int = 8765) -> bool:
        """
        Stop the dashboard.

        Args:
            port: Port of dashboard to stop

        Returns:
            True if successfully stopped
        """
        try:
            # Check if we have a background daemon for this port
            with self._lock:
                daemon = self._background_daemons.get(port)
                if daemon:
                    daemon.stop()
                    del self._background_daemons[port]
                    self.logger.info(f"Stopped background daemon on port {port}")
                    return True

            # Try to stop via process management
            # Check if port is in use (is_port_available returns False if in use)
            if not self.port_manager.is_port_available(port):
                # Use port manager to find and stop the process
                active_instances = self.port_manager.list_active_instances()
                for instance in active_instances:
                    if instance.get("port") == port:
                        pid = instance.get("pid")
                        if pid:
                            try:
                                import psutil

                                process = psutil.Process(pid)
                                process.terminate()
                                process.wait(timeout=5)
                                self.logger.info(
                                    f"Terminated dashboard process {pid} on port {port}"
                                )
                                return True
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to terminate process {pid}: {e}"
                                )

            self.logger.warning(f"No dashboard found running on port {port}")
            return False

        except Exception as e:
            self.logger.error(f"Error stopping dashboard: {e}")
            return False

    def is_dashboard_running(self, port: int = 8765) -> bool:
        """
        Check if dashboard is running.

        Args:
            port: Port to check

        Returns:
            True if dashboard is running
        """
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_dashboard_url(self, port: int = 8765) -> str:
        """
        Get dashboard URL.

        Args:
            port: Port number

        Returns:
            Dashboard URL
        """
        return f"http://localhost:{port}"

    def open_browser(self, url: str) -> bool:
        """
        Open URL in browser.

        Args:
            url: URL to open

        Returns:
            True if browser was opened successfully
        """
        try:
            self.logger.info(f"Opening browser to {url}")
            webbrowser.open(url)
            return True
        except Exception as e:
            self.logger.warning(f"Failed to open browser: {e}")
            return False

    def _wait_for_dashboard(self, port: int, timeout: int = 30) -> bool:
        """
        Wait for dashboard to be ready.

        Args:
            port: Port to check
            timeout: Maximum time to wait

        Returns:
            True if dashboard became ready
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_dashboard_running(port):
                return True
            time.sleep(0.5)
        return False

    def get_dashboard_info(self, port: int = 8765) -> Optional[DashboardInfo]:
        """
        Get information about running dashboard.

        Args:
            port: Port to check

        Returns:
            DashboardInfo if running, None otherwise
        """
        if self.is_dashboard_running(port):
            return DashboardInfo(
                url=self.get_dashboard_url(port), port=port, status="running"
            )
        return None

    def ensure_dependencies(self) -> Tuple[bool, Optional[str]]:
        """
        Ensure required dependencies are available.

        Returns:
            Tuple of (dependencies_ok, error_message)
        """
        try:
            import aiohttp
            import socketio

            return True, None
        except ImportError as e:
            error_msg = f"Required dependencies missing: {e}"
            return False, error_msg

    def find_available_port(self, preferred_port: int = 8765) -> int:
        """
        Find an available port starting from the preferred port.

        Args:
            preferred_port: Preferred port to start checking from

        Returns:
            Available port number
        """
        return self.port_manager.find_available_port(preferred_port)

    def _cleanup_port_conflicts(self, port: int) -> bool:
        """
        Try to clean up any processes using our port.

        Delegates to the consolidated DaemonManager for consistent behavior.

        Args:
            port: Port to clean up

        Returns:
            True if cleanup was successful or not needed
        """
        daemon_mgr = DaemonManager(port=port, host="localhost")
        return daemon_mgr.cleanup_port_conflicts()

    def start_server(
        self, port: Optional[int] = None, timeout: int = 30, force_restart: bool = True
    ) -> Tuple[bool, DashboardInfo]:
        """
        Start the server (compatibility method for SocketIOManager interface).

        Args:
            port: Port to use (finds available if None)
            timeout: Timeout for startup
            force_restart: If True, restart existing service if it's ours

        Returns:
            Tuple of (success, DashboardInfo)
        """
        if port is None:
            port = self.find_available_port()

        # Use force_restart to ensure we're using the latest code
        success, browser_opened = self.start_dashboard(
            port=port, background=True, open_browser=False, force_restart=force_restart
        )

        if success:
            dashboard_info = DashboardInfo(
                url=self.get_dashboard_url(port), port=port, status="running"
            )
            return True, dashboard_info
        return False, DashboardInfo(url="", port=port, status="failed")

    def is_server_running(self, port: int) -> bool:
        """
        Check if server is running (compatibility method for SocketIOManager interface).

        Args:
            port: Port to check

        Returns:
            True if server is running
        """
        return self.is_dashboard_running(port)

    def stop_server(self, port: Optional[int] = None, timeout: int = 10) -> bool:
        """
        Stop the server (compatibility method for SocketIOManager interface).

        Args:
            port: Port to stop (stops all if None)
            timeout: Timeout for shutdown

        Returns:
            True if stopped successfully
        """
        if port is None:
            # Stop all background daemons
            with self._lock:
                ports_to_stop = list(self._background_daemons.keys())

            success = True
            for p in ports_to_stop:
                if not self.stop_dashboard(p):
                    success = False
            return success
        return self.stop_dashboard(port)
