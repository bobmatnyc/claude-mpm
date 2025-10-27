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
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from .enums import HealthStatus


# Service operation results
@dataclass
class ServiceResult:
    """Standard result type for service operations."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
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

    deployed: List[str]
    updated: List[str]
    failed: List[str]
    skipped: List[str]
    errors: Dict[str, str]
    metadata: Dict[str, Any]

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
    version: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

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
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

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
    data: Dict[str, Any]
    timestamp: datetime
    source: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


# Configuration types
@dataclass
class ConfigSection:
    """Configuration section with validation."""

    name: str
    values: Dict[str, Any]
    schema: Optional[Dict[str, Any]] = None
    is_valid: bool = True
    validation_errors: Optional[List[str]] = None

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
    description: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at


# WebSocket/SocketIO types
@dataclass
class SocketMessage:
    """WebSocket/SocketIO message."""

    event: str
    data: Any
    room: Optional[str] = None
    namespace: Optional[str] = None
    sid: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

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
    metrics: Optional[Dict[str, Any]] = None
    checks: Optional[Dict[str, bool]] = None

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
    technologies: List[str]
    entry_points: List[Path]
    structure: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

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
    traceback: Optional[str] = None
    recovery_attempted: bool = False
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


# Type aliases for common patterns
ConfigDict = Dict[str, Any]
ErrorDict = Dict[str, str]
MetricsDict = Dict[str, Union[int, float, str]]
ValidationResult = Tuple[bool, Optional[List[str]]]
