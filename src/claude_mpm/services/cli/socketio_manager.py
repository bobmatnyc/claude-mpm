"""
Socket.IO Server Manager Service
=================================

WHY: This service extracts Socket.IO server management from run.py to provide a
centralized, reusable service for managing Socket.IO server lifecycle. This reduces
run.py complexity by ~200-250 lines and provides a clean interface for server management.

DESIGN DECISIONS:
- Interface-based design (ISocketIOManager) for testability and flexibility
- Integrates with existing PortManager for port allocation
- Provides server process management with graceful shutdown
- Handles dependency checking and installation prompts
- Manages server lifecycle (start, stop, status, wait)
- Thread-safe server state management
"""

import os
import signal
import socket
import subprocess
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

from ...core.logger import get_logger
from ...core.unified_paths import get_package_root, get_scripts_dir
from ...services.port_manager import PortManager
from ...utils.dependency_manager import ensure_socketio_dependencies


@dataclass
class ServerInfo:
    """Information about a running Socket.IO server."""

    port: int
    pid: Optional[int]
    is_running: bool
    launch_time: Optional[float]
    url: str


# Interface
class ISocketIOManager(ABC):
    """Interface for Socket.IO server management."""

    @abstractmethod
    def start_server(
        self, port: Optional[int] = None, timeout: int = 30
    ) -> Tuple[bool, ServerInfo]:
        """
        Start the Socket.IO server.

        Args:
            port: Optional specific port to use. If None, finds available port.
            timeout: Maximum time to wait for server startup

        Returns:
            Tuple of (success, ServerInfo)
        """

    @abstractmethod
    def stop_server(self, port: Optional[int] = None, timeout: int = 10) -> bool:
        """
        Stop the Socket.IO server.

        Args:
            port: Optional specific port to stop. If None, stops all servers.
            timeout: Maximum time to wait for graceful shutdown

        Returns:
            True if server was stopped successfully
        """

    @abstractmethod
    def is_server_running(self, port: int) -> bool:
        """
        Check if a Socket.IO server is running on the specified port.

        Args:
            port: Port to check

        Returns:
            True if server is running on the port
        """

    @abstractmethod
    def get_server_info(self, port: int) -> ServerInfo:
        """
        Get information about a server on the specified port.

        Args:
            port: Port to check

        Returns:
            ServerInfo object with server details
        """

    @abstractmethod
    def wait_for_server(self, port: int, timeout: int = 30) -> bool:
        """
        Wait for a server to be ready on the specified port.

        Args:
            port: Port to wait for
            timeout: Maximum time to wait in seconds

        Returns:
            True if server became ready within timeout
        """

    @abstractmethod
    def find_available_port(self, preferred_port: int = 8765) -> int:
        """
        Find an available port for the Socket.IO server.

        Args:
            preferred_port: Preferred port to try first

        Returns:
            Available port number
        """

    @abstractmethod
    def check_dependencies(self) -> bool:
        """
        Check if monitoring dependencies are installed and print helpful messages.

        Returns:
            True if all dependencies are available
        """

    @abstractmethod
    def ensure_dependencies(self) -> Tuple[bool, Optional[str]]:
        """
        Ensure Socket.IO dependencies are installed.

        Returns:
            Tuple of (success, error_message)
        """


