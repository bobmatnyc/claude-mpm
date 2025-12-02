from pathlib import Path

"""Type definitions and utilities for Claude MPM.

This module provides common type aliases, protocols, and TypedDict definitions
used throughout the codebase to ensure consistent type safety.

WHY: Centralizing type definitions reduces duplication, improves IDE support,
and makes the codebase more maintainable by providing a single source of truth
for complex type definitions.

DESIGN DECISION: Uses protocols and TypedDict to provide structural typing
that allows for more flexible and maintainable type checking while maintaining
strict type safety.
"""

import logging
from datetime import datetime
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
)

from typing_extensions import NotRequired, TypeAlias, TypedDict

from claude_mpm.core.enums import OperationResult, ServiceState

# Generic type variables
T = TypeVar("T")
TSession = TypeVar("TSession")  # Generic session type
TAgent = TypeVar("TAgent")  # Generic agent type
TService = TypeVar("TService")  # Generic service type

# Basic type aliases
PathLike: TypeAlias = Union[str, Path]
JSONValue: TypeAlias = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONDict: TypeAlias = Dict[str, JSONValue]

Headers: TypeAlias = Dict[str, str]
ErrorCode: TypeAlias = Union[int, str]
LogLevel: TypeAlias = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Session types
SessionId: TypeAlias = str
SessionStatus: TypeAlias = ServiceState  # Replaced Literal with ServiceState enum
LaunchMethod: TypeAlias = Literal["exec", "subprocess", "oneshot"]


class SessionConfig(TypedDict):
    """Configuration for a Claude session."""

    session_id: SessionId
    launch_method: LaunchMethod
    working_dir: str
    enable_websocket: NotRequired[bool]
    websocket_port: NotRequired[int]
    enable_tickets: NotRequired[bool]
    claude_args: NotRequired[List[str]]
    context: NotRequired[str]
    system_prompt: NotRequired[str]


class SessionResult(TypedDict):
    """Result from a session execution."""

    success: bool
    session_id: SessionId
    response: NotRequired[str]
    error: NotRequired[str]
    execution_time: NotRequired[float]
    exit_code: NotRequired[int]
    metadata: NotRequired[Dict[str, Any]]


class SessionEvent(TypedDict):
    """Event logged during session execution."""

    event: str
    timestamp: datetime
    session_id: NotRequired[SessionId]
    success: NotRequired[bool]
    error: NotRequired[str]
    exception_type: NotRequired[str]
    metadata: NotRequired[Dict[str, Any]]


# Agent types
AgentId: TypeAlias = str
AgentVersion: TypeAlias = str
AgentTier: TypeAlias = Literal["SYSTEM", "USER", "PROJECT"]
ModelName: TypeAlias = str
ResourceTier: TypeAlias = Literal["standard", "premium", "enterprise"]


class AgentCapabilities(TypedDict):
    """Capabilities of an agent."""

    model: ModelName
    tools: NotRequired[List[str]]
    resource_tier: NotRequired[ResourceTier]
    max_tokens: NotRequired[int]
    temperature: NotRequired[float]
    system_prompt: NotRequired[str]


class AgentMetadata(TypedDict):
    """Metadata for an agent."""

    name: str
    description: str
    tags: NotRequired[List[str]]
    author: NotRequired[str]
    created_at: NotRequired[str]
    updated_at: NotRequired[str]


class AgentDefinition(TypedDict):
    """Complete agent definition."""

    agent_id: AgentId
    version: AgentVersion
    metadata: AgentMetadata
    capabilities: AgentCapabilities
    instructions: str
    tier: NotRequired[AgentTier]
    file_path: NotRequired[PathLike]


# WebSocket/SocketIO types
EventName: TypeAlias = str
EventData: TypeAlias = Dict[str, Any]
SocketId: TypeAlias = str


class WebSocketMessage(TypedDict):
    """WebSocket message structure."""

    event: EventName
    data: EventData
    timestamp: NotRequired[datetime]
    session_id: NotRequired[SessionId]


class ClaudeStatus(TypedDict):
    """Claude process status."""

    status: ServiceState  # Replaced Literal with ServiceState enum
    message: str
    timestamp: NotRequired[datetime]
    pid: NotRequired[int]


class DelegationInfo(TypedDict):
    """Agent delegation information."""

    agent: AgentId
    task: str
    status: OperationResult  # Replaced Literal with OperationResult enum
    timestamp: NotRequired[datetime]
    result: NotRequired[str]


