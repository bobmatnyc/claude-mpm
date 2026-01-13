"""Project data models for MPM Commander.

This module defines the core data structures for managing projects,
tool sessions, and conversation threads.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _utc_now() -> datetime:
    """Return current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


class ProjectState(Enum):
    """Project execution state.

    Attributes:
        IDLE: No pending work in queue
        WORKING: Currently executing a work item
        BLOCKED: Waiting on human input or approval
        PAUSED: Manually paused by user
        ERROR: Encountered unrecoverable error
    """

    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class ToolSession:
    """Tool runtime session (Claude Code, Codex, Aider, etc.).

    Each session runs in an isolated tmux pane for output capture.

    Attributes:
        id: Unique session identifier
        project_id: Parent project ID
        runtime: Tool runtime name (e.g., "claude-code", "aider")
        tmux_target: Tmux window:pane identifier (e.g., "commander:proj-a-cc")
        status: Current session status
        output_buffer: Captured output from tool
        created_at: Session creation timestamp
        last_output_at: Last output received timestamp

    Example:
        >>> session = ToolSession(
        ...     id="sess-123",
        ...     project_id="proj-abc",
        ...     runtime="claude-code",
        ...     tmux_target="commander:proj-abc-cc"
        ... )
        >>> session.status
        'initializing'
    """

    id: str
    project_id: str
    runtime: str
    tmux_target: str
    status: str = "initializing"
    output_buffer: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    last_output_at: Optional[datetime] = None


@dataclass
class ThreadMessage:
    """Conversation thread message.

    Represents a single message in the project's conversation history,
    which can come from user, assistant, system, or tool outputs.

    Attributes:
        id: Unique message identifier
        role: Message sender role
        content: Message content
        session_id: Associated tool session (if from tool)
        event_id: Associated event (Phase 2)
        timestamp: Message creation timestamp

    Example:
        >>> msg = ThreadMessage(
        ...     id="msg-1",
        ...     role="user",
        ...     content="Fix the login bug"
        ... )
        >>> msg.role
        'user'
    """

    id: str
    role: str  # user, assistant, system, tool
    content: str
    session_id: Optional[str] = None
    event_id: Optional[str] = None
    timestamp: datetime = field(default_factory=_utc_now)


@dataclass
class Project:
    """Project context and state management.

    Maintains isolated state for a single project including:
    - Execution state and work queue
    - Tool sessions (Claude Code, Aider, etc.)
    - Conversation thread
    - Events and history (Phase 2)

    Attributes:
        id: Unique project identifier (UUID)
        path: Absolute filesystem path to project
        name: Human-readable project name
        state: Current execution state
        state_reason: Optional reason for state (e.g., error message)
        config_loaded: Whether .claude-mpm/ config loaded
        config: Loaded configuration dict
        sessions: Active tool sessions by session_id
        work_queue: Pending work items (Phase 3)
        active_work: Currently executing work item
        completed_work: History of completed work items
        pending_events: Events pending processing (Phase 2)
        event_history: Processed events (Phase 2)
        thread: Conversation message history
        created_at: Project registration timestamp
        last_activity: Last activity timestamp (updated on any change)

    Example:
        >>> from pathlib import Path
        >>> project = Project(
        ...     id="proj-abc123",
        ...     path="/Users/masa/Projects/my-app",
        ...     name="my-app"
        ... )
        >>> project.state
        <ProjectState.IDLE: 'idle'>
        >>> project.state = ProjectState.WORKING
        >>> project.state_reason = "Processing ticket #123"
    """

    id: str
    path: str
    name: str
    state: ProjectState = ProjectState.IDLE
    state_reason: Optional[str] = None
    config_loaded: bool = False
    config: Optional[Dict[str, Any]] = None
    sessions: Dict[str, ToolSession] = field(default_factory=dict)
    work_queue: List[Any] = field(default_factory=list)
    active_work: Optional[Any] = None
    completed_work: List[Any] = field(default_factory=list)
    pending_events: List[Any] = field(default_factory=list)
    event_history: List[Any] = field(default_factory=list)
    thread: List[ThreadMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)
    last_activity: datetime = field(default_factory=_utc_now)
