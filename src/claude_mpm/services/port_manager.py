#!/usr/bin/env python3
"""
Port Manager for SocketIO Server

Handles dynamic port selection, instance detection, and port availability checking.
Ensures only one instance runs per port and provides fallback port selection.
"""

import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

import psutil

from ..core.logging_config import get_logger


class ProcessInfo(NamedTuple):
    """Information about a process using a port."""

    pid: int
    name: str
    cmdline: str
    is_ours: bool
    is_debug: bool
    is_daemon: bool


class PortManager:
    """Manages port allocation and instance detection for SocketIO servers."""

    # Port range for SocketIO servers
    PORT_RANGE = range(8765, 8786)  # 8765-8785 (21 ports)
    DEFAULT_PORT = 8765

    def __init__(self, project_root: Optional[Path] = None):
        self.logger = get_logger(__name__ + ".PortManager")
        self.project_root = project_root or Path.cwd()
        self.state_dir = self.project_root / ".claude-mpm"
        self.state_dir.mkdir(exist_ok=True)
        self.instances_file = self.state_dir / "socketio-instances.json"

    def is_port_available(self, port: int) -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("localhost", port))
                return True
        except OSError:
            return False

    def get_process_on_port(self, port: int) -> Optional[ProcessInfo]:
        """Get information about the process using a specific port.

        WHY: We need to identify what process is using a port to make intelligent
        decisions about whether we can reclaim it (our debug scripts) or must
        avoid it (external processes or our daemons).

        Returns:
            ProcessInfo with details about the process, or None if port is free
        """
        try:
            # First try using lsof as it's more reliable for port detection
            try:
                result = subprocess.run(
                    ["lsof", "-i", f":{port}", "-sTCP:LISTEN", "-t"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    # Get the PID from lsof output
                    pid = int(result.stdout.strip().split()[0])
                    try:
                        process = psutil.Process(pid)
                        cmdline = " ".join(process.cmdline())

                        # Determine if this is our process and what type
                        is_ours = self._is_our_process(pid, cmdline)
                        is_debug = self._is_debug_process(cmdline) if is_ours else False
                        is_daemon = (
                            self._is_daemon_process(cmdline) if is_ours else False
                        )

                        return ProcessInfo(
                            pid=pid,
                            name=process.name(),
                            cmdline=cmdline,
                            is_ours=is_ours,
                            is_debug=is_debug,
                            is_daemon=is_daemon,
                        )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # Process exists but we can't access it
                        return ProcessInfo(
                            pid=pid,
                            name="unknown",
                            cmdline="<permission denied>",
                            is_ours=False,
                            is_debug=False,
                            is_daemon=False,
                        )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # lsof not available or timed out, fall back to psutil
                pass

            # Fallback to psutil method
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port == port and conn.status == "LISTEN":
                    try:
                        process = psutil.Process(conn.pid)
                        cmdline = " ".join(process.cmdline())

                        # Determine if this is our process and what type
                        is_ours = self._is_our_process(conn.pid, cmdline)
                        is_debug = self._is_debug_process(cmdline) if is_ours else False
                        is_daemon = (
                            self._is_daemon_process(cmdline) if is_ours else False
                        )

                        return ProcessInfo(
                            pid=conn.pid,
                            name=process.name(),
                            cmdline=cmdline,
                            is_ours=is_ours,
                            is_debug=is_debug,
                            is_daemon=is_daemon,
                        )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # Can't access process details, mark as unknown external
                        return ProcessInfo(
                            pid=conn.pid,
                            name="unknown",
                            cmdline="<permission denied>",
                            is_ours=False,
                            is_debug=False,
                            is_daemon=False,
                        )
        except psutil.AccessDenied:
            # No permission to check network connections
            # Try socket binding as last resort
            if not self.is_port_available(port):
                # Port is in use but we can't determine by what
                return ProcessInfo(
                    pid=0,
                    name="unknown",
                    cmdline="<unable to determine>",
                    is_ours=False,
                    is_debug=False,
                    is_daemon=False,
                )
        except Exception as e:
            self.logger.debug(f"Error getting process on port {port}: {e}")

        return None

    def _is_our_process(self, pid: int, cmdline: Optional[str] = None) -> bool:
        """Check if a process belongs to claude-mpm.

        WHY: We need to distinguish our processes from external ones to know
        which ports we can potentially reclaim.
        """
        try:
            if cmdline is None:
                process = psutil.Process(pid)
                cmdline = " ".join(process.cmdline())

            cmdline_lower = cmdline.lower()

            # Check for claude-mpm related patterns
            our_patterns = [
                "claude-mpm",
                "claude_mpm",
                "socketio_debug",
                "socketio_daemon",
                "socketio_server",
                str(self.project_root).lower(),  # Running from our project directory
                "scripts/test_",  # Our test scripts
                "scripts/debug_",  # Our debug scripts
                "scripts/demo_",  # Our demo scripts
                "scripts/run_",  # Our run scripts
                "scripts/validate_",  # Our validation scripts
            ]

            return any(pattern in cmdline_lower for pattern in our_patterns)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def _is_debug_process(self, cmdline: str) -> bool:
        """Check if a process is a debug/test script (safe to kill).

        WHY: Debug and test scripts can be safely terminated to reclaim ports,
        unlike production daemons which should be preserved.
        """
        cmdline_lower = cmdline.lower()

        debug_patterns = [
            "socketio_debug.py",
            "run_socketio_debug.py",
            "test_",
            "debug_",
            "demo_",
            "validate_",
            "scripts/test",
            "scripts/debug",
            "scripts/demo",
            "scripts/validate",
        ]

        # Also check if NOT a daemon (daemons are not debug scripts)
        is_not_daemon = "daemon" not in cmdline_lower or "debug" in cmdline_lower

        return (
            any(pattern in cmdline_lower for pattern in debug_patterns)
            and is_not_daemon
        )

    def _is_daemon_process(self, cmdline: str) -> bool:
        """Check if a process is a daemon (should be preserved).

        WHY: Daemon processes are production services that should not be
        automatically killed. Users must explicitly stop them.
        """
        cmdline_lower = cmdline.lower()

        daemon_patterns = [
            "socketio_daemon",
            "claude-mpm monitor",
            "daemon",
        ]

        # Exclude debug daemons
        if "debug" in cmdline_lower:
            return False

        return any(pattern in cmdline_lower for pattern in daemon_patterns)

    def kill_process_on_port(self, port: int, force: bool = False) -> bool:
        """Kill a process using a specific port if it's safe to do so.

        WHY: Automatically reclaim ports from our debug scripts while preserving
        daemons and avoiding external processes.

        Args:
            port: Port number to reclaim
            force: If True, kill even daemon processes (requires explicit user action)

        Returns:
            True if process was killed or port is now free, False otherwise
        """
        process_info = self.get_process_on_port(port)

        if not process_info:
            self.logger.info(f"Port {port} is already free")
            return True

        if not process_info.is_ours:
            self.logger.warning(
                f"Port {port} is used by external process '{process_info.name}' "
                f"(PID: {process_info.pid}). Cannot reclaim."
            )
            return False

        if process_info.is_daemon and not force:
            self.logger.warning(
                f"Port {port} is used by our daemon process (PID: {process_info.pid}). "
                f"Use --force flag or stop the daemon explicitly."
            )
            return False

        if process_info.is_debug or force:
            try:
                self.logger.info(
                    f"Killing {'debug' if process_info.is_debug else 'daemon'} process "
                    f"{process_info.pid} on port {port}"
                )

                # Try graceful termination first
                os.kill(process_info.pid, signal.SIGTERM)

                # Wait up to 2 seconds for graceful shutdown
                for _ in range(20):
                    time.sleep(0.1)
                    if not psutil.pid_exists(process_info.pid):
                        self.logger.info(
                            f"Process {process_info.pid} terminated gracefully"
                        )
                        return True

                # Force kill if still running
                self.logger.warning(
                    f"Process {process_info.pid} didn't terminate, forcing kill"
                )
                os.kill(process_info.pid, signal.SIGKILL)
                time.sleep(0.5)

                if not psutil.pid_exists(process_info.pid):
                    self.logger.info(f"Process {process_info.pid} force killed")
                    return True
                self.logger.error(f"Failed to kill process {process_info.pid}")
                return False

            except Exception as e:
                self.logger.error(f"Error killing process {process_info.pid}: {e}")
                return False

        return False

    def is_claude_mpm_instance(self, port: int) -> Tuple[bool, Optional[Dict]]:
        """Check if a port is being used by a claude-mpm SocketIO instance."""
        instances = self.load_instances()

        for instance_id, instance_info in instances.items():
            if instance_info.get("port") == port:
                # Check if the process is still running
                pid = instance_info.get("pid")
                if pid and self.is_process_running(pid):
                    # Verify it's actually our process
                    if self.is_our_socketio_process(pid):
                        return True, instance_info
                else:
                    # Process is dead, clean up the instance
                    self.remove_instance(instance_id)

        return False, None

    def is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running."""
        try:
            return psutil.pid_exists(pid)
        except Exception:
            return False

    def is_our_socketio_process(self, pid: int) -> bool:
        """Verify that a PID belongs to our SocketIO server."""
        try:
            process = psutil.Process(pid)
            cmdline = " ".join(process.cmdline())

            # Check if it's a Python process running our SocketIO daemon
            return "python" in cmdline.lower() and (
                "socketio_daemon" in cmdline or "claude-mpm" in cmdline
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def find_available_port(
        self, preferred_port: Optional[int] = None, reclaim: bool = True
    ) -> Optional[int]:
        """Find an available port, preferring the specified port if given.

        WHY: Enhanced to intelligently reclaim ports from our debug processes
        while avoiding external processes and preserving daemons.

        Args:
            preferred_port: Port to try first
            reclaim: If True, try to reclaim ports from our debug scripts

        Returns:
            Available port number or None if no ports available
        """
        # Try preferred port first
        if preferred_port and preferred_port in self.PORT_RANGE:
            if self.is_port_available(preferred_port):
                return preferred_port

            # Port is in use - check if we can reclaim it
            if reclaim:
                process_info = self.get_process_on_port(preferred_port)
                if process_info and process_info.is_ours and process_info.is_debug:
                    self.logger.info(
                        f"Port {preferred_port} used by our debug process, attempting to reclaim"
                    )
                    if self.kill_process_on_port(preferred_port):
                        time.sleep(0.5)  # Brief pause for port to be released
                        if self.is_port_available(preferred_port):
                            return preferred_port
                elif process_info:
                    if process_info.is_daemon:
                        self.logger.warning(
                            f"Port {preferred_port} used by our daemon (PID: {process_info.pid})"
                        )
                    elif not process_info.is_ours:
                        self.logger.warning(
                            f"Port {preferred_port} used by external process '{process_info.name}'"
                        )

        # Try default port
        if self.is_port_available(self.DEFAULT_PORT):
            return self.DEFAULT_PORT

        # Check if we can reclaim default port
        if reclaim:
            process_info = self.get_process_on_port(self.DEFAULT_PORT)
            if process_info and process_info.is_ours and process_info.is_debug:
                self.logger.info(
                    f"Default port {self.DEFAULT_PORT} used by our debug process, attempting to reclaim"
                )
                if self.kill_process_on_port(self.DEFAULT_PORT):
                    time.sleep(0.5)
                    if self.is_port_available(self.DEFAULT_PORT):
                        return self.DEFAULT_PORT

        # Try other ports in range
        for port in self.PORT_RANGE:
            if port == self.DEFAULT_PORT:
                continue  # Already tried

            if self.is_port_available(port):
                return port

            # Try to reclaim if it's our debug process
            if reclaim:
                process_info = self.get_process_on_port(port)
                if process_info and process_info.is_ours and process_info.is_debug:
                    self.logger.info(
                        f"Port {port} used by our debug process, attempting to reclaim"
                    )
                    if self.kill_process_on_port(port):
                        time.sleep(0.5)
                        if self.is_port_available(port):
                            self.logger.info(f"Reclaimed port {port}")
                            return port

        self.logger.error(
            f"No available ports in range {self.PORT_RANGE.start}-{self.PORT_RANGE.stop-1}"
        )
        return None

    def register_instance(self, port: int, pid: int, host: str = "localhost") -> str:
        """Register a new SocketIO server instance."""
        instances = self.load_instances()

        instance_id = f"socketio-{port}-{int(time.time())}"
        instance_info = {
            "port": port,
            "pid": pid,
            "host": host,
            "start_time": time.time(),
            "project_root": str(self.project_root),
        }

        instances[instance_id] = instance_info
        self.save_instances(instances)

        self.logger.info(
            f"Registered SocketIO instance {instance_id} on port {port} (PID: {pid})"
        )
        return instance_id

    def remove_instance(self, instance_id: str) -> bool:
        """Remove a SocketIO server instance registration."""
        instances = self.load_instances()

        if instance_id in instances:
            instance_info = instances.pop(instance_id)
            self.save_instances(instances)
            self.logger.info(
                f"Removed SocketIO instance {instance_id} (port: {instance_info.get('port')})"
            )
            return True

        return False

    def load_instances(self) -> Dict:
        """Load registered instances from file."""
        try:
            if self.instances_file.exists():
                with open(self.instances_file) as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load instances file: {e}")

        return {}

    def save_instances(self, instances: Dict) -> None:
        """Save registered instances to file."""
        try:
            with open(self.instances_file, "w") as f:
                json.dump(instances, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save instances file: {e}")

    def cleanup_dead_instances(self) -> int:
        """Clean up instances for processes that are no longer running."""
        instances = self.load_instances()
        dead_instances = []

        for instance_id, instance_info in instances.items():
            pid = instance_info.get("pid")
            if pid and not self.is_process_running(pid):
                dead_instances.append(instance_id)

        for instance_id in dead_instances:
            self.remove_instance(instance_id)

        if dead_instances:
            self.logger.info(f"Cleaned up {len(dead_instances)} dead instances")

        return len(dead_instances)

    def list_active_instances(self) -> List[Dict]:
        """List all active SocketIO instances."""
        instances = self.load_instances()
        active_instances = []

        for instance_id, instance_info in instances.items():
            pid = instance_info.get("pid")
            if pid and self.is_process_running(pid):
                instance_info["instance_id"] = instance_id
                instance_info["running"] = True
                active_instances.append(instance_info)

        return active_instances

    def get_instance_by_port(self, port: int) -> Optional[Dict]:
        """Get instance information for a specific port."""
        instances = self.load_instances()

        for instance_id, instance_info in instances.items():
            if instance_info.get("port") == port:
                pid = instance_info.get("pid")
                if pid and self.is_process_running(pid):
                    instance_info["instance_id"] = instance_id
                    instance_info["running"] = True
                    return instance_info

        return None

    def get_port_status(self, port: int) -> Dict[str, any]:
        """Get detailed status of a port including what's using it.

        WHY: Provides comprehensive information for users to understand
        port conflicts and make informed decisions.

        Returns:
            Dictionary with port status details
        """
        status = {
            "port": port,
            "available": self.is_port_available(port),
            "process": None,
            "instance": None,
            "recommendation": None,
        }

        # Check for process using the port
        process_info = self.get_process_on_port(port)
        if process_info:
            status["process"] = {
                "pid": process_info.pid,
                "name": process_info.name,
                "is_ours": process_info.is_ours,
                "is_debug": process_info.is_debug,
                "is_daemon": process_info.is_daemon,
                "cmdline": (
                    process_info.cmdline[:100] + "..."
                    if len(process_info.cmdline) > 100
                    else process_info.cmdline
                ),
            }

            # Provide recommendation based on process type
            if process_info.is_ours:
                if process_info.is_debug:
                    status["recommendation"] = (
                        "Can be automatically reclaimed (debug process)"
                    )
                elif process_info.is_daemon:
                    status["recommendation"] = (
                        "Stop daemon with 'claude-mpm monitor stop' or use --force"
                    )
                else:
                    status["recommendation"] = (
                        "Our process, consider stopping it manually"
                    )
            else:
                status["recommendation"] = "External process, choose a different port"

        # Check for registered instance
        instance_info = self.get_instance_by_port(port)
        if instance_info:
            status["instance"] = {
                "id": instance_info.get("instance_id"),
                "pid": instance_info.get("pid"),
                "start_time": instance_info.get("start_time"),
            }

        return status
