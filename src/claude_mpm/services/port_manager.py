#!/usr/bin/env python3
"""
Port Manager for SocketIO Server

Handles dynamic port selection, instance detection, and port availability checking.
Ensures only one instance runs per port and provides fallback port selection.
"""

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil

from ..core.logging_config import get_logger


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
                result = sock.bind(("localhost", port))
                return True
        except OSError:
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
        self, preferred_port: Optional[int] = None
    ) -> Optional[int]:
        """Find an available port, preferring the specified port if given."""
        # Try preferred port first
        if preferred_port and preferred_port in self.PORT_RANGE:
            if self.is_port_available(preferred_port):
                is_ours, instance_info = self.is_claude_mpm_instance(preferred_port)
                if not is_ours:
                    return preferred_port
                else:
                    self.logger.warning(
                        f"Port {preferred_port} is already used by claude-mpm instance: {instance_info}"
                    )

        # Try default port
        if self.is_port_available(self.DEFAULT_PORT):
            is_ours, instance_info = self.is_claude_mpm_instance(self.DEFAULT_PORT)
            if not is_ours:
                return self.DEFAULT_PORT
            else:
                self.logger.info(
                    f"Default port {self.DEFAULT_PORT} is already used by claude-mpm instance"
                )

        # Try other ports in range
        for port in self.PORT_RANGE:
            if port == self.DEFAULT_PORT:
                continue  # Already tried

            if self.is_port_available(port):
                is_ours, instance_info = self.is_claude_mpm_instance(port)
                if not is_ours:
                    self.logger.info(f"Selected available port: {port}")
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
                with open(self.instances_file, "r") as f:
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
