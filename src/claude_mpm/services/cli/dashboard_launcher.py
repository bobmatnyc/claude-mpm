"""
Dashboard Launcher Service
===========================

WHY: This service provides a centralized way to manage dashboard launching across
the application, particularly for Socket.IO monitoring and other web dashboards.
By extracting this logic from run.py, we reduce complexity and create a reusable
service for any command that needs to launch a dashboard.

DESIGN DECISIONS:
- Interface-based design (IDashboardLauncher) for testability and flexibility
- Support for multiple browser types and launch methods
- Port management integration for finding available ports
- Graceful fallback when browser launch fails
- Platform-specific optimizations for tab reuse
- Process management for standalone servers
"""

import os
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from abc import ABC, abstractmethod
from typing import Tuple

from ...core.logger import get_logger
from ...core.unified_paths import get_package_root
from ...services.port_manager import PortManager


# Interface
class IDashboardLauncher(ABC):
    """Interface for dashboard launching service."""

    @abstractmethod
    def launch_dashboard(
        self, port: int = 8765, monitor_mode: bool = True
    ) -> Tuple[bool, bool]:
        """
        Launch the web dashboard.

        Args:
            port: Port number for the dashboard server
            monitor_mode: Whether to open in monitor mode

        Returns:
            Tuple of (success, browser_opened)
        """

    @abstractmethod
    def is_dashboard_running(self, port: int = 8765) -> bool:
        """
        Check if dashboard server is running.

        Args:
            port: Port to check

        Returns:
            True if dashboard is running on the specified port
        """

    @abstractmethod
    def get_dashboard_url(self, port: int = 8765) -> str:
        """
        Get the dashboard URL.

        Args:
            port: Port number

        Returns:
            Dashboard URL string
        """

    @abstractmethod
    def stop_dashboard(self, port: int = 8765) -> bool:
        """
        Stop the dashboard server.

        Args:
            port: Port of the server to stop

        Returns:
            True if successfully stopped
        """

    @abstractmethod
    def wait_for_dashboard(self, port: int = 8765, timeout: int = 30) -> bool:
        """
        Wait for dashboard to be ready.

        Args:
            port: Port to check
            timeout: Maximum time to wait in seconds

        Returns:
            True if dashboard became ready within timeout
        """


