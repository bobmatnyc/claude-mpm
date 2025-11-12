"""
Local Process Manager for Claude MPM Framework
==============================================

WHY: Provides reliable process lifecycle management for local deployments
with process isolation, port conflict prevention, and graceful shutdown.

DESIGN DECISION: Uses subprocess.Popen for direct process control with
process groups for clean termination. Integrates with DeploymentStateManager
for persistent tracking.

ARCHITECTURE:
- Process group isolation (start_new_session=True on Unix)
- Port conflict detection using psutil
- Linear probing for alternative ports
- Protected port range enforcement
- Graceful shutdown with timeout and force kill fallback

USAGE:
    state_manager = DeploymentStateManager(state_file_path)
    process_manager = LocalProcessManager(state_manager)

    config = StartConfig(
        command=["npm", "run", "dev"],
        working_directory="/path/to/project",
        port=3000
    )

    deployment = process_manager.start(config)
    process_manager.stop(deployment.deployment_id)
"""

import os
import platform
import signal
import subprocess
import time
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import List, Optional

import psutil

from claude_mpm.core.enums import ServiceState
from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.process import (
    IDeploymentStateManager,
    ILocalProcessManager,
)
from claude_mpm.services.core.models.process import (
    DeploymentState,
    ProcessInfo,
    StartConfig,
    is_port_protected,
)


class ProcessSpawnError(Exception):
    """Raised when process cannot be spawned."""


class PortConflictError(Exception):
    """Raised when requested port is unavailable and no alternative found."""


