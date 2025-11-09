"""
Process Management Data Models for Claude MPM Framework
========================================================

WHY: This module defines data structures for process management operations,
including deployment state and runtime information.

DESIGN DECISION: Uses dataclasses for immutability and type safety. Provides
serialization methods for state persistence. Process status uses ServiceState
enum from core.enums (consolidated in Phase 3A Batch 24).

ARCHITECTURE:
- DeploymentState: Complete deployment information for persistence
- ProcessInfo: Runtime process information
- StartConfig: Configuration for spawning new processes

Note: ProcessStatus enum has been consolidated into ServiceState (core.enums).
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.enums import ServiceState

# Backward compatibility alias (consolidated in Phase 3A Batch 24)
ProcessStatus = ServiceState


@dataclass
class DeploymentState:
    """
    Complete deployment state for persistence.

    WHY: Contains all information needed to track, manage, and restart
    a deployment. Serializable to JSON for state file storage.

    Attributes:
        deployment_id: Unique identifier for this deployment
        process_id: OS process ID (PID)
        command: Command and arguments used to start process
        working_directory: Working directory for the process
        environment: Environment variables (beyond inherited ones)
        port: Primary port used by the process (if applicable)
        started_at: Timestamp when process was started
        status: Current ServiceState (process lifecycle state)
        metadata: Additional deployment-specific information
    """

    deployment_id: str
    process_id: int
    command: List[str]
    working_directory: str
    environment: Dict[str, str] = field(default_factory=dict)
    port: Optional[int] = None
    started_at: datetime = field(default_factory=datetime.now)
    status: ServiceState = ServiceState.STARTING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation with datetime converted to ISO format
        """
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeploymentState":
        """
        Create DeploymentState from dictionary.

        Args:
            data: Dictionary from JSON deserialization

        Returns:
            DeploymentState instance
        """
        # Convert ISO string to datetime
        if isinstance(data.get("started_at"), str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])

        # Convert status string to enum
        if isinstance(data.get("status"), str):
            status_value = data["status"]
            # Handle legacy "crashed" status -> map to ERROR
            if status_value == "crashed":
                data["status"] = (
                    ServiceState.ERROR
                )  # CRASHED semantically maps to ERROR state
            else:
                data["status"] = ServiceState(status_value)

        return cls(**data)

    def to_json(self) -> str:
        """
        Serialize to JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "DeploymentState":
        """
        Deserialize from JSON string.

        Args:
            json_str: JSON string

        Returns:
            DeploymentState instance
        """
        return cls.from_dict(json.loads(json_str))


@dataclass
class ProcessInfo:
    """
    Runtime process information.

    WHY: Provides real-time process status including resource usage and
    health information. Separate from DeploymentState to avoid mixing
    persistent state with transient runtime data.

    Attributes:
        deployment_id: Unique deployment identifier
        process_id: OS process ID
        status: Current ServiceState (process lifecycle state)
        port: Port the process is using
        uptime_seconds: How long the process has been running
        memory_mb: Current memory usage in megabytes
        cpu_percent: Current CPU usage percentage
        is_responding: Whether the process responds to health checks
        error_message: Error message if status is ERROR (crashed)
    """

    deployment_id: str
    process_id: int
    status: ServiceState
    port: Optional[int] = None
    uptime_seconds: float = 0.0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    is_responding: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class StartConfig:
    """
    Configuration for starting a new process.

    WHY: Encapsulates all parameters needed to spawn a process. Provides
    validation and sensible defaults.

    Attributes:
        command: Command and arguments to execute
        working_directory: Working directory for the process
        environment: Environment variables to set (beyond inherited)
        port: Preferred port for the process
        auto_find_port: If True, find alternative port if preferred is unavailable
        metadata: Additional deployment metadata
        deployment_id: Optional explicit deployment ID (generated if not provided)
    """

    command: List[str]
    working_directory: str
    environment: Dict[str, str] = field(default_factory=dict)
    port: Optional[int] = None
    auto_find_port: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    deployment_id: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.command:
            raise ValueError("Command cannot be empty")

        if not self.working_directory:
            raise ValueError("Working directory must be specified")

        # Ensure working_directory is absolute
        self.working_directory = str(Path(self.working_directory).absolute())

        # Validate port range if specified
        if self.port is not None:
            if not (1024 <= self.port <= 65535):
                raise ValueError(f"Port must be between 1024-65535, got {self.port}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# Port range constants
PROTECTED_PORT_RANGES = [
    (8765, 8785),  # Claude MPM services (WebSocket, SocketIO, monitors)
]


def is_port_protected(port: int) -> bool:
    """
    Check if a port is in a protected range.

    WHY: Prevents local-ops-agent from interfering with Claude MPM
    system services.

    Args:
        port: Port number to check

    Returns:
        True if port is protected
    """
    return any(start <= port <= end for start, end in PROTECTED_PORT_RANGES)


__all__ = [
    "PROTECTED_PORT_RANGES",
    "DeploymentState",
    "ProcessInfo",
    "ProcessStatus",  # Backward compatibility alias for ServiceState
    "StartConfig",
    "is_port_protected",
]
