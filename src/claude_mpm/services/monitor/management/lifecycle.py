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

import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from ....core.logging_config import get_logger


class DaemonLifecycle:
    """Manages daemon process lifecycle for the unified monitor.

    WHY: Provides proper daemon process management with PID files, signal
    handling, and graceful shutdown capabilities.
    """

    def __init__(self, pid_file: str, log_file: Optional[str] = None):
        """Initialize daemon lifecycle manager.

        Args:
            pid_file: Path to PID file
            log_file: Path to log file for daemon mode
        """
        self.pid_file = Path(pid_file)
        self.log_file = Path(log_file) if log_file else None
        self.logger = get_logger(__name__)

    def daemonize(self) -> bool:
        """Daemonize the current process.

        Returns:
            True if daemonization successful, False otherwise
        """
        try:
            # Clean up any existing asyncio event loops before forking
            self._cleanup_event_loops()

            # First fork
            pid = os.fork()
            if pid > 0:
                # Parent process exits
                sys.exit(0)
        except OSError as e:
            self.logger.error(f"First fork failed: {e}")
            return False

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                # Parent process exits
                sys.exit(0)
        except OSError as e:
            self.logger.error(f"Second fork failed: {e}")
            return False

        # Redirect standard file descriptors
        self._redirect_streams()

        # Write PID file
        self.write_pid_file()

        # Setup signal handlers
        self._setup_signal_handlers()

        self.logger.info(f"Daemon process started with PID {os.getpid()}")
        return True

    def _redirect_streams(self):
        """Redirect standard streams for daemon mode."""
        try:
            # Flush streams
            sys.stdout.flush()
            sys.stderr.flush()

            # Redirect stdin to /dev/null
            with open("/dev/null") as null_in:
                os.dup2(null_in.fileno(), sys.stdin.fileno())

            # Redirect stdout and stderr
            if self.log_file:
                # Redirect to log file
                with open(self.log_file, "a") as log_out:
                    os.dup2(log_out.fileno(), sys.stdout.fileno())
                    os.dup2(log_out.fileno(), sys.stderr.fileno())
            else:
                # Redirect to /dev/null
                with open("/dev/null", "w") as null_out:
                    os.dup2(null_out.fileno(), sys.stdout.fileno())
                    os.dup2(null_out.fileno(), sys.stderr.fileno())

        except Exception as e:
            self.logger.error(f"Error redirecting streams: {e}")

    def write_pid_file(self):
        """Write PID to PID file."""
        try:
            # Ensure parent directory exists
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)

            # Write PID
            with open(self.pid_file, "w") as f:
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

            with open(self.pid_file) as f:
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
