"""
Process Management Interfaces for Claude MPM Framework
=======================================================

WHY: This module defines interfaces for local process management operations,
enabling the local-ops-agent to spawn, track, and manage background processes
with proper isolation, state persistence, and port conflict prevention.

DESIGN DECISION: Process management interfaces are separated from other service
interfaces to maintain clear boundaries between deployment operations and other
system services.

ARCHITECTURE:
- ILocalProcessManager: Core interface for process lifecycle management
- IDeploymentStateManager: Interface for persistent state tracking
- Process data models defined in models/process.py

USAGE:
    state_manager = DeploymentStateManager(state_file_path)
    process_manager = LocalProcessManager(state_manager)

    config = StartConfig(
        command=["npm", "run", "dev"],
        working_directory="/path/to/project",
        port=3000
    )

    deployment = await process_manager.start(config)
    print(f"Started process {deployment.process_id} on port {deployment.port}")
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from claude_mpm.core.enums import ServiceState
from claude_mpm.services.core.models.process import (
    DeploymentState,
    ProcessInfo,
    StartConfig,
)


class IDeploymentStateManager(ABC):
    """
    Interface for deployment state persistence and management.

    WHY: State persistence is critical for tracking processes across restarts
    and preventing orphaned processes. This interface abstracts the storage
    mechanism to enable different backends (JSON file, database, etc.).

    DESIGN DECISION: Provides both low-level (save/load) and high-level (query)
    operations to support different use cases. Uses file locking to prevent
    corruption from concurrent access.

    Thread Safety: All operations must be thread-safe with proper locking.
    """

    @abstractmethod
    def load_state(self) -> Dict[str, DeploymentState]:
        """
        Load all deployment states from persistent storage.

        Returns:
            Dictionary mapping deployment_id to DeploymentState

        Raises:
            StateCorruptionError: If state file is corrupted
            IOError: If state file cannot be read
        """

    @abstractmethod
    def save_state(self, states: Dict[str, DeploymentState]) -> None:
        """
        Save all deployment states to persistent storage.

        Args:
            states: Dictionary mapping deployment_id to DeploymentState

        Raises:
            IOError: If state file cannot be written
        """

    @abstractmethod
    def get_deployment(self, deployment_id: str) -> Optional[DeploymentState]:
        """
        Get a specific deployment by ID.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            DeploymentState if found, None otherwise
        """

    @abstractmethod
    def get_all_deployments(self) -> List[DeploymentState]:
        """
        Get all tracked deployments.

        Returns:
            List of all DeploymentState objects
        """

    @abstractmethod
    def get_deployments_by_status(self, status: ServiceState) -> List[DeploymentState]:
        """
        Get all deployments with a specific status.

        Args:
            status: ServiceState to filter by

        Returns:
            List of matching DeploymentState objects
        """

    @abstractmethod
    def get_deployment_by_port(self, port: int) -> Optional[DeploymentState]:
        """
        Get deployment using a specific port.

        Args:
            port: Port number to search for

        Returns:
            DeploymentState if found, None otherwise
        """

    @abstractmethod
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

    @abstractmethod
    def add_deployment(self, deployment: DeploymentState) -> None:
        """
        Add or update a deployment in state.

        Args:
            deployment: DeploymentState to add/update

        Raises:
            IOError: If state cannot be persisted
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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


class ILocalProcessManager(ABC):
    """
    Interface for local process lifecycle management.

    WHY: Process management involves complex operations like spawning, tracking,
    and terminating background processes. This interface abstracts these operations
    to enable different implementations and improve testability.

    DESIGN DECISION: Provides high-level operations (start, stop, restart) that
    handle all the complexity internally including port checking, process group
    isolation, and state tracking.

    Process Lifecycle:
    1. Start: Spawn process with isolation and port checking
    2. Monitor: Track status and update state
    3. Stop: Graceful shutdown with fallback to force kill
    4. Cleanup: Remove state and release resources
    """

    @abstractmethod
    def start(self, config: StartConfig) -> DeploymentState:
        """
        Start a new background process.

        WHY: Combines process spawning, port allocation, and state tracking in
        a single operation to ensure consistency.

        Args:
            config: Configuration for the process to start

        Returns:
            DeploymentState with process information

        Raises:
            ProcessSpawnError: If process cannot be spawned
            PortConflictError: If requested port is unavailable and no alternative found
            ValueError: If configuration is invalid
        """

    @abstractmethod
    def stop(self, deployment_id: str, timeout: int = 10, force: bool = False) -> bool:
        """
        Stop a running process.

        WHY: Provides graceful shutdown with configurable timeout and force
        option for stuck processes.

        Args:
            deployment_id: Unique deployment identifier
            timeout: Seconds to wait for graceful shutdown
            force: If True, kill immediately without waiting

        Returns:
            True if process stopped successfully

        Raises:
            ValueError: If deployment_id not found
        """

    @abstractmethod
    def restart(self, deployment_id: str, timeout: int = 10) -> DeploymentState:
        """
        Restart a process (stop then start with same config).

        Args:
            deployment_id: Unique deployment identifier
            timeout: Seconds to wait for graceful shutdown

        Returns:
            New DeploymentState after restart

        Raises:
            ValueError: If deployment_id not found
            ProcessSpawnError: If restart fails
        """

    @abstractmethod
    def get_status(self, deployment_id: str) -> Optional[ProcessInfo]:
        """
        Get current status and runtime information for a process.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            ProcessInfo with current status, or None if not found
        """

    @abstractmethod
    def list_processes(
        self, status_filter: Optional[ServiceState] = None
    ) -> List[ProcessInfo]:
        """
        List all managed processes.

        Args:
            status_filter: Optional status to filter by

        Returns:
            List of ProcessInfo for all matching processes
        """

    @abstractmethod
    def is_port_available(self, port: int) -> bool:
        """
        Check if a port is available for use.

        WHY: Port conflict prevention is critical for reliable deployments.
        This check happens before process spawn.

        Args:
            port: Port number to check

        Returns:
            True if port is available
        """

    @abstractmethod
    def find_available_port(
        self, preferred_port: int, max_attempts: int = 10
    ) -> Optional[int]:
        """
        Find an available port starting from preferred_port.

        WHY: Uses linear probing to find alternative ports when the preferred
        port is unavailable. Respects protected port ranges.

        Args:
            preferred_port: Starting port number
            max_attempts: Maximum number of ports to try

        Returns:
            Available port number, or None if none found
        """

    @abstractmethod
    def cleanup_orphans(self) -> int:
        """
        Clean up orphaned process state entries.

        WHY: Processes may crash or be killed externally, leaving stale state.
        This method identifies and cleans up these orphans.

        Returns:
            Number of orphaned entries cleaned up
        """

    @abstractmethod
    def generate_deployment_id(
        self, project_name: str, port: Optional[int] = None
    ) -> str:
        """
        Generate a unique deployment ID.

        WHY: Provides consistent ID generation with optional port suffix for
        projects with multiple deployments.

        Args:
            project_name: Name of the project
            port: Optional port number to include in ID

        Returns:
            Unique deployment identifier
        """


__all__ = [
    "IDeploymentStateManager",
    "ILocalProcessManager",
]
