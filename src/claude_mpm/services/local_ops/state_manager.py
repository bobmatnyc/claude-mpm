"""
Deployment State Manager for Claude MPM Framework
=================================================

WHY: Provides persistent state tracking for local deployments with atomic
operations, file locking, and corruption recovery. Critical for preventing
orphaned processes and ensuring deployment reliability.

DESIGN DECISION: Uses JSON file storage with filelock for simplicity and
portability. File-based storage is sufficient for local deployments and
doesn't require external dependencies.

ARCHITECTURE:
- Thread-safe operations with file locking
- Atomic read-modify-write cycles
- Automatic corruption detection and recovery
- Process validation using psutil

USAGE:
    manager = DeploymentStateManager(state_file_path)
    manager.add_deployment(deployment_state)
    deployments = manager.get_all_deployments()
    manager.cleanup_dead_pids()
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import psutil
from filelock import FileLock

from claude_mpm.core.enums import ServiceState
from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.process import IDeploymentStateManager
from claude_mpm.services.core.models.process import DeploymentState


class StateCorruptionError(Exception):
    """Raised when state file is corrupted and cannot be recovered."""


class DeploymentStateManager(SyncBaseService, IDeploymentStateManager):
    """
    Manages persistent deployment state with atomic operations.

    WHY: Deployment state must survive restarts and be accessible to
    multiple processes. This manager ensures consistency with file locking
    and provides corruption recovery.

    Thread Safety: All public methods use file locking for atomicity.
    """

    def __init__(self, state_file_path: str):
        """
        Initialize state manager.

        Args:
            state_file_path: Path to JSON state file

        Raises:
            ValueError: If state_file_path is invalid
        """
        super().__init__("DeploymentStateManager")

        self.state_file = Path(state_file_path)
        self.lock_file = Path(str(state_file_path) + ".lock")

        # Create single FileLock instance for re-entrant locking
        # WHY: Using the same lock instance allows re-entrant calls
        # (e.g., add_deployment -> load_state) without deadlock
        self._file_lock = FileLock(str(self.lock_file), timeout=10)

        # Ensure parent directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize empty state if file doesn't exist
        if not self.state_file.exists():
            self._write_state({})

        self.log_info(f"Initialized state manager with file: {self.state_file}")

    def initialize(self) -> bool:
        """
        Initialize the state manager.

        Returns:
            True if initialization successful
        """
        try:
            # Validate state file can be read
            self.load_state()
            self._initialized = True
            return True
        except Exception as e:
            self.log_error(f"Failed to initialize: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown state manager (no resources to clean up)."""
        self._shutdown = True
        self.log_info("State manager shutdown complete")

    def load_state(self) -> Dict[str, DeploymentState]:
        """
        Load all deployment states from file.

        Returns:
            Dictionary mapping deployment_id to DeploymentState

        Raises:
            StateCorruptionError: If state file is corrupted beyond recovery
        """
        with self._file_lock:
            try:
                if not self.state_file.exists():
                    return {}

                with self.state_file.open() as f:
                    data = json.load(f)

                # Convert dict entries to DeploymentState objects
                states = {}
                for deployment_id, state_dict in data.items():
                    try:
                        states[deployment_id] = DeploymentState.from_dict(state_dict)
                    except Exception as e:
                        self.log_warning(
                            f"Skipping corrupted state entry {deployment_id}: {e}"
                        )

                return states

            except json.JSONDecodeError as e:
                self.log_error(f"State file corrupted: {e}")
                # Attempt recovery by backing up and creating fresh state
                backup_path = self.state_file.with_suffix(".json.corrupted")
                self.state_file.rename(backup_path)
                self.log_warning(f"Backed up corrupted state to {backup_path}")
                self._write_state({})
                return {}

            except Exception as e:
                raise StateCorruptionError(f"Failed to load state: {e}") from e

    def save_state(self, states: Dict[str, DeploymentState]) -> None:
        """
        Save all deployment states to file.

        Args:
            states: Dictionary mapping deployment_id to DeploymentState

        Raises:
            IOError: If state file cannot be written
        """
        with self._file_lock:
            self._write_state(states)

    def _write_state(self, states: Dict[str, DeploymentState]) -> None:
        """
        Internal method to write state without locking.

        WHY: Allows caller to handle locking for atomic operations.

        Args:
            states: States to write (can be dict or DeploymentState dict)
        """
        # Convert DeploymentState objects to dicts
        data = {}
        for deployment_id, state in states.items():
            if isinstance(state, DeploymentState):
                data[deployment_id] = state.to_dict()
            else:
                data[deployment_id] = state

        # Atomic write: write to temp file then rename
        temp_file = self.state_file.with_suffix(".tmp")
        try:
            with temp_file.open("w") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.state_file)
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise OSError(f"Failed to write state: {e}") from e

    def get_deployment(self, deployment_id: str) -> Optional[DeploymentState]:
        """
        Get a specific deployment by ID.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            DeploymentState if found, None otherwise
        """
        states = self.load_state()
        return states.get(deployment_id)

    def get_all_deployments(self) -> List[DeploymentState]:
        """
        Get all tracked deployments.

        Returns:
            List of all DeploymentState objects
        """
        states = self.load_state()
        return list(states.values())

    def get_deployments_by_status(self, status: ServiceState) -> List[DeploymentState]:
        """
        Get all deployments with a specific status.

        Args:
            status: ServiceState to filter by

        Returns:
            List of matching DeploymentState objects
        """
        states = self.load_state()
        return [s for s in states.values() if s.status == status]

    def get_deployment_by_port(self, port: int) -> Optional[DeploymentState]:
        """
        Get deployment using a specific port.

        Args:
            port: Port number to search for

        Returns:
            DeploymentState if found, None otherwise
        """
        states = self.load_state()
        for state in states.values():
            if state.port == port:
                return state
        return None

    def get_deployments_by_project(
        self, working_directory: str
    ) -> List[DeploymentState]:
        """
        Get all deployments for a specific project directory.

        Args:
            working_directory: Project directory path

        Returns:
            List of matching DeploymentState objects
        """
        # Normalize path for comparison
        normalized_dir = str(Path(working_directory).absolute())
        states = self.load_state()
        return [
            s
            for s in states.values()
            if str(Path(s.working_directory).absolute()) == normalized_dir
        ]

    def add_deployment(self, deployment: DeploymentState) -> None:
        """
        Add or update a deployment in state.

        Args:
            deployment: DeploymentState to add/update

        Raises:
            IOError: If state cannot be persisted
        """
        with self._file_lock:
            states = self.load_state()
            states[deployment.deployment_id] = deployment
            self._write_state(states)
            self.log_debug(f"Added deployment: {deployment.deployment_id}")

    def remove_deployment(self, deployment_id: str) -> bool:
        """
        Remove a deployment from state.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            True if deployment was removed, False if not found

        Raises:
            IOError: If state cannot be persisted
        """
        with self._file_lock:
            states = self.load_state()
            if deployment_id in states:
                del states[deployment_id]
                self._write_state(states)
                self.log_debug(f"Removed deployment: {deployment_id}")
                return True
            return False

    def update_deployment_status(
        self, deployment_id: str, status: ServiceState
    ) -> bool:
        """
        Update the status of a deployment.

        Args:
            deployment_id: Unique deployment identifier
            status: New ServiceState

        Returns:
            True if updated, False if deployment not found

        Raises:
            IOError: If state cannot be persisted
        """
        with self._file_lock:
            states = self.load_state()
            if deployment_id in states:
                states[deployment_id].status = status
                self._write_state(states)
                self.log_debug(f"Updated status for {deployment_id}: {status.value}")
                return True
            return False

    def cleanup_dead_pids(self) -> int:
        """
        Remove deployments with dead process IDs.

        WHY: Processes may crash or be killed externally. This method cleans
        up stale state entries for processes that no longer exist.

        Returns:
            Number of dead PIDs cleaned up

        Raises:
            IOError: If state cannot be persisted
        """
        with self._file_lock:
            states = self.load_state()
            cleaned_count = 0

            for deployment_id, state in list(states.items()):
                if not self._is_pid_alive(state.process_id):
                    self.log_info(
                        f"Cleaning dead PID {state.process_id} for {deployment_id}"
                    )
                    del states[deployment_id]
                    cleaned_count += 1

            if cleaned_count > 0:
                self._write_state(states)
                self.log_info(f"Cleaned up {cleaned_count} dead PIDs")

            return cleaned_count

    def _is_pid_alive(self, pid: int) -> bool:
        """
        Check if a process ID is alive.

        Args:
            pid: Process ID to check

        Returns:
            True if process exists and is running
        """
        try:
            process = psutil.Process(pid)
            # Check if process still exists and is not a zombie
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False


__all__ = ["DeploymentStateManager", "StateCorruptionError"]
