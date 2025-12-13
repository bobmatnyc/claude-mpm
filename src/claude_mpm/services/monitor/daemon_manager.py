"""
Unified Daemon Manager Service
==============================

WHY: This service consolidates ALL daemon lifecycle operations into a single place,
eliminating duplicate code and race conditions from having daemon management logic
scattered across multiple files.

DESIGN DECISIONS:
- Single source of truth for all daemon operations
- Robust port cleanup with retry logic
- Thread-safe operations with proper locking
- Comprehensive error handling and recovery
- Supports both foreground and background/daemon modes
- Manages PID files, port conflicts, and process lifecycle

This replaces duplicate logic that was in:
- UnifiedMonitorDaemon._cleanup_port_conflicts()
- UnifiedDashboardManager._cleanup_port_conflicts()
- Various daemon startup/stop logic spread across files
"""

import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

from ...core.enums import OperationResult
from ...core.logging_config import get_logger

# Exit code constants for signal handling
EXIT_NORMAL = 0
EXIT_SIGKILL = 137  # 128 + SIGKILL(9) - forced termination
EXIT_SIGTERM = 143  # 128 + SIGTERM(15) - graceful shutdown


class DaemonManager:
    """Centralized manager for all daemon lifecycle operations.

    This is the SINGLE source of truth for:
    - Port conflict resolution
    - Process cleanup
    - Daemon startup/stop
    - PID file management
    - Service detection
    """

    # Class-level lock for thread safety
    _lock = threading.Lock()

    def __init__(
        self,
        port: int = 8765,
        host: str = "localhost",
        pid_file: Optional[str] = None,
        log_file: Optional[str] = None,
    ):
        """Initialize the daemon manager.

        Args:
            port: Port number for the daemon
            host: Host to bind to
            pid_file: Path to PID file (uses default if None)
            log_file: Path to log file for daemon mode
        """
        self.port = port
        self.host = host
        self.logger = get_logger(__name__)

        # Set up paths
        if pid_file:
            self.pid_file = Path(pid_file)
        else:
            self.pid_file = self._get_default_pid_file()

        self.log_file = Path(log_file) if log_file else self._get_default_log_file()

        # Startup status communication
        self.startup_status_file = None

    def _get_default_pid_file(self) -> Path:
        """Get default PID file path with port number to support multiple daemons."""
        project_root = Path.cwd()
        claude_mpm_dir = project_root / ".claude-mpm"
        claude_mpm_dir.mkdir(exist_ok=True)
        # Include port in filename to support multiple daemon instances
        return claude_mpm_dir / f"monitor-daemon-{self.port}.pid"

    def _get_default_log_file(self) -> Path:
        """Get default log file path with port number to support multiple daemons."""
        project_root = Path.cwd()
        claude_mpm_dir = project_root / ".claude-mpm"
        claude_mpm_dir.mkdir(exist_ok=True)
        # Include port in filename to support multiple daemon instances
        return claude_mpm_dir / f"monitor-daemon-{self.port}.log"

    def cleanup_port_conflicts(self, max_retries: int = 3) -> bool:
        """Clean up any processes using the daemon port.

        This is the SINGLE implementation for port cleanup, replacing
        duplicate logic in multiple files.

        Args:
            max_retries: Maximum number of cleanup attempts

        Returns:
            True if port is available after cleanup, False otherwise
        """
        with self._lock:
            for attempt in range(max_retries):
                if attempt > 0:
                    self.logger.info(
                        f"Port cleanup attempt {attempt + 1}/{max_retries}"
                    )

                # First check if port is actually in use
                if self._is_port_available():
                    self.logger.debug(f"Port {self.port} is available")
                    return True

                self.logger.info(f"Port {self.port} is in use, attempting cleanup")

                # Try to find and kill processes using the port
                if self._kill_processes_on_port():
                    # Wait for port to be released
                    time.sleep(2 if attempt == 0 else 3)

                    # Verify port is now free
                    if self._is_port_available():
                        self.logger.info(f"Port {self.port} successfully cleaned up")
                        return True

                if attempt < max_retries - 1:
                    # Wait longer between attempts
                    time.sleep(3)

            self.logger.error(
                f"Failed to clean up port {self.port} after {max_retries} attempts"
            )
            return False

    def _is_port_available(self) -> bool:
        """Check if the port is available for binding.

        Returns:
            True if port is available, False otherwise
        """
        # Try to bind to the port using the same method as the actual server
        # We only need to check if we can bind to at least one address family
        try:
            # Try IPv4 first (most common)
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Use 127.0.0.1 for localhost to match what the server does
            bind_host = "127.0.0.1" if self.host == "localhost" else self.host
            test_sock.bind((bind_host, self.port))
            test_sock.close()
            return True
        except OSError:
            # IPv4 failed, try IPv6
            try:
                test_sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_sock.bind(("::1", self.port))
                test_sock.close()
                return True
            except Exception:
                # Both IPv4 and IPv6 failed - port is in use
                return False

    def _kill_processes_on_port(self) -> bool:
        """Kill processes using the daemon port.

        Returns:
            True if processes were killed or none found, False on error
        """
        try:
            # Try using lsof first (most reliable)
            if self._kill_using_lsof():
                return True

            # Fallback to checking our known PID file
            if self._kill_using_pid_file():
                return True

            # Try to identify claude-mpm processes
            return bool(self._kill_claude_mpm_processes())

        except Exception as e:
            self.logger.error(f"Error killing processes on port: {e}")
            return False

    def _kill_using_lsof(self) -> bool:
        """Kill processes using lsof to find them.

        Returns:
            True if successful or lsof not available, False on error
        """
        try:
            # Find processes using the port
            result = subprocess.run(
                ["lsof", "-ti", f":{self.port}"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0 or not result.stdout.strip():
                self.logger.debug(f"No processes found using port {self.port}")
                return True

            pids = result.stdout.strip().split("\n")
            self.logger.info(f"Found processes using port {self.port}: {pids}")

            # Kill each process
            for pid_str in pids:
                try:
                    pid = int(pid_str.strip())

                    # Check if it's a Python/Claude process
                    process_info = subprocess.run(
                        ["ps", "-p", str(pid), "-o", "comm="],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    # Get full command to check if it's our monitor process
                    cmd_info = subprocess.run(
                        ["ps", "-p", str(pid), "-o", "command="],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if cmd_info.returncode != 0:
                        continue

                    full_command = cmd_info.stdout.strip().lower()
                    process_name = process_info.stdout.strip().lower()

                    # Check if this is our monitor/socketio process specifically
                    # Look for monitor, socketio, dashboard, or our specific port
                    is_monitor = any(
                        [
                            "monitor" in full_command,
                            "socketio" in full_command,
                            "dashboard" in full_command,
                            f"port={self.port}" in full_command,
                            f":{self.port}" in full_command,
                            "unified_monitor" in full_command,
                        ]
                    )

                    if is_monitor and "python" in process_name:
                        self.logger.info(
                            f"Killing monitor process {pid}: {full_command[:100]}"
                        )
                        os.kill(pid, signal.SIGTERM)

                        # Wait briefly for graceful shutdown
                        time.sleep(1)

                        # Check if still alive and force kill if needed
                        try:
                            os.kill(pid, 0)  # Check if process exists
                            self.logger.warning(
                                f"Process {pid} didn't terminate, force killing"
                            )
                            os.kill(pid, signal.SIGKILL)
                            time.sleep(0.5)
                        except ProcessLookupError:
                            pass  # Process already dead
                    else:
                        # Not a monitor process - log but don't fail
                        self.logger.info(
                            f"Skipping non-monitor process {pid} ({process_name})"
                        )
                        # Continue to next PID - don't return False
                        continue

                except (ValueError, ProcessLookupError) as e:
                    self.logger.debug(f"Error handling PID {pid_str}: {e}")
                    continue

            return True

        except FileNotFoundError:
            # lsof not available
            self.logger.debug("lsof not available, using alternative methods")
            return True
        except Exception as e:
            self.logger.error(f"Error using lsof: {e}")
            return False

    def _kill_using_pid_file(self) -> bool:
        """Kill process using PID file.

        Returns:
            True if successful or no PID file, False on error
        """
        try:
            if not self.pid_file.exists():
                return True

            with self.pid_file.open() as f:
                pid = int(f.read().strip())

            self.logger.info(f"Found PID {pid} in PID file")

            # Kill the process
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)

                # Check if still alive
                try:
                    os.kill(pid, 0)
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.5)
                except ProcessLookupError:
                    pass

                # Remove PID file
                self.pid_file.unlink(missing_ok=True)
                return True

            except ProcessLookupError:
                # Process doesn't exist, just remove PID file
                self.pid_file.unlink(missing_ok=True)
                return True

        except Exception as e:
            self.logger.error(f"Error killing process from PID file: {e}")
            return False

    def _kill_claude_mpm_processes(self) -> bool:
        """Kill any claude-mpm monitor processes specifically.

        This targets monitor/dashboard/socketio processes only,
        NOT general Claude instances.

        Returns:
            True if successful, False on error
        """
        try:
            # Look for monitor-specific processes
            result = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True, check=False
            )

            if result.returncode != 0:
                return False

            lines = result.stdout.strip().split("\n")
            killed_any = False

            for line in lines:
                line_lower = line.lower()
                # Only target monitor/dashboard/socketio processes
                if any(
                    [
                        "monitor" in line_lower and "claude" in line_lower,
                        "dashboard" in line_lower and "claude" in line_lower,
                        "socketio" in line_lower,
                        f":{self.port}" in line_lower and "python" in line_lower,
                    ]
                ):
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                            self.logger.info(
                                f"Killing claude-mpm monitor process {pid}"
                            )
                            os.kill(pid, signal.SIGTERM)
                            killed_any = True
                            time.sleep(0.5)
                        except (ValueError, ProcessLookupError):
                            continue

            if killed_any:
                time.sleep(1)  # Give processes time to exit

            return True

        except Exception as e:
            self.logger.error(f"Error killing claude-mpm processes: {e}")
            return False

    def is_our_service(self) -> Tuple[bool, Optional[int]]:
        """Check if the service on the port is our claude-mpm monitor.

        Returns:
            Tuple of (is_ours, pid) where is_ours is True if it's our service
        """
        try:
            # First check PID file
            if self.pid_file.exists():
                try:
                    with self.pid_file.open() as f:
                        pid = int(f.read().strip())

                    # Verify process exists
                    os.kill(pid, 0)

                    # Check if it's a Python process
                    process_info = subprocess.run(
                        ["ps", "-p", str(pid), "-o", "comm="],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if "python" in process_info.stdout.lower():
                        return True, pid

                except (ValueError, ProcessLookupError, subprocess.CalledProcessError):
                    # PID file exists but process doesn't or isn't Python
                    self.pid_file.unlink(missing_ok=True)

            # Check if service responds to our health endpoint
            try:
                import requests

                response = requests.get(
                    f"http://{self.host}:{self.port}/health", timeout=2
                )

                if response.status_code == 200:
                    # Try to get service info
                    try:
                        data = response.json()
                        if "claude" in str(data).lower() or "mpm" in str(data).lower():
                            # It's likely our service, try to find PID
                            pid = self._find_service_pid()
                            return True, pid
                    except Exception:
                        pass

            except Exception:
                pass

            return False, None

        except Exception as e:
            self.logger.error(f"Error checking service ownership: {e}")
            return False, None

    def _find_service_pid(self) -> Optional[int]:
        """Find PID of service on our port using lsof.

        Returns:
            PID if found, None otherwise
        """
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{self.port}"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                if pids:
                    return int(pids[0].strip())

        except Exception:
            pass

        return None

    def _verify_daemon_health(self, max_attempts: int = 3) -> bool:
        """Verify daemon is healthy by checking HTTP health endpoint.

        Args:
            max_attempts: Maximum number of connection attempts

        Returns:
            True if health check passes, False otherwise
        """
        try:
            import requests

            for attempt in range(max_attempts):
                try:
                    # Try to connect to health endpoint
                    response = requests.get(
                        f"http://{self.host}:{self.port}/health", timeout=2
                    )

                    if response.status_code == 200:
                        self.logger.debug(
                            f"Health check passed on attempt {attempt + 1}/{max_attempts}"
                        )
                        return True

                    self.logger.debug(
                        f"Health check returned status {response.status_code} on attempt {attempt + 1}/{max_attempts}"
                    )

                except requests.exceptions.RequestException as e:
                    self.logger.debug(
                        f"Health check attempt {attempt + 1}/{max_attempts} failed: {e}"
                    )

                # Wait before retry (except on last attempt)
                if attempt < max_attempts - 1:
                    time.sleep(1)

            self.logger.debug(f"Health check failed after {max_attempts} attempts")
            return False

        except ImportError:
            # requests not available, skip health check
            self.logger.debug("requests library not available, skipping health check")
            return True
        except Exception as e:
            self.logger.debug(f"Health check error: {e}")
            return False

    def start_daemon(self, force_restart: bool = False) -> bool:
        """Start the daemon with automatic cleanup and retry.

        Args:
            force_restart: Force restart even if already running

        Returns:
            True if daemon started successfully
        """
        with self._lock:
            # Check if already running
            if self.is_running():
                if not force_restart:
                    pid = self.get_pid()
                    self.logger.info(f"Daemon already running with PID {pid}")
                    return True

                # Stop existing daemon
                self.logger.info("Force restarting daemon")
                if not self.stop_daemon():
                    self.logger.error("Failed to stop existing daemon")
                    return False

                # Wait for cleanup
                time.sleep(2)

            # Clean up port conflicts
            if not self.cleanup_port_conflicts():
                self.logger.error(f"Cannot start daemon - port {self.port} is in use")
                return False

            # Use subprocess for clean daemon startup (v4.2.40)
            # This avoids fork() issues with Python threading
            if self.use_subprocess_daemon():
                return self.start_daemon_subprocess(force_restart=force_restart)
            # Fallback to traditional fork (kept for compatibility)
            return self.daemonize()

    def use_subprocess_daemon(self) -> bool:
        """Check if we should use subprocess instead of fork for daemonization.

        Returns:
            True to use subprocess (safer), False to use traditional fork
        """
        # Check if we're already in a subprocess to prevent infinite recursion
        if os.environ.get("CLAUDE_MPM_SUBPROCESS_DAEMON") == "1":
            # We're already in a subprocess, use traditional fork
            return False

        # Otherwise, use subprocess for monitor daemon to avoid threading issues
        return True

    def start_daemon_subprocess(self, force_restart: bool = False) -> bool:
        """Start daemon using subprocess.Popen for clean process isolation.

        This avoids all the fork() + threading issues by starting the monitor
        in a completely fresh process with no inherited threads or locks.

        Args:
            force_restart: Whether this is a force restart (helps interpret exit codes)

        Returns:
            True if daemon started successfully
        """
        try:
            # Build command to run monitor in foreground mode in subprocess
            import sys

            python_exe = sys.executable

            # Run 'claude-mpm monitor start' in subprocess with environment variable
            # to indicate we're already in a subprocess (prevents infinite recursion)
            cmd = [
                python_exe,
                "-m",
                "claude_mpm.cli",
                "monitor",
                "start",
                "--background",  # Run as daemon
                "--port",
                str(self.port),
                "--host",
                self.host,
            ]

            # Set environment variable to prevent recursive subprocess creation
            env = os.environ.copy()
            env["CLAUDE_MPM_SUBPROCESS_DAEMON"] = "1"

            self.logger.info(f"Starting monitor daemon via subprocess: {' '.join(cmd)}")

            # Open log file for output redirection
            log_file_handle = None
            if self.log_file:
                log_file_handle = Path(self.log_file).open("a")
                log_file = log_file_handle
            else:
                log_file = subprocess.DEVNULL

            try:
                # Start the subprocess detached from parent
                # Redirect stdout/stderr to log file to capture output
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT if self.log_file else subprocess.DEVNULL,
                    start_new_session=True,  # Create new process group
                    close_fds=(not self.log_file),  # Keep log file open if redirecting
                    env=env,  # Pass modified environment
                )

                # Close the log file handle now that subprocess has it
                if log_file_handle:
                    log_file_handle.close()

                # Get the process PID
                pid = process.pid
                self.logger.info(f"Monitor subprocess started with PID {pid}")

                # Wait for the subprocess to write its PID file and bind to port
                # The subprocess will write the PID file after it starts successfully
                max_wait = 10  # seconds
                start_time = time.time()
                pid_file_found = False
                port_bound = False

                self.logger.debug(f"Waiting up to {max_wait}s for daemon to start...")

                while time.time() - start_time < max_wait:
                    # Check if process is still running
                    returncode = process.poll()
                    if returncode is not None:
                        # Process exited - interpret exit code with context
                        # Exit codes 137 (SIGKILL) and 143 (SIGTERM) are common during daemon replacement
                        if returncode == EXIT_SIGKILL:
                            # SIGKILL - process was forcefully terminated
                            if force_restart:
                                # This is expected during force restart - old daemon was killed
                                self.logger.info(
                                    f"Previous monitor instance replaced (exit {EXIT_SIGKILL}: SIGKILL during force restart)"
                                )
                            else:
                                # Unexpected SIGKILL - something else killed our new daemon
                                self.logger.warning(
                                    f"Monitor subprocess terminated unexpectedly (exit {EXIT_SIGKILL}: SIGKILL). "
                                    f"Check {self.log_file} for details."
                                )
                            return False
                        if returncode == EXIT_SIGTERM:
                            # SIGTERM - graceful shutdown requested
                            self.logger.info(
                                f"Monitor subprocess cleanly terminated (exit {EXIT_SIGTERM}: SIGTERM, graceful shutdown)"
                            )
                            return False
                        if returncode == EXIT_NORMAL:
                            # Normal exit
                            self.logger.info(
                                f"Monitor subprocess exited normally (exit code {EXIT_NORMAL})"
                            )
                            return False
                        # Unexpected exit code - this IS an error
                        self.logger.error(
                            f"Monitor daemon subprocess exited prematurely with code {returncode}"
                        )
                        self.logger.error(
                            f"Port {self.port} daemon failed to start. Check {self.log_file} for details."
                        )
                        return False

                    # Check if PID file was written
                    if not pid_file_found and self.pid_file.exists():
                        try:
                            with self.pid_file.open() as f:
                                written_pid = int(f.read().strip())
                            if written_pid == pid:
                                pid_file_found = True
                                self.logger.debug(
                                    f"PID file found with correct PID {pid}"
                                )
                        except Exception as e:
                            self.logger.debug(f"Error reading PID file: {e}")

                    # Check if port is bound (health check)
                    if not port_bound and not self._is_port_available():
                        # Port NOT available means it's in use (good!)
                        port_bound = True
                        self.logger.debug(f"Port {self.port} is now bound")

                    # Success criteria: both PID file exists and port is bound
                    if pid_file_found and port_bound:
                        self.logger.info(
                            f"Monitor daemon successfully started on port {self.port} (PID: {pid})"
                        )
                        # Additional health check: verify we can connect
                        if self._verify_daemon_health(max_attempts=3):
                            self.logger.info("Daemon health check passed")
                            return True
                        self.logger.warning(
                            "Daemon started but health check failed - may still be initializing"
                        )
                        return (
                            True  # Return success anyway if PID file and port are good
                        )

                    time.sleep(0.5)

                # Timeout waiting for daemon to start
                self.logger.error("Timeout waiting for monitor daemon to start")
                # Try to kill the process if it's still running
                if process.poll() is None:
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
                return False
            finally:
                # Clean up log file handle if still open
                if log_file_handle and not log_file_handle.closed:
                    log_file_handle.close()

        except Exception as e:
            self.logger.error(f"Failed to start daemon via subprocess: {e}")
            return False

    def daemonize(self) -> bool:
        """Daemonize the current process.

        Returns:
            True if successful (in parent), doesn't return in child
        """
        # Guard against re-entrant execution after fork
        if hasattr(self, "_forking_in_progress"):
            self.logger.error(
                "CRITICAL: Detected re-entrant daemonize call after fork!"
            )
            return False

        self._forking_in_progress = True

        try:
            # Clean up asyncio event loops before forking
            self._cleanup_event_loops()

            # Create status file for communication
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".status"
            ) as f:
                self.startup_status_file = f.name
                f.write("starting")

            # First fork
            pid = os.fork()
            if pid > 0:
                # Parent process - wait for child to confirm startup
                del self._forking_in_progress  # Clean up in parent
                return self._parent_wait_for_startup(pid)

        except OSError as e:
            self.logger.error(f"First fork failed: {e}")
            return False

        # Child process continues...

        # Decouple from parent
        os.chdir("/")
        os.setsid()
        os.umask(0)

        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                # First child exits
                sys.exit(0)
        except OSError as e:
            self.logger.error(f"Second fork failed: {e}")
            self._report_startup_error(f"Second fork failed: {e}")
            sys.exit(1)

        # Grandchild process - the actual daemon

        # Write PID file
        self.write_pid_file()

        # Redirect streams
        self._redirect_streams()

        # Setup signal handlers
        self._setup_signal_handlers()

        self.logger.info(f"Daemon process started with PID {os.getpid()}")

        # DO NOT report success here - let the caller report after starting the service
        # This prevents race conditions where we report success before the server starts
        # self._report_startup_success()  # REMOVED - caller must report

        # Note: Daemon process continues running
        # Caller is responsible for running the actual service AND reporting status
        return True

    def stop_daemon(self, timeout: int = 10) -> bool:
        """Stop the daemon process.

        Args:
            timeout: Maximum time to wait for daemon to stop

        Returns:
            True if stopped successfully
        """
        with self._lock:
            try:
                pid = self.get_pid()
                if not pid:
                    self.logger.info("No daemon PID found")
                    # Still try to clean up port
                    self.cleanup_port_conflicts()
                    return True

                self.logger.info(f"Stopping daemon with PID {pid}")

                # Send SIGTERM for graceful shutdown
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    # Process already dead
                    self.cleanup_pid_file()
                    return True

                # Wait for process to exit
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        os.kill(pid, 0)  # Check if still alive
                        time.sleep(0.5)
                    except ProcessLookupError:
                        # Process exited
                        self.cleanup_pid_file()
                        return True

                # Force kill if still running
                self.logger.warning("Daemon didn't stop gracefully, force killing")
                try:
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(1)
                except ProcessLookupError:
                    pass

                self.cleanup_pid_file()
                return True

            except Exception as e:
                self.logger.error(f"Error stopping daemon: {e}")
                return False

    def is_running(self) -> bool:
        """Check if daemon is running.

        Returns:
            True if daemon is running
        """
        try:
            pid = self.get_pid()
            if not pid:
                return False

            # Check if process exists
            os.kill(pid, 0)
            return True

        except ProcessLookupError:
            # Process doesn't exist
            self.cleanup_pid_file()
            return False

    def get_pid(self) -> Optional[int]:
        """Get daemon PID from PID file.

        Returns:
            PID if found, None otherwise
        """
        try:
            if not self.pid_file.exists():
                return None

            with self.pid_file.open() as f:
                return int(f.read().strip())

        except Exception as e:
            self.logger.error(f"Error reading PID file: {e}")
            return None

    def write_pid_file(self):
        """Write current PID to PID file."""
        try:
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            with self.pid_file.open("w") as f:
                f.write(str(os.getpid()))
            self.logger.debug(f"PID file written: {self.pid_file}")
        except Exception as e:
            self.logger.error(f"Error writing PID file: {e}")
            raise

    def cleanup_pid_file(self):
        """Remove PID file."""
        try:
            self.pid_file.unlink(missing_ok=True)
            self.logger.debug("PID file removed")
        except Exception as e:
            self.logger.error(f"Error removing PID file: {e}")

    def _cleanup_event_loops(self):
        """Clean up asyncio event loops before forking."""
        try:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop and not loop.is_closed():
                    # Cancel pending tasks
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()

                    # Stop and close loop
                    if loop.is_running():
                        loop.stop()

                    asyncio.set_event_loop(None)
                    loop.close()

            except RuntimeError:
                # No event loop
                pass

        except Exception as e:
            self.logger.debug(f"Error cleaning up event loops: {e}")

    def _redirect_streams(self):
        """Redirect standard streams for daemon mode."""
        try:
            sys.stdout.flush()
            sys.stderr.flush()

            # Redirect stdin to /dev/null
            with Path("/dev/null").open() as null_in:
                os.dup2(null_in.fileno(), sys.stdin.fileno())

            # Redirect stdout and stderr to log file
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("a") as log_out:
                os.dup2(log_out.fileno(), sys.stdout.fileno())
                os.dup2(log_out.fileno(), sys.stderr.fileno())

        except Exception as e:
            self.logger.error(f"Error redirecting streams: {e}")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down")
            self.cleanup_pid_file()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _parent_wait_for_startup(self, child_pid: int, timeout: float = 10.0) -> bool:
        """Parent process waits for child to confirm startup.

        Args:
            child_pid: PID of child process
            timeout: Maximum time to wait

        Returns:
            True if child started successfully
        """
        try:
            start_time = time.time()

            while time.time() - start_time < timeout:
                if (
                    not self.startup_status_file
                    or not Path(self.startup_status_file).exists()
                ):
                    time.sleep(0.1)
                    continue

                try:
                    with self.startup_status_file.open() as f:
                        status = f.read().strip()

                    if status == OperationResult.SUCCESS:
                        # Cleanup status file
                        Path(self.startup_status_file).unlink(missing_ok=True)
                        return True

                    if status.startswith("error:"):
                        error_msg = status[6:]
                        self.logger.error(f"Daemon startup failed: {error_msg}")
                        Path(self.startup_status_file).unlink(missing_ok=True)
                        return False

                except Exception:
                    pass

                time.sleep(0.1)

            self.logger.error("Daemon startup timed out")
            return False

        except Exception as e:
            self.logger.error(f"Error waiting for daemon startup: {e}")
            return False

    def _report_startup_success(self):
        """Report successful startup to parent process."""
        if self.startup_status_file:
            try:
                # Don't check if file exists - we need to write to it regardless
                # The parent created it and is waiting for us to update it
                with self.startup_status_file.open("w") as f:
                    f.write(OperationResult.SUCCESS)
                    f.flush()  # Ensure it's written immediately
                    os.fsync(f.fileno())  # Force write to disk
            except Exception:
                # Logging might not work in daemon process after fork
                pass

    def _report_startup_error(self, error: str):
        """Report startup error to parent process."""
        if self.startup_status_file:
            try:
                # Don't check if file exists - we need to write to it regardless
                with self.startup_status_file.open("w") as f:
                    f.write(f"error:{error}")
                    f.flush()  # Ensure it's written immediately
                    os.fsync(f.fileno())  # Force write to disk
            except Exception as e:
                # Try to write error to a debug file since logging might not work
                try:
                    with Path("/tmp/daemon_debug_error.txt").open("a") as debug:
                        debug.write(f"Error reporting error: {e}\n")
                        debug.write(f"Status file: {self.startup_status_file}\n")
                except Exception:
                    pass
