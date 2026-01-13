"""Pydantic request/response schemas for MPM Commander API.

This module defines all request and response models for the REST API,
providing type safety and automatic validation.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# Request Models


class RegisterProjectRequest(BaseModel):
    """Request to register a new project.

    Attributes:
        path: Filesystem path to project directory
        name: Optional display name (derived from path if omitted)
    """

    path: str = Field(..., description="Filesystem path to project")
    name: Optional[str] = Field(
        None, description="Display name (derived from path if omitted)"
    )


class CreateSessionRequest(BaseModel):
    """Request to create a new tool session.

    Attributes:
        runtime: Runtime adapter to use (e.g., "claude-code")
        agent_prompt: Optional custom system prompt for the agent
    """

    runtime: str = Field("claude-code", description="Runtime adapter to use")
    agent_prompt: Optional[str] = Field(None, description="Custom system prompt")


class SendMessageRequest(BaseModel):
    """Request to send a message to a project.

    Attributes:
        content: Message content
        session_id: Target session ID (uses active session if omitted)
    """

    content: str = Field(..., description="Message content")
    session_id: Optional[str] = Field(
        None, description="Target session (uses active if omitted)"
    )


# Response Models


class SessionResponse(BaseModel):
    """Session information response.

    Attributes:
        id: Unique session identifier
        project_id: Parent project ID
        runtime: Runtime adapter name
        tmux_target: Tmux pane target identifier
        status: Current session status
        created_at: Session creation timestamp
    """

    id: str
    project_id: str
    runtime: str
    tmux_target: str
    status: str
    created_at: datetime


class ProjectResponse(BaseModel):
    """Project information response.

    Attributes:
        id: Unique project identifier
        path: Absolute filesystem path
        name: Display name
        state: Current project state
        state_reason: Optional state reason (e.g., error message)
        sessions: List of active sessions
        pending_events_count: Number of pending events
        last_activity: Last activity timestamp
        created_at: Project registration timestamp
    """

    id: str
    path: str
    name: str
    state: str
    state_reason: Optional[str]
    sessions: List[SessionResponse]
    pending_events_count: int
    last_activity: datetime
    created_at: datetime


class MessageResponse(BaseModel):
    """Conversation message response.

    Attributes:
        id: Unique message identifier
        role: Message sender role (user, assistant, system, tool)
        content: Message content
        session_id: Associated session ID (if from tool)
        timestamp: Message creation timestamp
    """

    id: str
    role: str
    content: str
    session_id: Optional[str]
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response with structured error information.

    Attributes:
        error: Error details with code and message
    """

    error: dict  # {code: str, message: str}