# Implementation
class DashboardLauncher(IDashboardLauncher):
    """Dashboard launcher service implementation."""

    def __init__(self, logger=None):
        """
        Initialize the dashboard launcher.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or get_logger("DashboardLauncher")
        self.port_manager = PortManager()

    def launch_dashboard(
        self, port: int = 8765, monitor_mode: bool = True
    ) -> Tuple[bool, bool]:
        """
        Launch the web dashboard.

        WHY: Provides a unified way to launch dashboards with proper error handling,
        browser management, and server lifecycle control.

        Args:
            port: Port number for the dashboard server
            monitor_mode: Whether to open in monitor mode

        Returns:
            Tuple of (success, browser_opened)
        """
        try:
            # Verify dependencies for Socket.IO dashboard
            if monitor_mode and not self._verify_socketio_dependencies():
                return False, False

            self.logger.info(
                f"Launching dashboard (port: {port}, monitor: {monitor_mode})"
            )

            # Clean up dead instances and check for existing servers
            self.port_manager.cleanup_dead_instances()
            active_instances = self.port_manager.list_active_instances()

            # Determine the port to use
            server_port = self._determine_server_port(port, active_instances)
            server_running = self.is_dashboard_running(server_port)

            # Get dashboard URL
            dashboard_url = self.get_dashboard_url(server_port)

            if server_running:
                self.logger.info(
                    f"Dashboard server already running on port {server_port}"
                )
                print(f"✅ Dashboard server already running on port {server_port}")
                print(f"📊 Dashboard: {dashboard_url}")
            else:
                # Start the server
                print("🔧 Starting dashboard server...")
                if not self._start_dashboard_server(server_port):
                    print("❌ Failed to start dashboard server")
                    self._print_troubleshooting_tips(server_port)
                    return False, False

                print("✅ Dashboard server started successfully")
                print(f"📊 Dashboard: {dashboard_url}")

            # Open browser unless suppressed
            browser_opened = False
            if not self._is_browser_suppressed():
                print("🌐 Opening dashboard in browser...")
                browser_opened = self._open_browser(dashboard_url)
                if not browser_opened:
                    print("⚠️  Could not open browser automatically")
                    print(f"📊 Please open manually: {dashboard_url}")
            else:
                print("🌐 Browser opening suppressed (CLAUDE_MPM_NO_BROWSER=1)")
                self.logger.info("Browser opening suppressed by environment variable")

            return True, browser_opened

        except Exception as e:
            self.logger.error(f"Failed to launch dashboard: {e}")
            print(f"❌ Failed to launch dashboard: {e}")
            return False, False

    def is_dashboard_running(self, port: int = 8765) -> bool:
        """
        Check if dashboard server is running.

        WHY: Prevents duplicate server launches and helps determine if we need
        to start a new server or connect to an existing one.

        Args:
            port: Port to check

        Returns:
            True if dashboard is running on the specified port
        """
        try:
            # First, do a basic TCP connection check
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                result = s.connect_ex(("127.0.0.1", port))
                if result != 0:
                    self.logger.debug(f"TCP connection to port {port} failed")
                    return False

            # If TCP connection succeeds, try HTTP health check
            try:
                response = urllib.request.urlopen(
                    f"http://localhost:{port}/status", timeout=5
                )
                if response.getcode() == 200:
                    self.logger.debug(f"Dashboard health check passed on port {port}")
                    return True
            except Exception as e:
                self.logger.debug(f"HTTP health check failed for port {port}: {e}")
                # Server is listening but may not be fully ready yet
                return True  # Still consider it running if TCP works

        except Exception as e:
            self.logger.debug(f"Error checking dashboard on port {port}: {e}")

        return False

    def get_dashboard_url(self, port: int = 8765) -> str:
        """
        Get the dashboard URL.

        Args:
            port: Port number

        Returns:
            Dashboard URL string
        """
        return f"http://localhost:{port}"

    def stop_dashboard(self, port: int = 8765) -> bool:
        """
        Stop the dashboard server.

        WHY: Provides clean shutdown of dashboard servers to free up ports
        and resources.

        Args:
            port: Port of the server to stop

        Returns:
            True if successfully stopped
        """
        try:
            daemon_script = get_package_root() / "scripts" / "socketio_daemon.py"
            if not daemon_script.exists():
                self.logger.error(f"Daemon script not found: {daemon_script}")
                return False

            # Stop the daemon
            result = subprocess.run(
                [sys.executable, str(daemon_script), "stop", "--port", str(port)],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0:
                self.logger.info(f"Dashboard server stopped on port {port}")
                return True

            self.logger.warning(f"Failed to stop dashboard server: {result.stderr}")
            return False

        except Exception as e:
            self.logger.error(f"Error stopping dashboard server: {e}")
            return False

    def wait_for_dashboard(self, port: int = 8765, timeout: int = 30) -> bool:
        """
        Wait for dashboard to be ready.

        WHY: Ensures the dashboard is fully operational before attempting to
        open it in a browser, preventing "connection refused" errors.

        Args:
            port: Port to check
            timeout: Maximum time to wait in seconds

        Returns:
            True if dashboard became ready within timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_dashboard_running(port):
                return True
            time.sleep(0.5)
        return False

    # Private helper methods
    def _verify_socketio_dependencies(self) -> bool:
        """Verify Socket.IO dependencies are available."""
        try:
            import aiohttp
            import engineio
            import socketio

            self.logger.debug("Socket.IO dependencies verified")
            return True
        except ImportError as e:
            self.logger.error(f"Socket.IO dependencies not available: {e}")
            print(f"❌ Socket.IO dependencies missing: {e}")
            print("  Install with: pip install python-socketio aiohttp python-engineio")
            return False

    def _determine_server_port(
        self, requested_port: int, active_instances: list
    ) -> int:
        """Determine which port to use for the server."""
        if active_instances:
            # Prefer port 8765 if available
            for instance in active_instances:
                if instance.get("port") == 8765:
                    return 8765
            # Otherwise use first active instance
            return active_instances[0].get("port", requested_port)
        return requested_port

    def _start_dashboard_server(self, port: int) -> bool:
        """Start the dashboard server."""
        try:
            daemon_script = get_package_root() / "scripts" / "socketio_daemon.py"
            if not daemon_script.exists():
                self.logger.error(f"Daemon script not found: {daemon_script}")
                return False

            # Start the daemon
            result = subprocess.run(
                [sys.executable, str(daemon_script), "start", "--port", str(port)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                self.logger.info(f"Dashboard server started on port {port}")
                # Wait for server to be ready
                return self.wait_for_dashboard(port, timeout=10)

            self.logger.error(f"Failed to start dashboard server: {result.stderr}")
            return False

        except Exception as e:
            self.logger.error(f"Error starting dashboard server: {e}")
            return False

    def _is_browser_suppressed(self) -> bool:
        """Check if browser opening is suppressed."""
        return os.environ.get("CLAUDE_MPM_NO_BROWSER") == "1"

    def _open_browser(self, url: str) -> bool:
        """
        Open URL in browser with platform-specific optimizations.

        WHY: Different platforms have different ways to reuse browser tabs.
        This method tries platform-specific approaches before falling back
        to the standard webbrowser module.
        """
        try:
            system = platform.system().lower()

            if system == "darwin":  # macOS
                try:
                    # Try to open in existing tab with -g flag (background)
                    subprocess.run(["open", "-g", url], check=True, timeout=5)
                    self.logger.info("Opened browser on macOS")
                    return True
                except Exception:
                    pass

            elif system == "linux":
                try:
                    # Try xdg-open for Linux
                    subprocess.run(["xdg-open", url], check=True, timeout=5)
                    self.logger.info("Opened browser on Linux")
                    return True
                except Exception:
                    pass

            elif system == "windows":
                try:
                    # Try to use existing browser window
                    webbrowser.get().open(url, new=0)
                    self.logger.info("Opened browser on Windows")
                    return True
                except Exception:
                    pass

            # Fallback to standard webbrowser module
            webbrowser.open(url, new=0, autoraise=True)
            self.logger.info("Opened browser using webbrowser module")
            return True

        except Exception as e:
            self.logger.warning(f"Browser opening failed: {e}")
            try:
                # Final fallback
                webbrowser.open(url)
                return True
            except Exception:
                return False

    def _print_troubleshooting_tips(self, port: int):
        """Print troubleshooting tips for dashboard launch failures."""
        print("💡 Troubleshooting tips:")
        print(f"   - Check if port {port} is already in use")
        print("   - Verify Socket.IO dependencies: pip install python-socketio aiohttp")
        print("   - Try a different port with --websocket-port")
        print("   - Check firewall settings for localhost connections")
