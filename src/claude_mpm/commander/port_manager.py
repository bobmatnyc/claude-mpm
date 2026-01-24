"""Port manager for Commander daemon.

Handles port conflict detection, process identification, and PID file management
specifically for the Commander daemon service.
"""

import logging
import os
import signal
import socket
import subprocess  # nosec B404
import time
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, Optional

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

logger = logging.getLogger(__name__)

# ANSI colors for output
CYAN = "\033[36m"
DIM = "\033[2m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


class ProcessInfo(NamedTuple):
    """Information about a process using a port."""

    pid: int
    name: str
    cmdline: str
    is_commander: bool
    is_healthy: bool


@dataclass
class PortStatus:
    """Detailed status of a port."""

    port: int
    available: bool
    process: Optional[ProcessInfo] = None
    pid_file_pid: Optional[int] = None
    pid_file_exists: bool = False
    recommendation: str = ""


class CommanderPortManager:
    """Manages port allocation and conflict detection for Commander daemon.

    Provides commander-specific process identification and PID file management.
    Reuses patterns from the existing PortManager infrastructure.
    """

    # Commander-specific patterns for process identification
    COMMANDER_PATTERNS = [
        "commander",
        "daemon_main",
        "claude_mpm.commander",
        "mpm commander",
        "claude-mpm commander",
        "CommanderDaemon",
        "uvicorn",  # Commander uses uvicorn
    ]

    # Additional patterns to identify our processes
    OUR_PATTERNS = [
        "claude-mpm",
        "claude_mpm",
    ]

    def __init__(self, port: int = 8766, host: str = "127.0.0.1"):
        """Initialize the port manager.

        Args:
            port: Commander daemon port (default: 8766)
            host: Commander daemon host (default: 127.0.0.1)
        """
        self.port = port
        self.host = host

        # PID file location
        self.config_dir = Path.home() / ".claude-mpm" / "commander"
        self.pid_file = self.config_dir / f"commander-{port}.pid"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def is_port_available(self) -> bool:
        """Check if the port is available for binding.

        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.host, self.port))
                return True
        except OSError:
            return False

    def get_process_on_port(self) -> Optional[ProcessInfo]:
        """Get information about the process using the port.

        Returns:
            ProcessInfo with details about the process, or None if port is free
        """
        if psutil is None:
            logger.warning("psutil not available, limited process detection")
            return self._get_process_via_lsof()

        try:
            # Try lsof first (more reliable for port detection)
            process_info = self._get_process_via_lsof()
            if process_info:
                return process_info

            # Fallback to psutil
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port == self.port and conn.status == "LISTEN":
                    try:
                        process = psutil.Process(conn.pid)
                        cmdline = " ".join(process.cmdline())

                        is_commander = self._is_commander_process(cmdline)
                        is_healthy = False
                        if is_commander:
                            is_healthy = self._check_process_health(conn.pid)

                        return ProcessInfo(
                            pid=conn.pid,
                            name=process.name(),
                            cmdline=cmdline,
                            is_commander=is_commander,
                            is_healthy=is_healthy,
                        )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        return ProcessInfo(
                            pid=conn.pid or 0,
                            name="unknown",
                            cmdline="<permission denied>",
                            is_commander=False,
                            is_healthy=False,
                        )

        except psutil.AccessDenied:
            # No permission to check network connections
            if not self.is_port_available():
                return ProcessInfo(
                    pid=0,
                    name="unknown",
                    cmdline="<unable to determine>",
                    is_commander=False,
                    is_healthy=False,
                )
        except Exception as e:
            logger.debug(f"Error getting process on port {self.port}: {e}")

        return None

    def _get_process_via_lsof(self) -> Optional[ProcessInfo]:
        """Get process information using lsof command.

        Returns:
            ProcessInfo if a process is found, None otherwise
        """
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{self.port}", "-sTCP:LISTEN", "-t"],  # nosec B603 B607
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                pid = int(result.stdout.strip().split()[0])

                # Get process details
                name = "unknown"
                cmdline = "<unknown>"

                if psutil is not None:
                    try:
                        process = psutil.Process(pid)
                        name = process.name()
                        cmdline = " ".join(process.cmdline())
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                is_commander = self._is_commander_process(cmdline)
                is_healthy = False
                if is_commander:
                    is_healthy = self._check_process_health(pid)

                return ProcessInfo(
                    pid=pid,
                    name=name,
                    cmdline=cmdline,
                    is_commander=is_commander,
                    is_healthy=is_healthy,
                )

        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass

        return None

    def _is_commander_process(self, cmdline: str) -> bool:
        """Check if a process is a Commander daemon.

        Args:
            cmdline: Process command line

        Returns:
            True if this appears to be a Commander process
        """
        if not cmdline:
            return False

        cmdline_lower = cmdline.lower()

        # Check for commander-specific patterns
        for pattern in self.COMMANDER_PATTERNS:
            if pattern.lower() in cmdline_lower:
                # Additional check: must also have claude-mpm/claude_mpm somewhere
                for our_pattern in self.OUR_PATTERNS:
                    if our_pattern.lower() in cmdline_lower:
                        return True

        return False

    def _check_process_health(self, pid: int) -> bool:
        """Check if a Commander process is healthy.

        Args:
            pid: Process ID to check

        Returns:
            True if the process is healthy (responding to health checks)
        """
        try:
            import requests

            response = requests.get(
                f"http://{self.host}:{self.port}/api/health", timeout=2
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_pid_from_file(self) -> Optional[int]:
        """Read the PID from the PID file.

        Returns:
            PID if file exists and is valid, None otherwise
        """
        if not self.pid_file.exists():
            return None

        try:
            pid_str = self.pid_file.read_text().strip()
            return int(pid_str)
        except (ValueError, OSError) as e:
            logger.debug(f"Error reading PID file: {e}")
            return None

    def write_pid_file(self, pid: int) -> bool:
        """Write PID to the PID file.

        Args:
            pid: Process ID to write

        Returns:
            True if successful, False otherwise
        """
        try:
            self.pid_file.write_text(str(pid))
            logger.debug(f"Wrote PID {pid} to {self.pid_file}")
            return True
        except OSError as e:
            logger.error(f"Failed to write PID file: {e}")
            return False

    def cleanup_pid_file(self) -> bool:
        """Remove the PID file.

        Returns:
            True if successful or file doesn't exist, False on error
        """
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                logger.debug(f"Removed PID file {self.pid_file}")
            return True
        except OSError as e:
            logger.error(f"Failed to remove PID file: {e}")
            return False

    def is_pid_stale(self, pid: int) -> bool:
        """Check if a PID is stale (process no longer exists or is different).

        Args:
            pid: Process ID to check

        Returns:
            True if the PID is stale, False if it's valid
        """
        if psutil is None:
            # Without psutil, check if process exists via kill(0)
            try:
                os.kill(pid, 0)
                return False  # Process exists
            except OSError:
                return True  # Process doesn't exist

        try:
            process = psutil.Process(pid)
            if not process.is_running():
                return True

            # Check if it's actually our commander process
            cmdline = " ".join(process.cmdline())
            if not self._is_commander_process(cmdline):
                # PID was reused by a different process
                return True

            return False

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return True

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """Kill a process by PID.

        Args:
            pid: Process ID to kill
            force: If True, use SIGKILL; otherwise SIGTERM first

        Returns:
            True if process was killed or doesn't exist, False on error
        """
        try:
            # Check if process exists
            if psutil is not None:
                if not psutil.pid_exists(pid):
                    return True
            else:
                try:
                    os.kill(pid, 0)
                except OSError:
                    return True

            # Send SIGTERM first (graceful)
            logger.info(f"Sending SIGTERM to process {pid}")
            os.kill(pid, signal.SIGTERM)

            # Wait for graceful shutdown
            for _ in range(20):  # 2 seconds
                time.sleep(0.1)
                if psutil is not None:
                    if not psutil.pid_exists(pid):
                        return True
                else:
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        return True

            # Force kill if still running and force is True
            if force:
                logger.warning(f"Process {pid} didn't terminate, forcing kill")
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)

                if psutil is not None:
                    return not psutil.pid_exists(pid)
                try:
                    os.kill(pid, 0)
                    return False
                except OSError:
                    return True

            return False

        except ProcessLookupError:
            return True  # Process doesn't exist
        except PermissionError:
            logger.error(f"Permission denied killing process {pid}")
            return False
        except Exception as e:
            logger.error(f"Error killing process {pid}: {e}")
            return False

    def get_port_status(self) -> PortStatus:
        """Get comprehensive status of the port.

        Returns:
            PortStatus with full details about the port
        """
        available = self.is_port_available()
        process = None if available else self.get_process_on_port()
        pid_from_file = self.get_pid_from_file()
        pid_file_exists = self.pid_file.exists()

        recommendation = ""
        if available:
            recommendation = "Port is available, safe to start"
        elif process:
            if process.is_commander:
                if process.is_healthy:
                    recommendation = (
                        "Existing healthy Commander daemon found, consider reusing"
                    )
                else:
                    recommendation = (
                        "Stale Commander daemon detected, safe to clean up and restart"
                    )
            else:
                recommendation = (
                    f"Port in use by unknown process: {process.name} (PID: {process.pid}). "
                    "Use --port to specify a different port, or --force to reclaim"
                )

        return PortStatus(
            port=self.port,
            available=available,
            process=process,
            pid_file_pid=pid_from_file,
            pid_file_exists=pid_file_exists,
            recommendation=recommendation,
        )

    def handle_port_conflict(self, force: bool = False) -> tuple[bool, str]:
        """Handle port conflicts intelligently.

        Args:
            force: If True, kill any process on the port (with warning)

        Returns:
            Tuple of (can_proceed, message)
            - can_proceed: True if daemon can start, False otherwise
            - message: User-friendly message about what happened
        """
        status = self.get_port_status()

        # Port is available
        if status.available:
            # Clean up stale PID file if exists
            if status.pid_file_exists:
                pid = status.pid_file_pid
                if pid and self.is_pid_stale(pid):
                    self.cleanup_pid_file()
                    return (
                        True,
                        f"{GREEN}+{RESET} Port {self.port} available (cleaned up stale PID file)",
                    )
            return True, f"{GREEN}+{RESET} Port {self.port} available"

        # Port is in use
        process = status.process

        if process is None:
            # Can't determine what's using the port
            if force:
                return False, (
                    f"{RED}x{RESET} Port {self.port} in use by unknown process\n"
                    "  Cannot force kill without process information"
                )
            return False, (
                f"{RED}x{RESET} Port {self.port} in use by unknown process\n"
                "  Use --port to specify a different port"
            )

        # Check if it's our Commander process
        if process.is_commander:
            if process.is_healthy:
                return True, (
                    f"{YELLOW}!{RESET} Port {self.port} already in use by Commander (PID: {process.pid})\n"
                    f"{GREEN}+{RESET} Existing daemon is healthy, using it"
                )
            # Stale commander process - clean it up
            logger.info(f"Cleaning up stale Commander process (PID: {process.pid})")
            print(
                f"{YELLOW}!{RESET} Stale Commander detected on port {self.port} (PID: {process.pid})"
            )

            if self.kill_process(process.pid, force=True):
                self.cleanup_pid_file()
                # Wait a moment for port to be released
                time.sleep(0.5)
                if self.is_port_available():
                    return (
                        True,
                        f"{GREEN}+{RESET} Cleaned up stale process, starting fresh daemon",
                    )
                return False, f"{RED}x{RESET} Failed to release port after cleanup"
            return False, f"{RED}x{RESET} Failed to clean up stale Commander process"

        # Not our process
        if force:
            print(
                f"{YELLOW}WARNING:{RESET} Killing unknown process {process.name} (PID: {process.pid}) with --force"
            )
            if self.kill_process(process.pid, force=True):
                self.cleanup_pid_file()
                time.sleep(0.5)
                if self.is_port_available():
                    return (
                        True,
                        f"{GREEN}+{RESET} Force-killed process, port now available",
                    )
                return False, f"{RED}x{RESET} Failed to release port after force kill"
            return False, f"{RED}x{RESET} Failed to kill process {process.pid}"

        # Not our process and no --force flag
        return False, (
            f"{RED}x{RESET} Port {self.port} in use by unknown process: {process.name} (PID: {process.pid})\n"
            f"  Use --port to specify a different port, or --force to reclaim"
        )


def check_and_handle_port_conflict(
    port: int = 8766, host: str = "127.0.0.1", force: bool = False
) -> tuple[bool, str, Optional[int]]:
    """Convenience function to check and handle port conflicts.

    Args:
        port: Port to check
        host: Host to check
        force: If True, force kill any process on the port

    Returns:
        Tuple of (can_proceed, message, existing_pid_if_healthy)
        - can_proceed: True if daemon can start
        - message: User-friendly status message
        - existing_pid_if_healthy: PID of healthy existing daemon (to skip starting new one)
    """
    manager = CommanderPortManager(port=port, host=host)
    status = manager.get_port_status()

    # Check if there's a healthy daemon we should reuse
    if status.process and status.process.is_commander and status.process.is_healthy:
        return (
            True,
            (
                f"{YELLOW}!{RESET} Port {port} already in use by Commander (PID: {status.process.pid})\n"
                f"{GREEN}+{RESET} Existing daemon is healthy, using it"
            ),
            status.process.pid,
        )

    can_proceed, message = manager.handle_port_conflict(force=force)
    return can_proceed, message, None