# Hook types
HookName: TypeAlias = str
HookPriority: TypeAlias = int
HookResult: TypeAlias = Any


class HookConfig(TypedDict):
    """Hook configuration."""

    name: HookName
    enabled: NotRequired[bool]
    priority: NotRequired[HookPriority]
    config: NotRequired[Dict[str, Any]]


class HookContext(TypedDict):
    """Context passed to hook handlers."""

    hook_name: HookName
    session_id: NotRequired[SessionId]
    agent_id: NotRequired[AgentId]
    data: NotRequired[Dict[str, Any]]


# Service types
ServiceName: TypeAlias = str
ServiceStatus: TypeAlias = ServiceState  # Replaced Literal with ServiceState enum


class ServiceConfig(TypedDict):
    """Service configuration."""

    name: ServiceName
    enabled: NotRequired[bool]
    port: NotRequired[int]
    host: NotRequired[str]
    config: NotRequired[Dict[str, Any]]


class ServiceInfo(TypedDict):
    """Service information."""

    name: ServiceName
    status: ServiceStatus
    uptime: NotRequired[float]
    requests_handled: NotRequired[int]
    errors: NotRequired[int]
    last_error: NotRequired[str]


# Memory types
MemoryType: TypeAlias = Literal[
    "pattern",
    "architecture",
    "guideline",
    "mistake",
    "strategy",
    "integration",
    "performance",
    "context",
]
MemoryId: TypeAlias = str


class Memory(TypedDict):
    """Agent memory entry."""

    id: MemoryId
    type: MemoryType
    content: str
    agent_id: AgentId
    timestamp: datetime
    relevance_score: NotRequired[float]
    usage_count: NotRequired[int]
    tags: NotRequired[List[str]]


class MemorySearchResult(TypedDict):
    """Result from memory search."""

    memory: Memory
    score: float
    matches: NotRequired[List[str]]


# Project and deployment types
class ProjectConfig(TypedDict):
    """Project-specific configuration."""

    project_name: NotRequired[str]
    agent_deployment: NotRequired[Dict[str, Any]]
    excluded_agents: NotRequired[List[AgentId]]
    included_agents: NotRequired[List[AgentId]]
    custom_agents_path: NotRequired[PathLike]
    memory_enabled: NotRequired[bool]
    websocket_enabled: NotRequired[bool]


class DeploymentResult(TypedDict):
    """Result from agent deployment."""

    deployed: List[AgentId]
    failed: List[Tuple[AgentId, str]]
    skipped: List[AgentId]
    total_time: float


# Response logging types
class ResponseLogEntry(TypedDict):
    """Entry in response log."""

    timestamp: datetime
    request_summary: str
    response_content: str
    metadata: Dict[str, Any]
    agent: AgentId
    session_id: NotRequired[SessionId]
    execution_time: NotRequired[float]


# Command/CLI types
CommandName: TypeAlias = str
CommandArgs: TypeAlias = List[str]


class CommandResult(TypedDict):
    """Result from command execution."""

    success: bool
    output: NotRequired[str]
    error: NotRequired[str]
    exit_code: int


# Protocols for structural typing


