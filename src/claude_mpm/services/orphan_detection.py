#!/usr/bin/env python3
"""
Orphan Detection Service
========================

Detects and manages orphaned deployment processes across different deployment methods.
Provides safe cleanup capabilities with multiple safety checks to prevent accidental
termination of active services.

Part of local-ops agent improvements for process lifecycle management.

WHY: Deployments can leave orphaned processes when:
- PM2 processes outlive their parent
- Docker containers keep running after deployment fails
- State files reference dead processes
- Projects are deleted but processes remain

SAFETY PHILOSOPHY:
- Never kill processes without verification
- Require manual confirmation for high-severity cases
- Preserve Claude MPM/MCP services at all costs
- Respect process ownership boundaries
- Implement multiple safety checks before any action

DESIGN DECISIONS:
- Multi-method support: PM2, Docker, native processes
- Severity levels: low, medium, high (affects confirmation requirements)
- Age-based protection: Never touch processes < 1 minute old
- Protected port ranges: Claude Code services (8765-8785)
- Ownership verification: Cross-reference with state files
"""

import json
import subprocess
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import psutil

from .core.base import SyncBaseService
from .port_manager import PortManager


class OrphanSeverity(Enum):
    """Severity levels for orphaned processes."""

    LOW = "low"  # Safe to auto-cleanup (e.g., old test processes)
    MEDIUM = "medium"  # Needs user awareness (e.g., untracked deployments)
    HIGH = "high"  # Requires explicit confirmation (e.g., running production services)


class OrphanType(Enum):
    """Types of orphaned resources."""

    DEAD_PID = "dead_pid"  # State file references dead process
    DELETED_PROJECT = "deleted_project"  # Process for non-existent project
    UNTRACKED_PROCESS = "untracked_process"  # Process on managed port without state
    PM2_ORPHAN = "pm2_orphan"  # PM2 process not in any state file
    DOCKER_ORPHAN = "docker_orphan"  # Docker container not in any state file
    STALE_DEPLOYMENT = "stale_deployment"  # Deployment hasn't been updated in days


class OrphanInfo:
    """Information about an orphaned resource."""

    def __init__(
        self,
        orphan_type: OrphanType,
        severity: OrphanSeverity,
        description: str,
        details: Dict[str, Any],
        cleanup_action: Optional[str] = None,
    ):
        """
        Initialize orphan info.

        Args:
            orphan_type: Type of orphan
            severity: Severity level
            description: Human-readable description
            details: Additional details (PID, port, etc.)
            cleanup_action: Suggested cleanup action
        """
        self.orphan_type = orphan_type
        self.severity = severity
        self.description = description
        self.details = details
        self.cleanup_action = cleanup_action
        self.detected_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.orphan_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "details": self.details,
            "cleanup_action": self.cleanup_action,
            "detected_at": self.detected_at.isoformat(),
        }


