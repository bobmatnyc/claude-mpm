#!/usr/bin/env python3
"""
Project Port Allocator Service
==============================

Provides deterministic, hash-based port allocation for local development projects.
Ensures each project gets a consistent port across sessions while avoiding conflicts.

Part of local-ops agent improvements for single port per project allocation.

WHY: Manual port assignment is error-prone and leads to conflicts. Hash-based
allocation provides predictable, consistent port assignments while avoiding
collisions through linear probing.

DESIGN DECISIONS:
- Hash-based allocation: Projects get same port consistently (SHA-256 of path)
- Port range: 3000-3999 (1000 ports for user projects)
- Linear probing: Handles hash collisions gracefully
- Global registry: Prevents conflicts across multiple projects
- Persistent state: Survives restarts and maintains history
- Atomic operations: Prevents race conditions in port allocation
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import psutil

from .core.base import SyncBaseService


class ProjectPortAllocator(SyncBaseService):
    """
    Manages port allocation for local development projects.

    Features:
    - Deterministic port allocation based on project path hash
    - Persistent state tracking across sessions
    - Global registry to prevent cross-project conflicts
    - Orphan detection and cleanup
    - Linear probing for conflict resolution
    """

    # Port range for user projects (avoiding system ports and Claude MPM services)
    DEFAULT_PORT_RANGE_START = 3000
    DEFAULT_PORT_RANGE_END = 3999

    # Claude MPM services use 8765-8785, keep these protected
    PROTECTED_PORT_RANGES = [(8765, 8785)]

    # State file names
    STATE_FILE_NAME = "deployment-state.json"
    GLOBAL_REGISTRY_FILE = "global-port-registry.json"

    def __init__(
        self,
        project_root: Optional[Path] = None,
        port_range_start: Optional[int] = None,
        port_range_end: Optional[int] = None,
    ):
        """
        Initialize the port allocator.

        Args:
            project_root: Project directory (default: current working directory)
            port_range_start: Start of port range (default: 3000)
            port_range_end: End of port range (default: 3999)
        """
        super().__init__(service_name="ProjectPortAllocator")

        self.project_root = (project_root or Path.cwd()).resolve()
        self.port_range_start = port_range_start or self.DEFAULT_PORT_RANGE_START
        self.port_range_end = port_range_end or self.DEFAULT_PORT_RANGE_END

        # Project-local state directory
        self.state_dir = self.project_root / ".claude-mpm"
        self.state_file = self.state_dir / self.STATE_FILE_NAME

        # Global registry in user home directory
        self.global_registry_dir = Path.home() / ".claude-mpm"
        self.global_registry_file = self.global_registry_dir / self.GLOBAL_REGISTRY_FILE

        # Ensure directories exist
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.global_registry_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> bool:
        """
        Initialize the service.

        Returns:
            True if initialization successful
        """
        try:
            # Cleanup any dead registrations on startup
            self.cleanup_dead_registrations()
            self._initialized = True
            self.log_info("ProjectPortAllocator initialized successfully")
            return True
        except Exception as e:
            self.log_error(f"Failed to initialize: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        self._shutdown = True
        self.log_info("ProjectPortAllocator shutdown")

    def _compute_project_hash(self, project_path: Path) -> str:
        """
        Compute deterministic hash for a project path.

        Args:
            project_path: Absolute path to project

        Returns:
            SHA-256 hash of the project path
        """
        # Use absolute path for consistency
        absolute_path = project_path.resolve()
        path_str = str(absolute_path)

        # Compute SHA-256 hash
        hash_obj = hashlib.sha256(path_str.encode("utf-8"))
        return hash_obj.hexdigest()

    def _hash_to_port(self, project_hash: str) -> int:
        """
        Convert project hash to a port number in the allowed range.

        Args:
            project_hash: SHA-256 hash of project path

        Returns:
            Port number in the configured range
        """
        # Use first 8 hex chars as integer
        hash_int = int(project_hash[:8], 16)

        # Map to port range
        port_range = self.port_range_end - self.port_range_start + 1
        return self.port_range_start + (hash_int % port_range)

    def _is_port_available(self, port: int) -> bool:
        """
        Check if a port is available for binding.

        Args:
            port: Port number to check

        Returns:
            True if port is available
        """
        try:
            import socket

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("localhost", port))
                return True
        except OSError:
            return False

    def _is_protected_port(self, port: int) -> bool:
        """
        Check if port is in a protected range.

        Args:
            port: Port number to check

        Returns:
            True if port is protected
        """
        return any(start <= port <= end for start, end in self.PROTECTED_PORT_RANGES)

    def _load_project_state(self) -> Dict[str, Any]:
        """
        Load project deployment state.

        Returns:
            State dictionary or empty dict if not found
        """
        try:
            if self.state_file.exists():
                with self.state_file.open() as f:
                    return json.load(f)
        except Exception as e:
            self.log_warning(f"Failed to load project state: {e}")

        return {}

    def _save_project_state(self, state: Dict[str, Any]) -> None:
        """
        Save project deployment state atomically.

        Args:
            state: State dictionary to save
        """
        try:
            # Write to temporary file first
            temp_file = self.state_file.with_suffix(".tmp")
            with temp_file.open("w") as f:
                json.dump(state, f, indent=2)

            # Atomic rename
            temp_file.replace(self.state_file)

        except Exception as e:
            self.log_error(f"Failed to save project state: {e}")
            raise

    def _load_global_registry(self) -> Dict[str, Any]:
        """
        Load global port registry.

        Returns:
            Registry dictionary or empty dict if not found
        """
        try:
            if self.global_registry_file.exists():
                with self.global_registry_file.open() as f:
                    return json.load(f)
        except Exception as e:
            self.log_warning(f"Failed to load global registry: {e}")

        return {"allocations": {}, "last_updated": None}

    def _save_global_registry(self, registry: Dict[str, Any]) -> None:
        """
        Save global port registry atomically.

        Args:
            registry: Registry dictionary to save
        """
        try:
            # Update timestamp
            registry["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Write to temporary file first
            temp_file = self.global_registry_file.with_suffix(".tmp")
            with temp_file.open("w") as f:
                json.dump(registry, f, indent=2)

            # Atomic rename
            temp_file.replace(self.global_registry_file)

        except Exception as e:
            self.log_error(f"Failed to save global registry: {e}")
            raise

    def get_project_port(
        self,
        project_path: Optional[Path] = None,
        service_name: str = "main",
        respect_env_override: bool = True,
    ) -> int:
        """
        Get the allocated port for a project service.

        This is the main entry point for port allocation. It:
        1. Checks for environment variable override (PROJECT_PORT)
        2. Checks existing allocation in state files
        3. Computes hash-based port with linear probing for conflicts

        Args:
            project_path: Path to project (default: self.project_root)
            service_name: Name of the service (default: "main")
            respect_env_override: Whether to respect PROJECT_PORT env var

        Returns:
            Allocated port number

        Raises:
            RuntimeError: If no available port found
        """
        project_path = (project_path or self.project_root).resolve()

        # Check environment variable override
        if respect_env_override:
            env_port = os.environ.get("PROJECT_PORT")
            if env_port:
                try:
                    port = int(env_port)
                    self.log_info(
                        f"Using port {port} from PROJECT_PORT environment variable"
                    )
                    return port
                except ValueError:
                    self.log_warning(f"Invalid PROJECT_PORT value: {env_port}")

        # Check existing allocation
        state = self._load_project_state()
        deployments = state.get("deployments", {})

        if service_name in deployments:
            existing_port = deployments[service_name].get("port")
            if existing_port and self._is_port_available(existing_port):
                self.log_info(
                    f"Reusing existing port {existing_port} for {service_name}"
                )
                return existing_port

        # Compute hash-based port with linear probing
        project_hash = self._compute_project_hash(project_path)
        base_port = self._hash_to_port(project_hash)

        # Try base port first
        port = self._find_available_port(base_port, project_path, service_name)

        self.log_info(
            f"Allocated port {port} for {service_name} "
            f"(hash: {project_hash[:8]}, base: {base_port})"
        )

        return port

    def _find_available_port(
        self,
        start_port: int,
        project_path: Path,
        service_name: str,
    ) -> int:
        """
        Find available port using linear probing.

        Args:
            start_port: Starting port from hash
            project_path: Project path
            service_name: Service name

        Returns:
            Available port number

        Raises:
            RuntimeError: If no available port found
        """
        max_probes = self.port_range_end - self.port_range_start + 1

        for offset in range(max_probes):
            port = start_port + offset

            # Wrap around if we exceed range
            if port > self.port_range_end:
                port = self.port_range_start + (port - self.port_range_end - 1)

            # Skip protected ports
            if self._is_protected_port(port):
                continue

            # Check if port is available
            if self._is_port_available(port):
                return port

        raise RuntimeError(
            f"No available ports in range {self.port_range_start}-{self.port_range_end}"
        )

    def register_port(
        self,
        port: int,
        service_name: str = "main",
        deployment_info: Optional[Dict[str, Any]] = None,
        project_path: Optional[Path] = None,
    ) -> None:
        """
        Register a port allocation for a project service.

        Args:
            port: Port number
            service_name: Service name
            deployment_info: Additional deployment information
            project_path: Project path (default: self.project_root)
        """
        project_path = (project_path or self.project_root).resolve()
        project_hash = self._compute_project_hash(project_path)

        # Update project state
        state = self._load_project_state()

        if "project_path" not in state:
            state["project_path"] = str(project_path)
            state["project_hash"] = project_hash
            state["deployments"] = {}
            state["port_history"] = []

        # Merge deployment info
        deployment_data = deployment_info or {}
        deployment_data.update(
            {
                "port": port,
                "service_name": service_name,
                "registered_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        state["deployments"][service_name] = deployment_data

        # Track port history
        if port not in state.get("port_history", []):
            state.setdefault("port_history", []).append(port)

        state["last_updated"] = datetime.now(timezone.utc).isoformat()

        self._save_project_state(state)

        # Update global registry
        registry = self._load_global_registry()

        registry.setdefault("allocations", {})[str(port)] = {
            "project_path": str(project_path),
            "project_hash": project_hash,
            "service_name": service_name,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        self._save_global_registry(registry)

        self.log_info(f"Registered port {port} for {service_name}")

    def release_port(
        self,
        port: int,
        service_name: str = "main",
        project_path: Optional[Path] = None,
    ) -> None:
        """
        Release a port allocation.

        Args:
            port: Port number to release
            service_name: Service name
            project_path: Project path (default: self.project_root)
        """
        project_path = (project_path or self.project_root).resolve()

        # Update project state
        state = self._load_project_state()
        deployments = state.get("deployments", {})

        if service_name in deployments:
            del deployments[service_name]
            state["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._save_project_state(state)

        # Update global registry
        registry = self._load_global_registry()
        allocations = registry.get("allocations", {})

        if str(port) in allocations:
            del allocations[str(port)]
            self._save_global_registry(registry)

        self.log_info(f"Released port {port} for {service_name}")

    def cleanup_dead_registrations(self) -> int:
        """
        Clean up registrations for dead processes.

        Returns:
            Number of registrations cleaned up
        """
        cleaned = 0

        # Clean project state
        state = self._load_project_state()
        deployments = state.get("deployments", {})
        dead_services = []

        for service_name, deployment in deployments.items():
            pid = deployment.get("pid")
            if pid and not self._is_process_alive(pid):
                dead_services.append(service_name)
                cleaned += 1

        for service_name in dead_services:
            self.log_info(f"Cleaning up dead deployment: {service_name}")
            del deployments[service_name]

        if dead_services:
            state["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._save_project_state(state)

        # Clean global registry
        registry = self._load_global_registry()
        allocations = registry.get("allocations", {})
        dead_ports = []

        for port_str, allocation in allocations.items():
            project_path = Path(allocation.get("project_path", ""))

            # Check if project still exists
            if not project_path.exists():
                dead_ports.append(port_str)
                cleaned += 1
                continue

            # Check project state file
            state_file = project_path / ".claude-mpm" / self.STATE_FILE_NAME
            if state_file.exists():
                try:
                    with state_file.open() as f:
                        project_state = json.load(f)

                    # Check if service still registered
                    service_name = allocation.get("service_name")
                    if service_name not in project_state.get("deployments", {}):
                        dead_ports.append(port_str)
                        cleaned += 1

                except Exception as e:
                    self.log_warning(f"Error checking state for port {port_str}: {e}")

        for port_str in dead_ports:
            self.log_info(f"Cleaning up dead global allocation: port {port_str}")
            del allocations[port_str]

        if dead_ports:
            self._save_global_registry(registry)

        if cleaned > 0:
            self.log_info(f"Cleaned up {cleaned} dead registrations")

        return cleaned

    def _is_process_alive(self, pid: int) -> bool:
        """
        Check if a process is alive.

        Args:
            pid: Process ID

        Returns:
            True if process is alive
        """
        try:
            return psutil.pid_exists(pid)
        except Exception:
            return False

    def get_allocation_info(
        self,
        service_name: str = "main",
        project_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get allocation information for a service.

        Args:
            service_name: Service name
            project_path: Project path (default: self.project_root)

        Returns:
            Allocation info dict or None if not found
        """
        project_path = (project_path or self.project_root).resolve()
        state = self._load_project_state()
        deployments = state.get("deployments", {})

        return deployments.get(service_name)

    def list_project_allocations(
        self,
        project_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        List all port allocations for a project.

        Args:
            project_path: Project path (default: self.project_root)

        Returns:
            Dictionary of service allocations
        """
        project_path = (project_path or self.project_root).resolve()
        state = self._load_project_state()

        return {
            "project_path": str(project_path),
            "project_hash": state.get("project_hash"),
            "deployments": state.get("deployments", {}),
            "port_history": state.get("port_history", []),
            "last_updated": state.get("last_updated"),
        }

    def list_global_allocations(self) -> Dict[str, Any]:
        """
        List all global port allocations.

        Returns:
            Global registry data
        """
        return self._load_global_registry()
