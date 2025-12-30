"""
Daemon Lifecycle Management for Unified Monitor
===============================================

WHY: This module provides proper daemon process lifecycle management including
daemonization, PID file management, and graceful shutdown for the unified
monitor daemon.

DESIGN DECISIONS:
- Standard Unix daemon patterns
- PID file management for process tracking
- Proper signal handling for graceful shutdown
- Log file redirection for daemon mode
"""

import json
import os
import signal
import socket
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

from ....core.enums import OperationResult
from ....core.logging_config import get_logger


class DaemonLifecycle:
    """Manages daemon process lifecycle for the unified monitor.

    WHY: Provides proper daemon process management with PID files, signal
    handling, and graceful shutdown capabilities.
    """

    def __init__(self, pid_file: str, log_file: Optional[str] = None, port: int = 8765):
        """Initialize daemon lifecycle manager.

        Args:
            pid_file: Path to PID file
            log_file: Path to log file for daemon mode
            port: Port number for startup verification
        """
        self.pid_file = Path(pid_file)
        self.log_file = Path(log_file) if log_file else None
        self.port = port
        self.logger = get_logger(__name__)
        # Create a temporary file for startup status communication
        self.startup_status_file = None

    def daemonize(self) -> bool:
        """Daemonize the current process.

        Returns:
            True if daemonization successful, False otherwise
        """
        try:
            # Clean up any existing asyncio event loops before forking
            self._cleanup_event_loops()

            # Create a temporary file for startup status communication
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".status"
            ) as f:
                self.startup_status_file = f.name
                f.write("starting")

            # First fork
            pid = os.fork()
            if pid > 0:
                # Parent process - wait for child to confirm startup
                return self._parent_wait_for_startup(pid)
        except OSError as e:
            self.logger.error(f"First fork failed: {e}")
            self._report_startup_error(f"First fork failed: {e}")
            return False

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                # First child process exits
                sys.exit(0)
        except OSError as e:
            self.logger.error(f"Second fork failed: {e}")
            self._report_startup_error(f"Second fork failed: {e}")
            return False

        # Set up error logging before redirecting streams
        self._setup_early_error_logging()

        # Write PID file first (before stream redirection)
        try:
            self.write_pid_file()
        except Exception as e:
            self._report_startup_error(f"Failed to write PID file: {e}")
            return False

        # Redirect standard file descriptors
        self._redirect_streams()

        # Setup signal handlers
        self._setup_signal_handlers()

        self.logger.info(f"Daemon process started with PID {os.getpid()}")

        # Report successful startup (after basic setup but before server start)
        self._report_startup_success()
        return True

    def _redirect_streams(self):
        """Redirect standard streams for daemon mode."""
        try:
            # Flush streams
            sys.stdout.flush()
            sys.stderr.flush()

            # Redirect stdin to /dev/null
            with Path("/dev/null").open() as null_in:
                os.dup2(null_in.fileno(), sys.stdin.fileno())

            # Redirect stdout and stderr
            if self.log_file:
                # Redirect to log file
                with self.log_file.open("a") as log_out:
                    os.dup2(log_out.fileno(), sys.stdout.fileno())
                    os.dup2(log_out.fileno(), sys.stderr.fileno())
            else:
                # Default to a daemon log file instead of /dev/null for errors
                default_log = Path.home() / ".claude-mpm" / "monitor-daemon.log"
                default_log.parent.mkdir(parents=True, exist_ok=True)
                with default_log.open("a") as log_out:
                    os.dup2(log_out.fileno(), sys.stdout.fileno())
                    os.dup2(log_out.fileno(), sys.stderr.fileno())

        except Exception as e:
            self.logger.error(f"Error redirecting streams: {e}")
            self._report_startup_error(f"Failed to redirect streams: {e}")

    def write_pid_file(self):
        """Write PID to PID file."""
        try:
            # Ensure parent directory exists
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)

            # Write PID
            with self.pid_file.open("w") as f:
                f.write(str(os.getpid()))

            self.logger.debug(f"PID file written: {self.pid_file}")

        except Exception as e:
            self.logger.error(f"Error writing PID file: {e}")
            raise

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            self.cleanup()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def is_running(self) -> bool:
        """Check if daemon is currently running.

        Returns:
            True if daemon is running, False otherwise
        """
        try:
            pid = self.get_pid()
            if pid is None:
                return False

            # Check if process exists
            os.kill(pid, 0)  # Signal 0 just checks if process exists
            return True

        except (OSError, ProcessLookupError):
            # Process doesn't exist
            self._cleanup_stale_pid_file()
            return False

    def get_pid(self) -> Optional[int]:
        """Get PID from PID file.

        Returns:
            PID if found, None otherwise
        """
        try:
            if not self.pid_file.exists():
                return None

            with self.pid_file.open() as f:
                pid_str = f.read().strip()
                return int(pid_str) if pid_str else None

        except (OSError, ValueError):
            return None

    def stop_daemon(self) -> bool:
        """Stop the running daemon.

        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            pid = self.get_pid()
            if pid is None:
                self.logger.warning("No PID file found, daemon may not be running")
                return False

            # Send SIGTERM for graceful shutdown
            self.logger.info(f"Stopping daemon with PID {pid}")
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit
            for _ in range(30):  # Wait up to 30 seconds
                if not self.is_running():
                    self.logger.info("Daemon stopped successfully")
                    return True
                time.sleep(1)

            # Force kill if still running
            self.logger.warning("Daemon didn't stop gracefully, forcing kill")
            os.kill(pid, signal.SIGKILL)

            # Wait a bit more
            for _ in range(5):
                if not self.is_running():
                    self.logger.info("Daemon force-killed successfully")
                    return True
                time.sleep(1)

            self.logger.error("Failed to stop daemon")
            return False

        except ProcessLookupError:
            # Process already dead
            self._cleanup_stale_pid_file()
            self.logger.info("Daemon was already stopped")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping daemon: {e}")
            return False

    def restart_daemon(self) -> bool:
        """Restart the daemon.

        Returns:
            True if restarted successfully, False otherwise
        """
        self.logger.info("Restarting daemon")

        # Stop first
        if not self.stop_daemon():
            return False

        # Wait a moment
        time.sleep(2)

        # Start again (this would need to be called from the main daemon)
        # For now, just return True as the actual restart logic is in the daemon
        return True

    def cleanup(self):
        """Cleanup daemon resources."""
        try:
            # Remove PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
                self.logger.debug(f"PID file removed: {self.pid_file}")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def _cleanup_stale_pid_file(self):
        """Remove stale PID file."""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                self.logger.debug("Removed stale PID file")
        except Exception as e:
            self.logger.error(f"Error removing stale PID file: {e}")

    def _cleanup_event_loops(self):
        """Clean up any existing asyncio event loops before forking.

        This prevents the 'I/O operation on closed kqueue object' error
        that occurs when forked processes inherit event loops.
        """
        try:
            import asyncio
            import gc

            # Try to get the current event loop
            try:
                loop = asyncio.get_event_loop()
                if loop and loop.is_running():
                    # Can't close a running loop, but we can stop it
                    loop.stop()
                    self.logger.debug("Stopped running event loop before fork")
                elif loop:
                    # Close the loop if it exists and is not running
                    loop.close()
                    self.logger.debug("Closed event loop before fork")
            except RuntimeError:
                # No event loop in current thread
                pass

            # Clear the event loop policy to ensure clean state
            asyncio.set_event_loop(None)

            # Force garbage collection to clean up any loop resources
            gc.collect()

        except ImportError:
            # asyncio not available (unlikely but handle it)
            pass
        except Exception as e:
            self.logger.debug(f"Error cleaning up event loops before fork: {e}")

    def get_status(self) -> dict:
        """Get daemon status information.

        Returns:
            Dictionary with status information
        """
        pid = self.get_pid()
        running = self.is_running()

        status = {
            "running": running,
            "pid": pid,
            "pid_file": str(self.pid_file),
            "log_file": str(self.log_file) if self.log_file else None,
        }

        if running and pid:
            try:
                # Get process info
                import psutil

                process = psutil.Process(pid)
                status.update(
                    {
                        "cpu_percent": process.cpu_percent(),
                        "memory_info": process.memory_info()._asdict(),
                        "create_time": process.create_time(),
                        "status": process.status(),
                    }
                )
            except ImportError:
                # psutil not available
                pass
            except Exception as e:
                self.logger.debug(f"Error getting process info: {e}")

        return status

    def _parent_wait_for_startup(self, child_pid: int, timeout: float = 10.0) -> bool:
        """Parent process waits for child daemon to report startup status.

        Args:
            child_pid: PID of the child process
            timeout: Maximum time to wait for startup

        Returns:
            True if child started successfully, False otherwise
        """
        import time

        start_time = time.time()

        # Wait for child to update status file
        while time.time() - start_time < timeout:
            try:
                # Check if status file exists and read it
                if self.startup_status_file and Path(self.startup_status_file).exists():
                    with self.startup_status_file.open() as f:
                        status = f.read().strip()

                    if status == OperationResult.SUCCESS:
                        # Child started successfully
                        self._cleanup_status_file()
                        return True
                    if status.startswith("error:"):
                        # Child reported an error
                        error_msg = status[6:]  # Remove "error:" prefix
                        self.logger.error(f"Daemon startup failed: {error_msg}")
                        print(
                            f"Error: Failed to start monitor daemon: {error_msg}",
                            file=sys.stderr,
                        )
                        self._cleanup_status_file()
                        return False
                    if status == "starting":
                        # Still starting, continue waiting
                        pass

                # Also check if child process is still alive
                try:
                    os.kill(child_pid, 0)  # Check if process exists
                except ProcessLookupError:
                    # Child process died
                    self.logger.error("Child daemon process died during startup")
                    print(
                        "Error: Monitor daemon process died during startup",
                        file=sys.stderr,
                    )
                    self._cleanup_status_file()
                    return False

            except Exception as e:
                self.logger.debug(f"Error checking startup status: {e}")

            time.sleep(0.1)  # Check every 100ms

        # Timeout reached
        self.logger.error(f"Daemon startup timed out after {timeout} seconds")
        print(
            f"Error: Monitor daemon startup timed out after {timeout} seconds",
            file=sys.stderr,
        )
        self._cleanup_status_file()
        return False

    def _report_startup_success(self):
        """Report successful startup to parent process."""
        if self.startup_status_file:
            try:
                with self.startup_status_file.open("w") as f:
                    f.write(OperationResult.SUCCESS)
            except Exception as e:
                self.logger.error(f"Failed to report startup success: {e}")

    def _report_startup_error(self, error_msg: str):
        """Report startup error to parent process.

        Args:
            error_msg: Error message to report
        """
        if self.startup_status_file:
            try:
                with self.startup_status_file.open("w") as f:
                    f.write(f"error:{error_msg}")
            except Exception:
                pass  # Can't report if file write fails

    def _cleanup_status_file(self):
        """Clean up the temporary status file."""
        if self.startup_status_file:
            try:
                Path(self.startup_status_file).unlink(missing_ok=True)
            except Exception:
                pass  # Ignore cleanup errors
            finally:
                self.startup_status_file = None

    def _setup_early_error_logging(self):
        """Set up error logging before stream redirection.

        This ensures we can capture and report errors that occur during
        daemon initialization, especially port binding errors.
        """
        try:
            # If no log file specified, create a default one
            if not self.log_file:
                default_log = Path.home() / ".claude-mpm" / "monitor-daemon.log"
                default_log.parent.mkdir(parents=True, exist_ok=True)
                self.log_file = default_log

            # Configure logger to write to file immediately
            import logging

            # Use RotatingFileHandler for automatic log rotation
            # 5MB max size, 5 backup files (consistent with project logging standards)
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=5,
            )
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        except Exception as e:
            # If we can't set up logging, at least try to report the error
            self._report_startup_error(f"Failed to setup error logging: {e}")

    def verify_port_available(
        self, host: str = "localhost"
    ) -> Tuple[bool, Optional[str]]:
        """Verify that the port is available for binding.

        Args:
            host: Host to check port on

        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_sock.bind((host, self.port))
            test_sock.close()
            return True, None
        except OSError as e:
            error_msg = f"Port {self.port} is already in use or cannot be bound: {e}"
            return False, error_msg

    def is_our_service(self, host: str = "localhost") -> Tuple[bool, Optional[int]]:
        """Check if the service on the port is our Socket.IO service.

        This uses multiple detection methods:
        1. Check health endpoint for service signature
        2. Check Socket.IO namespace availability
        3. Check process ownership if PID file exists

        Args:
            host: Host to check

        Returns:
            Tuple of (is_ours, pid_if_found)
        """
        self.logger.debug(f"Checking if service on {host}:{self.port} is ours")

        try:
            # Method 1: Check health endpoint
            import urllib.error
            import urllib.request

            health_url = f"http://{host}:{self.port}/health"
            self.logger.debug(f"Checking health endpoint: {health_url}")

            try:
                req = urllib.request.Request(health_url)
                req.add_header("User-Agent", "claude-mpm-monitor")

                with urllib.request.urlopen(req, timeout=3) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        self.logger.debug(f"Health endpoint response: {data}")

                        # Check for our service signature
                        service_name = data.get("service")
                        if service_name == "claude-mpm-monitor":
                            # Try to get PID from response
                            pid = data.get("pid")
                            if pid:
                                self.logger.info(
                                    f"Found our claude-mpm-monitor service via health endpoint, PID: {pid}"
                                )
                                return True, pid
                            # Service is ours but no PID in response
                            # Try to get from PID file
                            file_pid = self.get_pid()
                            self.logger.info(
                                f"Found our claude-mpm-monitor service via health endpoint, PID from file: {file_pid}"
                            )
                            return True, file_pid
                        self.logger.debug(
                            f"Service name '{service_name}' does not match 'claude-mpm-monitor'"
                        )

            except urllib.error.URLError as e:
                self.logger.debug(f"Health endpoint not accessible: {e}")
            except urllib.error.HTTPError as e:
                self.logger.debug(f"Health endpoint HTTP error: {e}")
            except json.JSONDecodeError as e:
                self.logger.debug(f"Health endpoint invalid JSON: {e}")
            except Exception as e:
                self.logger.debug(f"Health endpoint check failed: {e}")

            # Method 2: Check if PID file exists and process matches
            pid = self.get_pid()
            if pid:
                self.logger.debug(f"Checking PID from file: {pid}")
                try:
                    # Check if process exists
                    os.kill(pid, 0)
                    self.logger.debug(f"Process {pid} exists")

                    # Process exists, check if it's using our port
                    # This requires psutil for accurate port checking
                    try:
                        import psutil

                        process = psutil.Process(pid)

                        # Check process command line for our service
                        cmdline = " ".join(process.cmdline())
                        if "claude_mpm" in cmdline or "claude-mpm" in cmdline:
                            if "monitor" in cmdline:
                                self.logger.info(
                                    f"Found our claude-mpm monitor process via PID file, PID: {pid}"
                                )
                                return True, pid

                        # Also check if it's listening on our port
                        connections = process.connections()
                        for conn in connections:
                            if conn.laddr.port == self.port and conn.status == "LISTEN":
                                self.logger.info(
                                    f"Found process {pid} listening on our port {self.port}"
                                )
                                # Double-check it's a Python process (likely ours)
                                if "python" in process.name().lower():
                                    self.logger.info(
                                        "Confirmed as Python process, assuming it's our service"
                                    )
                                    return True, pid

                    except ImportError:
                        # psutil not available, but we have a PID file and process exists
                        # Assume it's ours since we manage the PID file
                        self.logger.info(
                            f"Found process with our PID file: {pid}, assuming it's ours (psutil not available)"
                        )
                        return True, pid
                    except psutil.NoSuchProcess:
                        self.logger.debug(f"Process {pid} no longer exists")
                    except psutil.AccessDenied:
                        # Can't access process info, but it exists - likely ours
                        self.logger.info(
                            f"Process {pid} exists but access denied, assuming it's ours"
                        )
                        return True, pid
                    except Exception as e:
                        self.logger.debug(f"Error checking process {pid}: {e}")

                except (OSError, ProcessLookupError):
                    # Process doesn't exist
                    self.logger.debug(f"Process {pid} does not exist")
                    self._cleanup_stale_pid_file()

            # Method 3: Try Socket.IO connection to check namespace
            try:
                import socketio

                sio_client = socketio.Client()

                # Try to connect with a short timeout
                connected = False

                def on_connect():
                    nonlocal connected
                    connected = True

                sio_client.on("connect", on_connect)

                try:
                    sio_client.connect(f"http://{host}:{self.port}", wait_timeout=2)
                    if connected:
                        # Successfully connected to Socket.IO
                        sio_client.disconnect()

                        # Check for orphaned process (no PID file but service running)
                        try:
                            # Try to find process using the port
                            import psutil

                            for proc in psutil.process_iter(["pid", "name"]):
                                try:
                                    for conn in proc.connections():
                                        if (
                                            conn.laddr.port == self.port
                                            and conn.status == "LISTEN"
                                        ):
                                            # Found process listening on our port
                                            if "python" in proc.name().lower():
                                                self.logger.debug(
                                                    f"Found likely orphaned claude-mpm service on port {self.port}, PID: {proc.pid}"
                                                )
                                                return True, proc.pid
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    continue
                        except ImportError:
                            pass

                        # Socket.IO service exists but can't determine if it's ours
                        self.logger.debug(
                            f"Found Socket.IO service on port {self.port}, but cannot confirm ownership"
                        )
                        return False, None

                except Exception:
                    pass
                finally:
                    if sio_client.connected:
                        sio_client.disconnect()

            except ImportError:
                # socketio not available
                pass
            except Exception as e:
                self.logger.debug(f"Error checking Socket.IO connection: {e}")

            # Method 4: Final fallback - if we have a PID file and can't definitively say it's NOT ours
            # This handles edge cases where the health endpoint might be temporarily unavailable
            if pid and self.pid_file.exists():
                try:
                    # One more check - see if process exists
                    os.kill(pid, 0)
                    self.logger.info(
                        f"PID file exists with valid process {pid}, assuming it's our stale service"
                    )
                    return True, pid
                except (OSError, ProcessLookupError):
                    pass

            # No service detected or not ours
            self.logger.debug("Service not detected as ours")
            return False, None

        except Exception as e:
            self.logger.error(f"Error checking if service is ours: {e}", exc_info=True)
            return False, None