class OrphanDetectionService(SyncBaseService):
    """
    Service for detecting and managing orphaned deployment processes.

    Capabilities:
    - Scan for orphaned PM2 processes
    - Scan for orphaned Docker containers
    - Detect untracked processes on managed ports
    - Verify state file integrity
    - Safe cleanup with multiple safety checks
    """

    # Minimum process age before considering for cleanup (safety measure)
    MIN_PROCESS_AGE_SECONDS = 60  # 1 minute

    # Protected port ranges (Claude Code services)
    PROTECTED_PORT_RANGES = [(8765, 8785)]

    # Protected process patterns
    PROTECTED_PATTERNS = [
        "claude-mpm",
        "claude_mpm",
        "socketio_daemon",
        "mcp-",
        "monitor",
    ]

    # Port range for user projects
    USER_PORT_RANGE_START = 3000
    USER_PORT_RANGE_END = 9999

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the orphan detection service.

        Args:
            project_root: Project directory (default: current working directory)
        """
        super().__init__(service_name="OrphanDetectionService")

        self.project_root = (project_root or Path.cwd()).resolve()
        self.state_dir = self.project_root / ".claude-mpm"
        self.state_file = self.state_dir / "deployment-state.json"

        # Global registry
        self.global_registry_dir = Path.home() / ".claude-mpm"
        self.global_registry_file = (
            self.global_registry_dir / "global-port-registry.json"
        )

        # Port manager for process checks
        self.port_manager = PortManager(project_root=self.project_root)

    def initialize(self) -> bool:
        """
        Initialize the service.

        Returns:
            True if initialization successful
        """
        try:
            self._initialized = True
            self.log_info("OrphanDetectionService initialized successfully")
            return True
        except Exception as e:
            self.log_error(f"Failed to initialize: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        self._shutdown = True
        self.log_info("OrphanDetectionService shutdown")

    def _is_protected_process(self, cmdline: str) -> bool:
        """
        Check if process is protected (Claude MPM services).

        Args:
            cmdline: Process command line

        Returns:
            True if process is protected
        """
        cmdline_lower = cmdline.lower()
        return any(pattern in cmdline_lower for pattern in self.PROTECTED_PATTERNS)

    def _is_protected_port(self, port: int) -> bool:
        """
        Check if port is in protected range.

        Args:
            port: Port number

        Returns:
            True if port is protected
        """
        return any(start <= port <= end for start, end in self.PROTECTED_PORT_RANGES)

    def _get_process_age(self, pid: int) -> Optional[float]:
        """
        Get process age in seconds.

        Args:
            pid: Process ID

        Returns:
            Age in seconds or None if process not found
        """
        try:
            process = psutil.Process(pid)
            create_time = process.create_time()
            return time.time() - create_time
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def _is_process_safe_to_kill(self, pid: int, cmdline: str) -> Tuple[bool, str]:
        """
        Check if a process is safe to kill.

        Args:
            pid: Process ID
            cmdline: Process command line

        Returns:
            Tuple of (is_safe, reason)
        """
        # Check if protected
        if self._is_protected_process(cmdline):
            return False, "Protected Claude MPM/MCP service"

        # Check process age
        age = self._get_process_age(pid)
        if age is None:
            return False, "Cannot determine process age"

        if age < self.MIN_PROCESS_AGE_SECONDS:
            return (
                False,
                f"Process too young ({age:.1f}s < {self.MIN_PROCESS_AGE_SECONDS}s)",
            )

        return True, "Safe to cleanup"

    def scan_dead_pids(self) -> List[OrphanInfo]:
        """
        Scan for dead PIDs in state files.

        Returns:
            List of orphaned state entries
        """
        orphans = []

        try:
            if not self.state_file.exists():
                return orphans

            with self.state_file.open() as f:
                state = json.load(f)

            deployments = state.get("deployments", {})

            for service_name, deployment in deployments.items():
                pid = deployment.get("pid")

                if not pid:
                    continue

                # Check if process exists
                if not psutil.pid_exists(pid):
                    orphans.append(
                        OrphanInfo(
                            orphan_type=OrphanType.DEAD_PID,
                            severity=OrphanSeverity.LOW,
                            description=f"State file references dead process (PID: {pid})",
                            details={
                                "service_name": service_name,
                                "pid": pid,
                                "port": deployment.get("port"),
                                "state_file": str(self.state_file),
                            },
                            cleanup_action="Remove from state file",
                        )
                    )

        except Exception as e:
            self.log_error(f"Error scanning dead PIDs: {e}")

        return orphans

    def scan_deleted_projects(self) -> List[OrphanInfo]:
        """
        Scan global registry for projects that no longer exist.

        Returns:
            List of orphaned project entries
        """
        orphans = []

        try:
            if not self.global_registry_file.exists():
                return orphans

            with self.global_registry_file.open() as f:
                registry = json.load(f)

            allocations = registry.get("allocations", {})

            for port_str, allocation in allocations.items():
                project_path = Path(allocation.get("project_path", ""))

                # Check if project directory exists
                if not project_path.exists():
                    orphans.append(
                        OrphanInfo(
                            orphan_type=OrphanType.DELETED_PROJECT,
                            severity=OrphanSeverity.MEDIUM,
                            description="Port allocated to deleted project",
                            details={
                                "port": int(port_str),
                                "project_path": str(project_path),
                                "service_name": allocation.get("service_name"),
                            },
                            cleanup_action="Remove from global registry",
                        )
                    )

        except Exception as e:
            self.log_error(f"Error scanning deleted projects: {e}")

        return orphans

    def scan_untracked_processes(self) -> List[OrphanInfo]:
        """
        Scan for processes on managed ports without state tracking.

        Returns:
            List of untracked processes
        """
        orphans = []

        try:
            # Load global registry to know which ports are managed
            managed_ports = set()
            if self.global_registry_file.exists():
                with self.global_registry_file.open() as f:
                    registry = json.load(f)
                    managed_ports = {int(p) for p in registry.get("allocations", {})}

            # Scan all network connections
            for conn in psutil.net_connections(kind="inet"):
                if conn.status != "LISTEN":
                    continue

                port = conn.laddr.port

                # Skip if not in user port range
                if not (self.USER_PORT_RANGE_START <= port <= self.USER_PORT_RANGE_END):
                    continue

                # Skip protected ports
                if self._is_protected_port(port):
                    continue

                # Check if port is tracked in global registry
                if port not in managed_ports:
                    try:
                        process = psutil.Process(conn.pid)
                        cmdline = " ".join(process.cmdline())

                        # Skip protected processes
                        if self._is_protected_process(cmdline):
                            continue

                        orphans.append(
                            OrphanInfo(
                                orphan_type=OrphanType.UNTRACKED_PROCESS,
                                severity=OrphanSeverity.MEDIUM,
                                description=f"Process on port {port} not tracked in state files",
                                details={
                                    "pid": conn.pid,
                                    "port": port,
                                    "process_name": process.name(),
                                    "cmdline": cmdline[:100],
                                },
                                cleanup_action="Investigate and add to state or cleanup",
                            )
                        )

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

        except Exception as e:
            self.log_error(f"Error scanning untracked processes: {e}")

        return orphans

    def scan_pm2_orphans(self) -> List[OrphanInfo]:
        """
        Scan for orphaned PM2 processes.

        Returns:
            List of orphaned PM2 processes
        """
        orphans = []

        try:
            # Get all PM2 processes
            result = subprocess.run(
                ["pm2", "jlist"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode != 0:
                self.log_debug("PM2 not available or no processes")
                return orphans

            pm2_processes = json.loads(result.stdout)

            # Load all state files to find tracked PM2 processes
            tracked_pm2_names = self._get_tracked_pm2_processes()

            for proc in pm2_processes:
                name = proc.get("name")
                pid = proc.get("pid")

                # Skip if tracked in any state file
                if name in tracked_pm2_names:
                    continue

                # Skip protected processes
                script = proc.get("pm2_env", {}).get("pm_exec_path", "")
                if self._is_protected_process(script):
                    continue

                orphans.append(
                    OrphanInfo(
                        orphan_type=OrphanType.PM2_ORPHAN,
                        severity=OrphanSeverity.HIGH,  # High severity - running service
                        description=f"PM2 process '{name}' not tracked in any state file",
                        details={
                            "pm2_name": name,
                            "pid": pid,
                            "status": proc.get("pm2_env", {}).get("status"),
                            "restart_count": proc.get("pm2_env", {}).get(
                                "restart_time", 0
                            ),
                        },
                        cleanup_action="pm2 delete {name}",
                    )
                )

        except subprocess.TimeoutExpired:
            self.log_warning("PM2 command timed out")
        except json.JSONDecodeError:
            self.log_warning("Failed to parse PM2 output")
        except Exception as e:
            self.log_error(f"Error scanning PM2 orphans: {e}")

        return orphans

    def scan_docker_orphans(self) -> List[OrphanInfo]:
        """
        Scan for orphaned Docker containers.

        Returns:
            List of orphaned Docker containers
        """
        orphans = []

        try:
            # Get all running Docker containers
            result = subprocess.run(
                ["docker", "ps", "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode != 0:
                self.log_debug("Docker not available or no containers")
                return orphans

            # Load tracked Docker containers
            tracked_containers = self._get_tracked_docker_containers()

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                try:
                    container = json.loads(line)
                    container_id = container.get("ID")
                    container_name = container.get("Names")

                    # Skip if tracked
                    if (
                        container_id in tracked_containers
                        or container_name in tracked_containers
                    ):
                        continue

                    # Skip protected containers
                    if any(
                        pattern in container_name.lower()
                        for pattern in self.PROTECTED_PATTERNS
                    ):
                        continue

                    orphans.append(
                        OrphanInfo(
                            orphan_type=OrphanType.DOCKER_ORPHAN,
                            severity=OrphanSeverity.HIGH,
                            description=f"Docker container '{container_name}' not tracked in any state file",
                            details={
                                "container_id": container_id,
                                "container_name": container_name,
                                "image": container.get("Image"),
                                "status": container.get("Status"),
                            },
                            cleanup_action=f"docker stop {container_id}",
                        )
                    )

                except json.JSONDecodeError:
                    continue

        except subprocess.TimeoutExpired:
            self.log_warning("Docker command timed out")
        except Exception as e:
            self.log_error(f"Error scanning Docker orphans: {e}")

        return orphans

    def _get_tracked_pm2_processes(self) -> Set[str]:
        """
        Get set of PM2 process names tracked in state files.

        Returns:
            Set of PM2 process names
        """
        tracked = set()

        # Check project state
        if self.state_file.exists():
            try:
                with self.state_file.open() as f:
                    state = json.load(f)

                for deployment in state.get("deployments", {}).values():
                    if deployment.get("method") == "pm2":
                        process_name = deployment.get("process_name")
                        if process_name:
                            tracked.add(process_name)

            except Exception as e:
                self.log_warning(f"Error reading state file: {e}")

        # TODO: Could also scan other projects' state files for comprehensive check

        return tracked

    def _get_tracked_docker_containers(self) -> Set[str]:
        """
        Get set of Docker containers tracked in state files.

        Returns:
            Set of container IDs and names
        """
        tracked = set()

        # Check project state
        if self.state_file.exists():
            try:
                with self.state_file.open() as f:
                    state = json.load(f)

                for deployment in state.get("deployments", {}).values():
                    if deployment.get("method") == "docker":
                        container_id = deployment.get("container_id")
                        container_name = deployment.get("container_name")

                        if container_id:
                            tracked.add(container_id)
                        if container_name:
                            tracked.add(container_name)

            except Exception as e:
                self.log_warning(f"Error reading state file: {e}")

        return tracked

    def scan_all_orphans(self) -> Dict[str, List[OrphanInfo]]:
        """
        Perform comprehensive orphan scan.

        Returns:
            Dictionary mapping orphan types to lists of orphans
        """
        results = {
            "dead_pids": self.scan_dead_pids(),
            "deleted_projects": self.scan_deleted_projects(),
            "untracked_processes": self.scan_untracked_processes(),
            "pm2_orphans": self.scan_pm2_orphans(),
            "docker_orphans": self.scan_docker_orphans(),
        }

        total = sum(len(orphans) for orphans in results.values())
        self.log_info(f"Orphan scan complete: found {total} potential orphans")

        return results

    def cleanup_orphan(
        self,
        orphan: OrphanInfo,
        force: bool = False,
    ) -> Tuple[bool, str]:
        """
        Clean up a specific orphan.

        Args:
            orphan: Orphan info
            force: Skip safety checks (use with extreme caution)

        Returns:
            Tuple of (success, message)
        """
        # High severity orphans require explicit confirmation
        if orphan.severity == OrphanSeverity.HIGH and not force:
            return False, "High severity orphan requires explicit force=True"

        try:
            if orphan.orphan_type == OrphanType.DEAD_PID:
                return self._cleanup_dead_pid(orphan)

            if orphan.orphan_type == OrphanType.DELETED_PROJECT:
                return self._cleanup_deleted_project(orphan)

            if orphan.orphan_type == OrphanType.UNTRACKED_PROCESS:
                return self._cleanup_untracked_process(orphan, force)

            if orphan.orphan_type == OrphanType.PM2_ORPHAN:
                return self._cleanup_pm2_orphan(orphan, force)

            if orphan.orphan_type == OrphanType.DOCKER_ORPHAN:
                return self._cleanup_docker_orphan(orphan, force)

            return False, f"Unknown orphan type: {orphan.orphan_type}"

        except Exception as e:
            self.log_error(f"Error cleaning up orphan: {e}")
            return False, str(e)

    def _cleanup_dead_pid(self, orphan: OrphanInfo) -> Tuple[bool, str]:
        """Clean up dead PID entry from state file."""
        try:
            with self.state_file.open() as f:
                state = json.load(f)

            service_name = orphan.details.get("service_name")
            if service_name in state.get("deployments", {}):
                del state["deployments"][service_name]

                with self.state_file.open("w") as f:
                    json.dump(state, f, indent=2)

                return True, f"Removed dead PID entry for {service_name}"

            return False, "Entry not found in state file"

        except Exception as e:
            return False, f"Failed to cleanup: {e}"

    def _cleanup_deleted_project(self, orphan: OrphanInfo) -> Tuple[bool, str]:
        """Clean up deleted project entry from global registry."""
        try:
            with self.global_registry_file.open() as f:
                registry = json.load(f)

            port = str(orphan.details.get("port"))
            if port in registry.get("allocations", {}):
                del registry["allocations"][port]

                with self.global_registry_file.open("w") as f:
                    json.dump(registry, f, indent=2)

                return True, f"Removed deleted project entry for port {port}"

            return False, "Entry not found in global registry"

        except Exception as e:
            return False, f"Failed to cleanup: {e}"

    def _cleanup_untracked_process(
        self,
        orphan: OrphanInfo,
        force: bool,
    ) -> Tuple[bool, str]:
        """Clean up untracked process."""
        pid = orphan.details.get("pid")
        cmdline = orphan.details.get("cmdline", "")

        # Safety check
        is_safe, reason = self._is_process_safe_to_kill(pid, cmdline)
        if not is_safe and not force:
            return False, f"Safety check failed: {reason}"

        try:
            process = psutil.Process(pid)
            process.terminate()

            # Wait for graceful termination
            process.wait(timeout=5)

            return True, f"Terminated untracked process {pid}"

        except psutil.TimeoutExpired:
            if force:
                process.kill()
                return True, f"Force killed untracked process {pid}"
            return False, "Process did not terminate gracefully"

        except Exception as e:
            return False, f"Failed to terminate process: {e}"

    def _cleanup_pm2_orphan(
        self,
        orphan: OrphanInfo,
        force: bool,
    ) -> Tuple[bool, str]:
        """Clean up orphaned PM2 process."""
        if not force:
            return False, "PM2 cleanup requires force=True"

        pm2_name = orphan.details.get("pm2_name")

        try:
            result = subprocess.run(
                ["pm2", "delete", pm2_name],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0:
                return True, f"Deleted PM2 process '{pm2_name}'"
            return False, f"PM2 delete failed: {result.stderr}"

        except Exception as e:
            return False, f"Failed to delete PM2 process: {e}"

    def _cleanup_docker_orphan(
        self,
        orphan: OrphanInfo,
        force: bool,
    ) -> Tuple[bool, str]:
        """Clean up orphaned Docker container."""
        if not force:
            return False, "Docker cleanup requires force=True"

        container_id = orphan.details.get("container_id")

        try:
            result = subprocess.run(
                ["docker", "stop", container_id],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                return True, f"Stopped Docker container {container_id}"
            return False, f"Docker stop failed: {result.stderr}"

        except Exception as e:
            return False, f"Failed to stop Docker container: {e}"
