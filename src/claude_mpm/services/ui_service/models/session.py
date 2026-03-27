"""Pydantic models for session management."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SessionStatus(str, Enum):
    """Lifecycle status of a managed Claude session."""

    starting = "starting"
    idle = "idle"
    busy = "busy"
    compacting = "compacting"
    terminated = "terminated"


class SessionCreate(BaseModel):
    """Request body for creating a new session.

    Attributes:
        resume_id: Optional Claude session ID to resume.
        model: Claude model to use (e.g. 'claude-opus-4-5').
        bare: Pass --bare flag to suppress system prompt.
        cwd: Working directory for the subprocess.
        permission_mode: Initial permission mode (default, acceptEdits, etc.).
        project_root: Optional project root directory; used as cwd default when
            cwd is not explicitly set.
    """

    model_config = ConfigDict(from_attributes=True)

    resume_id: str | None = Field(None, description="Claude session ID to resume")
    model: str | None = Field(None, description="Claude model identifier")
    bare: bool = Field(False, description="Pass --bare to claude CLI")
    cwd: str | None = Field(None, description="Working directory for subprocess")
    permission_mode: str = Field("default", description="Initial permission mode")
    project_root: str | None = Field(None, description="Project root directory")


class SessionUpdate(BaseModel):
    """Request body for updating a session's mutable properties.

    Attributes:
        model: New model to use (applies to next message).
        permission_mode: Updated permission mode.
        output_format: Output format override.
    """

    model_config = ConfigDict(from_attributes=True)

    model: str | None = None
    permission_mode: str | None = None
    output_format: str | None = None


class ManagedSessionState(BaseModel):
    """Public view of a managed session's state.

    Attributes:
        id: UI service session UUID.
        claude_session_id: Underlying Claude session ID (for --resume).
        status: Current lifecycle status.
        model: Active model identifier.
        cwd: Working directory.
        project_root: Project root directory (may differ from cwd).
        created_at: Session creation timestamp.
        last_activity: Timestamp of last input/output.
        context_tokens_used: Tokens consumed in current context window.
        context_tokens_total: Total context window capacity.
        context_percent_used: Percentage of context window used.
        permission_mode: Active permission mode.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    claude_session_id: str | None = None
    status: SessionStatus = SessionStatus.idle
    model: str = "claude-opus-4-5"
    cwd: str = "."
    project_root: str | None = None
    created_at: datetime
    last_activity: datetime
    context_tokens_used: int = 0
    context_tokens_total: int = 200000
    context_percent_used: float = 0.0
    permission_mode: str = "default"