class LocalProcessManager(SyncBaseService, ILocalProcessManager):
    """
    Manages local process lifecycle with isolation and state tracking.

    WHY: Provides high-level process management operations that handle
    all the complexity of spawning, tracking, and terminating background
    processes reliably.

    Thread Safety: Operations are thread-safe through state manager locking.
    """

    def __init__(self, state_manager: IDeploymentStateManager):
        """
        Initialize process manager.

        Args:
            state_manager: State manager for deployment persistence
        """
        super().__init__("LocalProcessManager")
        self.state_manager = state_manager
        self.is_windows = platform.system() == "Windows"

    def initialize(self) -> bool:
        """
        Initialize the process manager.

        Returns:
            True if initialization successful
        """
        try:
            # Ensure state manager is initialized
            if not self.state_manager.is_initialized:
                if not self.state_manager.initialize():
                    self.log_error("Failed to initialize state manager")
                    return False

            self._initialized = True
            self.log_info("Process manager initialized")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown process manager (processes continue running)."""
        self._shutdown = True
        self.log_info("Process manager shutdown complete")

    def start(self, config: StartConfig) -> DeploymentState:
        """
        Start a new background process.

        WHY: Combines process spawning, port allocation, and state tracking
        in a single atomic operation.

        Args:
            config: Configuration for the process to start

        Returns:
            DeploymentState with process information

        Raises:
            ProcessSpawnError: If process cannot be spawned
            PortConflictError: If port unavailable and no alternative found
            ValueError: If configuration is invalid
        """
        # Validate working directory exists
        working_dir = Path(config.working_directory)
        if not working_dir.exists():
            raise ValueError(f"Working directory does not exist: {working_dir}")

        # Handle port allocation if needed
        allocated_port = None
        if config.port is not None:
            allocated_port = self._allocate_port(config.port, config.auto_find_port)

        # Generate deployment ID if not provided
        project_name = working_dir.name
        deployment_id = config.deployment_id or self.generate_deployment_id(
            project_name, allocated_port
        )

        # Prepare environment variables
        env = os.environ.copy()
        env.update(config.environment)
        if allocated_port is not None:
            env["PORT"] = str(allocated_port)

        # Spawn the process
        try:
            self.log_info(
                f"Spawning process for {deployment_id}: {' '.join(config.command)}"
            )

            # Platform-specific process group creation
            if self.is_windows:
                # Windows: use CREATE_NEW_PROCESS_GROUP
                process = subprocess.Popen(
                    config.command,
                    cwd=str(working_dir),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                # Unix: use start_new_session for process group isolation
                process = subprocess.Popen(
                    config.command,
                    cwd=str(working_dir),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                )

            # Give process a moment to start
            time.sleep(0.5)

            # Check if process is still running
            if process.poll() is not None:
                # Process died immediately
                _stdout, stderr = process.communicate()
                error_msg = stderr.decode("utf-8", errors="replace") if stderr else ""
                raise ProcessSpawnError(
                    f"Process died immediately. Exit code: {process.returncode}. "
                    f"Error: {error_msg}"
                )

            # Create deployment state
            deployment = DeploymentState(
                deployment_id=deployment_id,
                process_id=process.pid,
                command=config.command,
                working_directory=str(working_dir),
                environment=config.environment,
                port=allocated_port,
                started_at=datetime.now(tz=timezone.utc),
                status=ServiceState.RUNNING,
                metadata=config.metadata,
            )

            # Save to state
            self.state_manager.add_deployment(deployment)

            self.log_info(
                f"Started process {process.pid} for {deployment_id} "
                f"on port {allocated_port or 'N/A'}"
            )

            return deployment

        except subprocess.SubprocessError as e:
            raise ProcessSpawnError(f"Failed to spawn process: {e}") from e

    def stop(self, deployment_id: str, timeout: int = 10, force: bool = False) -> bool:
        """
        Stop a running process.

        WHY: Provides graceful shutdown with configurable timeout and
        force kill fallback for stuck processes.

        Args:
            deployment_id: Unique deployment identifier
            timeout: Seconds to wait for graceful shutdown
            force: If True, kill immediately without waiting

        Returns:
            True if process stopped successfully

        Raises:
            ValueError: If deployment_id not found
        """
        deployment = self.state_manager.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        try:
            process = psutil.Process(deployment.process_id)
        except psutil.NoSuchProcess:
            # Process already dead, just update state
            self.log_info(f"Process {deployment.process_id} already dead")
            self.state_manager.update_deployment_status(
                deployment_id, ServiceState.STOPPED
            )
            return True

        self.log_info(f"Stopping process {deployment.process_id} for {deployment_id}")
        self.state_manager.update_deployment_status(
            deployment_id, ServiceState.STOPPING
        )

        try:
            if force:
                # Force kill immediately
                self._kill_process_group(process)
                self.state_manager.update_deployment_status(
                    deployment_id, ServiceState.STOPPED
                )
                return True

            # Try graceful shutdown first
            self._terminate_process_group(process)

            # Wait for process to die
            start_time = time.time()
            while time.time() - start_time < timeout:
                if not process.is_running():
                    self.log_info(f"Process {deployment.process_id} stopped gracefully")
                    self.state_manager.update_deployment_status(
                        deployment_id, ServiceState.STOPPED
                    )
                    return True
                time.sleep(0.1)

            # Timeout exceeded, force kill
            self.log_warning(
                f"Graceful shutdown timeout, force killing {deployment.process_id}"
            )
            self._kill_process_group(process)
            self.state_manager.update_deployment_status(
                deployment_id, ServiceState.STOPPED
            )
            return True

        except psutil.NoSuchProcess:
            # Process died during shutdown
            self.state_manager.update_deployment_status(
                deployment_id, ServiceState.STOPPED
            )
            return True

        except Exception as e:
            self.log_error(f"Error stopping process: {e}")
            return False

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
        # Get existing deployment config
        deployment = self.state_manager.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        # Stop the process
        self.stop(deployment_id, timeout=timeout)

        # Create new start config from existing deployment
        config = StartConfig(
            command=deployment.command,
            working_directory=deployment.working_directory,
            environment=deployment.environment,
            port=deployment.port,
            auto_find_port=True,
            metadata=deployment.metadata,
        )

        # Remove old deployment from state
        self.state_manager.remove_deployment(deployment_id)

        # Start new process
        return self.start(config)

    def get_status(self, deployment_id: str) -> Optional[ProcessInfo]:
        """
        Get current status and runtime information for a process.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            ProcessInfo with current status, or None if not found
        """
        deployment = self.state_manager.get_deployment(deployment_id)
        if not deployment:
            return None

        try:
            process = psutil.Process(deployment.process_id)

            # Calculate uptime
            create_time = process.create_time()
            uptime = time.time() - create_time

            # Get memory usage
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)

            # Get CPU usage
            cpu_percent = process.cpu_percent(interval=0.1)

            # Determine status
            if process.is_running():
                status = ServiceState.RUNNING
            else:
                status = ServiceState.STOPPED

            return ProcessInfo(
                deployment_id=deployment_id,
                process_id=deployment.process_id,
                status=status,
                port=deployment.port,
                uptime_seconds=uptime,
                memory_mb=memory_mb,
                cpu_percent=cpu_percent,
                is_responding=True,  # TODO: Add actual health check
            )

        except psutil.NoSuchProcess:
            return ProcessInfo(
                deployment_id=deployment_id,
                process_id=deployment.process_id,
                status=ServiceState.ERROR,  # CRASHED semantically maps to ERROR state
                port=deployment.port,
                error_message="Process no longer exists",
            )

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
        if status_filter:
            deployments = self.state_manager.get_deployments_by_status(status_filter)
        else:
            deployments = self.state_manager.get_all_deployments()

        process_infos = []
        for deployment in deployments:
            info = self.get_status(deployment.deployment_id)
            if info:
                process_infos.append(info)

        return process_infos

    def is_port_available(self, port: int) -> bool:
        """
        Check if a port is available for use.

        WHY: Port conflict prevention is critical for reliable deployments.

        Args:
            port: Port number to check

        Returns:
            True if port is available
        """
        # Check if port is protected
        if is_port_protected(port):
            return False

        # Check if port is in use
        connections = psutil.net_connections()
        return all(conn.laddr.port != port for conn in connections)

    def find_available_port(
        self, preferred_port: int, max_attempts: int = 10
    ) -> Optional[int]:
        """
        Find an available port starting from preferred_port.

        WHY: Uses linear probing to find alternative ports when preferred
        port is unavailable. Respects protected port ranges.

        Args:
            preferred_port: Starting port number
            max_attempts: Maximum number of ports to try

        Returns:
            Available port number, or None if none found
        """
        for offset in range(max_attempts):
            candidate_port = preferred_port + offset

            # Skip ports outside valid range
            if candidate_port > 65535:
                break

            # Check if port is available
            if self.is_port_available(candidate_port):
                if offset > 0:
                    self.log_info(
                        f"Port {preferred_port} unavailable, using {candidate_port}"
                    )
                return candidate_port

        return None

    def cleanup_orphans(self) -> int:
        """
        Clean up orphaned process state entries.

        WHY: Processes may crash or be killed externally, leaving stale state.

        Returns:
            Number of orphaned entries cleaned up
        """
        return self.state_manager.cleanup_dead_pids()

    def generate_deployment_id(
        self, project_name: str, port: Optional[int] = None
    ) -> str:
        """
        Generate a unique deployment ID.

        WHY: Provides consistent ID generation with optional port suffix.

        Args:
            project_name: Name of the project
            port: Optional port number to include in ID

        Returns:
            Unique deployment identifier
        """
        # Use timestamp for uniqueness
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")

        # Generate short hash from project name for readability
        name_hash = sha256(project_name.encode()).hexdigest()[:8]

        if port:
            return f"{project_name}_{name_hash}_{timestamp}_p{port}"
        return f"{project_name}_{name_hash}_{timestamp}"

    def _allocate_port(self, preferred_port: int, auto_find: bool) -> int:
        """
        Allocate a port for the deployment.

        Args:
            preferred_port: Preferred port number
            auto_find: If True, find alternative if preferred unavailable

        Returns:
            Allocated port number

        Raises:
            PortConflictError: If port unavailable and auto_find is False
        """
        # Check if preferred port is available
        if self.is_port_available(preferred_port):
            return preferred_port

        # If auto_find disabled, raise error
        if not auto_find:
            raise PortConflictError(
                f"Port {preferred_port} is unavailable and auto_find_port is disabled"
            )

        # Find alternative port
        alternative = self.find_available_port(preferred_port)
        if alternative is None:
            raise PortConflictError(
                f"No available ports found starting from {preferred_port}"
            )

        return alternative

    def _terminate_process_group(self, process: psutil.Process) -> None:
        """
        Send SIGTERM to process group for graceful shutdown.

        Args:
            process: Process to terminate
        """
        if self.is_windows:
            # Windows: terminate the process tree
            try:
                parent = process
                children = parent.children(recursive=True)
                for child in children:
                    child.terminate()
                parent.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        else:
            # Unix: send SIGTERM to process group
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                # Fallback to single process
                process.terminate()

    def _kill_process_group(self, process: psutil.Process) -> None:
        """
        Send SIGKILL to process group for force termination.

        Args:
            process: Process to kill
        """
        if self.is_windows:
            # Windows: kill the process tree
            try:
                parent = process
                children = parent.children(recursive=True)
                for child in children:
                    child.kill()
                parent.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        else:
            # Unix: send SIGKILL to process group
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                # Fallback to single process
                process.kill()


__all__ = ["LocalProcessManager", "PortConflictError", "ProcessSpawnError"]