# Implementation
class SocketIOManager(ISocketIOManager):
    """Socket.IO server manager implementation."""

    def __init__(self, logger=None):
        """
        Initialize the Socket.IO manager.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or get_logger("SocketIOManager")
        self.port_manager = PortManager()
        self._server_processes = {}  # port -> subprocess.Popen
        self._lock = threading.Lock()

    def start_server(
        self, port: Optional[int] = None, timeout: int = 30
    ) -> Tuple[bool, ServerInfo]:
        """
        Start the Socket.IO server.

        WHY: Provides a unified way to start Socket.IO servers with proper error handling,
        port management, and process lifecycle control.

        Args:
            port: Optional specific port to use. If None, finds available port.
            timeout: Maximum time to wait for server startup

        Returns:
            Tuple of (success, ServerInfo)
        """
        with self._lock:
            # Determine port to use
            target_port = port if port else self.find_available_port()

            # Check if server already running on this port
            if self.is_server_running(target_port):
                # Verify the server is healthy and responding
                if self.wait_for_server(target_port, timeout=2):
                    self.logger.info(
                        f"Healthy Socket.IO server already running on port {target_port}"
                    )
                    return True, self.get_server_info(target_port)
                # Server exists but not responding, try to clean it up
                self.logger.warning(
                    f"Socket.IO server on port {target_port} not responding, attempting cleanup"
                )
                self.stop_server(port=target_port, timeout=5)
                # Continue with starting a new server

            # Ensure dependencies are available
            deps_ok, error_msg = self.ensure_dependencies()
            if not deps_ok:
                self.logger.error(f"Socket.IO dependencies not available: {error_msg}")
                return False, ServerInfo(
                    port=target_port,
                    pid=None,
                    is_running=False,
                    launch_time=None,
                    url=f"http://localhost:{target_port}",
                )

            # Start the server
            try:
                self.logger.info(f"Starting Socket.IO server on port {target_port}")

                # Get the socketio daemon script path using proper resource resolution
                try:
                    from ...core.unified_paths import get_package_resource_path

                    daemon_script = get_package_resource_path(
                        "scripts/socketio_daemon_wrapper.py"
                    )
                except FileNotFoundError:
                    # Fallback to old method for development environments
                    scripts_dir = get_scripts_dir()
                    daemon_script = scripts_dir / "socketio_daemon_wrapper.py"

                    if not daemon_script.exists():
                        self.logger.error(
                            f"Socket.IO daemon script not found: {daemon_script}"
                        )
                        return False, ServerInfo(
                            port=target_port,
                            pid=None,
                            is_running=False,
                            launch_time=None,
                            url=f"http://localhost:{target_port}",
                        )

                # Start the server process
                env = os.environ.copy()
                env["PYTHONPATH"] = str(get_package_root())

                process = subprocess.Popen(
                    [sys.executable, str(daemon_script), "--port", str(target_port)],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,  # Detach from parent process group
                )

                # Store process reference
                self._server_processes[target_port] = process

                # Wait for server to be ready
                if self.wait_for_server(target_port, timeout):
                    self.logger.info(
                        f"Socket.IO server started successfully on port {target_port}"
                    )
                    return True, self.get_server_info(target_port)
                self.logger.error(
                    f"Socket.IO server failed to start within {timeout} seconds"
                )
                # Clean up failed process
                self._cleanup_process(target_port)
                return False, ServerInfo(
                    port=target_port,
                    pid=None,
                    is_running=False,
                    launch_time=None,
                    url=f"http://localhost:{target_port}",
                )

            except Exception as e:
                self.logger.error(f"Failed to start Socket.IO server: {e}")
                return False, ServerInfo(
                    port=target_port,
                    pid=None,
                    is_running=False,
                    launch_time=None,
                    url=f"http://localhost:{target_port}",
                )

    def stop_server(self, port: Optional[int] = None, timeout: int = 10) -> bool:
        """
        Stop the Socket.IO server.

        WHY: Provides graceful shutdown of Socket.IO servers with proper cleanup
        and process termination.

        Args:
            port: Optional specific port to stop. If None, stops all servers.
            timeout: Maximum time to wait for graceful shutdown

        Returns:
            True if server was stopped successfully
        """
        with self._lock:
            if port:
                return self._stop_server_on_port(port, timeout)
            # Stop all managed servers
            success = True
            for server_port in list(self._server_processes.keys()):
                if not self._stop_server_on_port(server_port, timeout):
                    success = False
            return success

    def _stop_server_on_port(self, port: int, timeout: int) -> bool:
        """Stop server on specific port."""
        try:
            # Check if we have a process reference
            if port in self._server_processes:
                process = self._server_processes[port]

                # Send graceful shutdown signal
                if process.poll() is None:  # Process is still running
                    self.logger.info(f"Stopping Socket.IO server on port {port}")
                    process.terminate()

                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=timeout)
                        self.logger.info(
                            f"Socket.IO server on port {port} stopped gracefully"
                        )
                    except subprocess.TimeoutExpired:
                        # Force kill if graceful shutdown failed
                        self.logger.warning(
                            f"Force killing Socket.IO server on port {port}"
                        )
                        process.kill()
                        process.wait()

                # Clean up process reference
                del self._server_processes[port]
                return True

            # Try to stop server by port (external process)
            process_info = self.port_manager.get_process_on_port(port)
            if process_info and process_info.is_ours:
                try:
                    os.kill(process_info.pid, signal.SIGTERM)
                    time.sleep(2)  # Give it time to shut down

                    # Check if still running
                    try:
                        os.kill(process_info.pid, 0)  # Check if process exists
                        # Still running, force kill
                        os.kill(process_info.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Process already terminated

                    self.logger.info(
                        f"Stopped Socket.IO server (PID: {process_info.pid}) on port {port}"
                    )
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to stop server on port {port}: {e}")
                    return False

            return True  # No server to stop

        except Exception as e:
            self.logger.error(f"Error stopping server on port {port}: {e}")
            return False

    def _cleanup_process(self, port: int):
        """Clean up failed or terminated process."""
        if port in self._server_processes:
            process = self._server_processes[port]
            try:
                if process.poll() is None:
                    process.kill()
                    process.wait()
            except:
                pass
            del self._server_processes[port]

    def is_server_running(self, port: int) -> bool:
        """
        Check if a Socket.IO server is running on the specified port.

        WHY: Quick check to determine if a server is already running to avoid
        conflicts and duplicates.

        Args:
            port: Port to check

        Returns:
            True if server is running on the port
        """
        # First check our managed processes
        if port in self._server_processes:
            process = self._server_processes[port]
            if process.poll() is None:
                return True
            # Process terminated, clean up
            self._cleanup_process(port)

        # Check if port is in use (by any process)
        process_info = self.port_manager.get_process_on_port(port)
        if process_info:
            # Check if it's a Socket.IO server
            return (
                "socketio" in process_info.cmdline.lower()
                or "socket-io" in process_info.cmdline.lower()
                or process_info.is_daemon
            )

        return False

    def get_server_info(self, port: int) -> ServerInfo:
        """
        Get information about a server on the specified port.

        Args:
            port: Port to check

        Returns:
            ServerInfo object with server details
        """
        is_running = self.is_server_running(port)
        pid = None
        launch_time = None

        if is_running:
            # Get process info
            if port in self._server_processes:
                process = self._server_processes[port]
                pid = process.pid
                launch_time = time.time()  # Approximate
            else:
                process_info = self.port_manager.get_process_on_port(port)
                if process_info:
                    pid = process_info.pid

        return ServerInfo(
            port=port,
            pid=pid,
            is_running=is_running,
            launch_time=launch_time,
            url=f"http://localhost:{port}",
        )

    def wait_for_server(self, port: int, timeout: int = 30) -> bool:
        """
        Wait for a server to be ready on the specified port.

        WHY: Ensures the server is fully started and ready to accept connections
        before proceeding with other operations.

        Args:
            port: Port to wait for
            timeout: Maximum time to wait in seconds

        Returns:
            True if server became ready within timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Try to connect to the server
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(("localhost", port))
                    if result == 0:
                        self.logger.debug(f"Socket.IO server ready on port {port}")
                        return True
            except Exception:
                pass

            time.sleep(0.5)

        return False

    def find_available_port(self, preferred_port: int = 8765) -> int:
        """
        Find an available port for the Socket.IO server.

        WHY: Automatically finds an available port to avoid conflicts when the
        preferred port is already in use.

        Args:
            preferred_port: Preferred port to try first

        Returns:
            Available port number
        """
        # First check if our Socket.IO server is already running on the preferred port
        if self.is_server_running(preferred_port):
            # Check if it's healthy
            if self.wait_for_server(preferred_port, timeout=2):
                self.logger.info(
                    f"Healthy Socket.IO server already running on port {preferred_port}"
                )
                return preferred_port
            self.logger.warning(
                f"Socket.IO server on port {preferred_port} not responding, will try to restart"
            )

        # Try preferred port first if available
        if self.port_manager.is_port_available(preferred_port):
            return preferred_port

        # Find alternative port using the correct method name
        available_port = self.port_manager.find_available_port(
            preferred_port=preferred_port, reclaim=True
        )

        if available_port:
            self.logger.info(
                f"Port {preferred_port} unavailable, using {available_port}"
            )
            return available_port
        # If no port found, raise an error
        raise RuntimeError(
            f"No available ports in range {self.port_manager.PORT_RANGE.start}-"
            f"{self.port_manager.PORT_RANGE.stop-1}"
        )

    def check_dependencies(self) -> bool:
        """Check if monitoring dependencies are installed."""
        missing = []
        try:
            import socketio
        except ImportError:
            missing.append("python-socketio")
        try:
            import aiohttp
        except ImportError:
            missing.append("aiohttp")
        try:
            import engineio
        except ImportError:
            missing.append("python-engineio")

        if missing:
            print(f"Missing dependencies for monitoring: {', '.join(missing)}")
            print("\nTo install all monitoring dependencies:")
            print("  pip install claude-mpm[monitor]")
            print("\nOr install manually:")
            print(f"  pip install {' '.join(missing)}")
            return False
        return True

    def ensure_dependencies(self) -> Tuple[bool, Optional[str]]:
        """
        Ensure Socket.IO dependencies are installed.

        WHY: Verifies that required Socket.IO packages are available before
        attempting to start the server.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Use existing dependency manager
            success, error_msg = ensure_socketio_dependencies(self.logger)

            if not success:
                # Provide helpful error message with improved guidance
                missing = []
                try:
                    import socketio
                except ImportError:
                    missing.append("python-socketio")
                try:
                    import aiohttp
                except ImportError:
                    missing.append("aiohttp")
                try:
                    import engineio
                except ImportError:
                    missing.append("python-engineio")

                if missing:
                    detailed_error = (
                        f"Missing dependencies for monitoring: {', '.join(missing)}\n"
                        "To install all monitoring dependencies:\n"
                        "  pip install claude-mpm[monitor]\n"
                        "Or install manually:\n"
                        f"  pip install {' '.join(missing)}"
                    )
                    return False, detailed_error

                if error_msg:
                    return False, error_msg
                return False, (
                    "Socket.IO dependencies not installed. "
                    "Install with: pip install python-socketio aiohttp python-engineio "
                    "or pip install claude-mpm[monitor]"
                )

            return True, None

        except Exception as e:
            return False, str(e)