class SessionProtocol(Protocol):
    """Protocol for session handlers."""

    def initialize_session(self, prompt: str) -> Tuple[bool, Optional[str]]:
        """Initialize the session."""
        ...

    def execute_command(
        self, prompt: str, context: Optional[str], infrastructure: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Execute a command."""
        ...

    def cleanup_session(self) -> None:
        """Clean up the session."""
        ...


class LoggerProtocol(Protocol):
    """Protocol for loggers."""

    def log_system(
        self, message: str, level: LogLevel = "INFO", component: Optional[str] = None
    ) -> None:
        """Log a system message."""
        ...

    def log_agent(self, agent: AgentId, message: str, level: LogLevel = "INFO") -> None:
        """Log an agent message."""
        ...

    def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        ...


class WebSocketServerProtocol(Protocol):
    """Protocol for WebSocket server."""

    def start(self) -> None:
        """Start the server."""
        ...

    def session_started(
        self, session_id: SessionId, launch_method: LaunchMethod, working_dir: str
    ) -> None:
        """Notify session start."""
        ...

    def session_ended(self) -> None:
        """Notify session end."""
        ...

    def claude_status_changed(self, status: str, message: str) -> None:
        """Update Claude status."""
        ...

    def claude_output(self, output: str, stream: Literal["stdout", "stderr"]) -> None:
        """Send Claude output."""
        ...

    def agent_delegated(self, agent: AgentId, task: str, status: str) -> None:
        """Notify agent delegation."""
        ...


class AgentServiceProtocol(Protocol):
    """Protocol for agent service."""

    def deploy_agents(
        self, agents: List[AgentDefinition], target_dir: PathLike
    ) -> DeploymentResult:
        """Deploy agents to target directory."""
        ...

    def discover_agents(self, tier: AgentTier) -> List[AgentDefinition]:
        """Discover agents at specified tier."""
        ...

    def get_agent(
        self, agent_id: AgentId, tier: Optional[AgentTier] = None
    ) -> Optional[AgentDefinition]:
        """Get specific agent."""
        ...


class MemoryServiceProtocol(Protocol):
    """Protocol for memory service."""

    def add_memory(self, memory: Memory) -> bool:
        """Add a memory entry."""
        ...

    def search_memories(
        self,
        query: str,
        agent_id: Optional[AgentId] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
    ) -> List[MemorySearchResult]:
        """Search memories."""
        ...

    def get_relevant_memories(
        self, context: str, agent_id: AgentId, limit: int = 5
    ) -> List[Memory]:
        """Get relevant memories for context."""
        ...


# Factory function types
SessionFactory = Callable[[Any], SessionProtocol]
ServiceFactory = Callable[[ServiceConfig], Any]
LoggerFactory = Callable[[str], logging.Logger]

# Validation function types
Validator = Callable[[Any], bool]
Transformer = Callable[[T], T]
ErrorHandler = Callable[[Exception], None]

# Async types for future use
AsyncSessionResult = Awaitable[SessionResult]
AsyncCommandResult = Awaitable[CommandResult]
AsyncDeploymentResult = Awaitable[DeploymentResult]


# Container/Dependency injection types
class ServiceContainer(Protocol):
    """Protocol for service container."""

    def register(self, name: str, factory: ServiceFactory) -> None:
        """Register a service."""
        ...

    def get(self, name: str) -> Any:
        """Get a service instance."""
        ...

    def has(self, name: str) -> bool:
        """Check if service is registered."""
        ...


# Event system types
EventHandler = Callable[[EventData], None]
EventFilter = Callable[[EventData], bool]


class EventSubscription(TypedDict):
    """Event subscription details."""

    event: EventName
    handler: EventHandler
    filter: NotRequired[EventFilter]
    priority: NotRequired[int]


# Testing types (for test files)
class TestFixture(TypedDict):
    """Test fixture data."""

    name: str
    data: Any
    setup: NotRequired[Callable[[], None]]
    teardown: NotRequired[Callable[[], None]]


# Export commonly used type combinations
CommonTypes = Union[str, int, float, bool, None, List[Any], Dict[str, Any]]
ConfigDict = Dict[str, CommonTypes]
ErrorResult = Tuple[bool, Optional[str]]
SuccessResult = Tuple[bool, Any]

__all__ = [
    "AgentCapabilities",
    "AgentDefinition",
    # Agent types
    "AgentId",
    "AgentMetadata",
    "AgentServiceProtocol",
    "AgentTier",
    "AgentVersion",
    "ClaudeStatus",
    "CommandArgs",
    "CommandName",
    "CommandResult",
    # Common combinations
    "CommonTypes",
    "ConfigDict",
    "DelegationInfo",
    "DeploymentResult",
    "ErrorCode",
    "ErrorResult",
    "EventData",
    # WebSocket types
    "EventName",
    "Headers",
    "HookConfig",
    "HookContext",
    # Hook types
    "HookName",
    "HookPriority",
    "HookResult",
    "JSONDict",
    "JSONValue",
    "LaunchMethod",
    "LogLevel",
    "LoggerProtocol",
    "Memory",
    "MemoryId",
    "MemorySearchResult",
    "MemoryServiceProtocol",
    # Memory types
    "MemoryType",
    "ModelName",
    # Basic type aliases
    "PathLike",
    # Other types
    "ProjectConfig",
    "ResourceTier",
    "ResponseLogEntry",
    "ServiceConfig",
    "ServiceContainer",
    "ServiceInfo",
    # Service types
    "ServiceName",
    "ServiceStatus",
    "SessionConfig",
    "SessionEvent",
    # Session types
    "SessionId",
    # Protocols
    "SessionProtocol",
    "SessionResult",
    "SessionStatus",
    "SocketId",
    "SuccessResult",
    # Generic type variables
    "T",
    "TAgent",
    "TService",
    "TSession",
    "WebSocketMessage",
    "WebSocketServerProtocol",
]
