from pathlib import Path

"""
Central type definitions for Claude MPM.

This module provides shared type definitions to prevent circular import
dependencies. By centralizing commonly used types, we avoid the need for
cross-module imports that can create circular dependency chains.

WHY: Circular imports were causing ImportError exceptions throughout the
codebase. By extracting shared types to this central location, modules
can import types without creating dependency cycles.

DESIGN DECISION: Only include types that are shared across multiple modules.
Module-specific types should remain in their respective modules.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from .enums import HealthStatus


# Service operation results
@dataclass
class ServiceResult:
    """Standard result type for service operations."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "errors": self.errors,
        }


# Deployment-related types
@dataclass
class DeploymentResult:
    """Result of an agent deployment operation."""

    deployed: list[str]
    updated: list[str]
    failed: list[str]
    skipped: list[str]
    errors: dict[str, str]
    metadata: dict[str, Any]

    @property
    def total_processed(self) -> int:
        """Get total number of agents processed."""
        return (
            len(self.deployed)
            + len(self.updated)
            + len(self.failed)
            + len(self.skipped)
        )

    @property
    def success_rate(self) -> float:
        """Calculate deployment success rate."""
        if self.total_processed == 0:
            return 0.0
        successful = len(self.deployed) + len(self.updated)
        return successful / self.total_processed


# Agent-related types
class AgentTier(Enum):
    """Agent tier levels for precedence."""

    PROJECT = "PROJECT"  # Highest precedence - project-specific agents
    USER = "USER"  # User-level agents
    SYSTEM = "SYSTEM"  # Lowest precedence - system agents

    @classmethod
    def from_string(cls, value: str) -> "AgentTier":
        """Convert string to AgentTier enum."""
        value_upper = value.upper()
        for tier in cls:
            if tier.value == value_upper:
                return tier
        raise ValueError(f"Invalid agent tier: {value}")


@dataclass
class AgentInfo:
    """Basic agent information."""

    agent_id: str
    name: str
    tier: AgentTier
    path: Path
    version: str | None = None
    description: str | None = None
    capabilities: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}


# Memory-related types
@dataclass
class MemoryEntry:
    """Single memory entry for an agent."""

    timestamp: datetime
    content: str
    category: str
    agent_id: str
    session_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


# Hook-related types
class HookType(Enum):
    """Types of hooks in the system."""

    PRE_DELEGATION = "pre_delegation"
    POST_DELEGATION = "post_delegation"
    PRE_RESPONSE = "pre_response"
    POST_RESPONSE = "post_response"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class HookContext:
    """Context passed to hook handlers."""

    event_type: str
    data: dict[str, Any]
    timestamp: datetime
    source: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


# Configuration types
@dataclass
class ConfigSection:
    """Configuration section with validation."""

    name: str
    values: dict[str, Any]
    schema: dict[str, Any] | None = None
    is_valid: bool = True
    validation_errors: list[str] | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.validation_errors is None:
            self.validation_errors = []


# Task/Ticket types
class TaskStatus(Enum):
    """Task/ticket status values."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Basic task/ticket information."""

    task_id: str
    title: str
    status: TaskStatus
    description: str | None = None
    assignee: str | None = None
    priority: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.updated_at is None:
            self.updated_at = self.created_at


# WebSocket/SocketIO types
@dataclass
class SocketMessage:
    """WebSocket/SocketIO message."""

    event: str
    data: Any
    room: str | None = None
    namespace: str | None = None
    sid: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


# Health monitoring types
@dataclass
class HealthCheck:
    """Health check result."""

    service_name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    metrics: dict[str, Any] | None = None
    checks: dict[str, bool] | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metrics is None:
            self.metrics = {}
        if self.checks is None:
            self.checks = {}


# Project analysis types
@dataclass
class ProjectCharacteristics:
    """Analyzed project characteristics."""

    path: Path
    name: str
    type: str  # e.g., "python", "node", "mixed"
    technologies: list[str]
    entry_points: list[Path]
    structure: dict[str, Any]
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


# Error types
class ErrorSeverity(Enum):
    """Error severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context for error handling."""

    error: Exception
    severity: ErrorSeverity
    component: str
    operation: str
    timestamp: datetime
    traceback: str | None = None
    recovery_attempted: bool = False
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


# Type aliases for common patterns
ConfigDict = dict[str, Any]
ErrorDict = dict[str, str]
MetricsDict = dict[str, int | float | str]
ValidationResult = tuple[bool, list[str] | None]
