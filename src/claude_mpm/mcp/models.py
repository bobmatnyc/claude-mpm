"""Data models for MCP session management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SessionStatus(Enum):
    """Status of a Claude MPM session."""

    STARTING = "starting"
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class SessionInfo:
    """Information about a Claude MPM session."""

    session_id: str
    status: SessionStatus
    start_time: str
    working_directory: str
    last_activity: str | None = None
    message_count: int = 0
    last_output: str | None = None


@dataclass
class SessionResult:
    """Result from a session operation."""

    success: bool
    session_id: str | None = None
    output: str | None = None
    error: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
