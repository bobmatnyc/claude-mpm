"""Session management endpoints for MPM Commander API.

This module implements REST endpoints for creating and managing tool sessions
(Claude Code, Aider, etc.) within projects.
"""

import logging
import subprocess  # nosec B404 - needed for tmux error handling
import uuid
from typing import List

from fastapi import APIRouter, Request, Response

from ...models import ToolSession
from ..errors import (
    InvalidRuntimeError,
    ProjectNotFoundError,
    SessionNotFoundError,
    TmuxNoSpaceError,
)
from ..schemas import CreateSessionRequest, SessionResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Valid runtime adapters (Phase 1: claude-code only)
VALID_RUNTIMES = {"claude-code"}


def _get_registry(request: Request):
    """Get registry instance from app.state."""
    if not hasattr(request.app.state, "registry") or request.app.state.registry is None:
        raise RuntimeError("Registry not initialized")
    return request.app.state.registry


def _get_tmux(request: Request):
    """Get tmux orchestrator instance from app.state."""
    if not hasattr(request.app.state, "tmux") or request.app.state.tmux is None:
        raise RuntimeError("Tmux orchestrator not initialized")
    return request.app.state.tmux


def _session_to_response(session: ToolSession) -> SessionResponse:
    """Convert ToolSession model to SessionResponse schema.

    Args:
        session: ToolSession instance

    Returns:
        SessionResponse with session data
    """
    return SessionResponse(
        id=session.id,
        project_id=session.project_id,
        runtime=session.runtime,
        tmux_target=session.tmux_target,
        status=session.status,
        created_at=session.created_at,
    )


@router.get("/projects/{project_id}/sessions", response_model=List[SessionResponse])
async def list_sessions(request: Request, project_id: str) -> List[SessionResponse]:
    """List all sessions for a project.

    Args:
        project_id: Unique project identifier

    Returns:
        List of session information (may be empty)

    Raises:
        ProjectNotFoundError: If project_id doesn't exist

    Example:
        GET /api/projects/abc-123/sessions
        Response: [
            {
                "id": "sess-456",
                "project_id": "abc-123",
                "runtime": "claude-code",
                "tmux_target": "%1",
                "status": "running",
                "created_at": "2025-01-12T10:00:00Z"
            }
        ]
    """
    registry = _get_registry(request)
    project = registry.get(project_id)

    if project is None:
        raise ProjectNotFoundError(project_id)

    # Convert sessions dict to list of responses
    return [_session_to_response(s) for s in project.sessions.values()]


@router.post(
    "/projects/{project_id}/sessions", response_model=SessionResponse, status_code=201
)
async def create_session(
    request: Request, project_id: str, req: CreateSessionRequest
) -> SessionResponse:
    """Create a new session for a project.

    Creates a new tmux pane and initializes the specified runtime adapter.

    Args:
        project_id: Unique project identifier
        req: Session creation request

    Returns:
        Newly created session information

    Raises:
        ProjectNotFoundError: If project_id doesn't exist
        InvalidRuntimeError: If runtime is not supported
        TmuxNoSpaceError: If tmux has no space for new pane

    Example:
        POST /api/projects/abc-123/sessions
        Body: {
            "runtime": "claude-code",
            "agent_prompt": "You are a helpful coding assistant"
        }
        Response: {
            "id": "sess-456",
            "project_id": "abc-123",
            "runtime": "claude-code",
            "tmux_target": "%1",
            "status": "initializing",
            "created_at": "2025-01-12T10:00:00Z"
        }
    """
    registry = _get_registry(request)
    tmux_orch = _get_tmux(request)

    # Validate project exists
    project = registry.get(project_id)
    if project is None:
        raise ProjectNotFoundError(project_id)

    # Validate runtime
    if req.runtime not in VALID_RUNTIMES:
        raise InvalidRuntimeError(req.runtime)

    # Generate session ID
    session_id = str(uuid.uuid4())

    # Create tmux pane for session
    try:
        tmux_target = tmux_orch.create_pane(
            pane_id=f"{project.name}-{req.runtime}",
            working_dir=project.path,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        if "no space for new pane" in stderr.lower():
            raise TmuxNoSpaceError() from None
        raise  # Re-raise other subprocess errors

    # Create session object
    session = ToolSession(
        id=session_id,
        project_id=project_id,
        runtime=req.runtime,
        tmux_target=tmux_target,
        status="initializing",
    )

    # Add session to project
    registry.add_session(project_id, session)

    # TODO: Start runtime adapter in pane (Phase 2)
    # For Phase 1, session stays in "initializing" state

    return _session_to_response(session)


@router.delete("/sessions/{session_id}", status_code=204)
async def stop_session(request: Request, session_id: str) -> Response:
    """Stop and remove a session.

    Kills the tmux pane and removes the session from its project.

    Args:
        session_id: Unique session identifier

    Returns:
        Empty response with 204 status

    Raises:
        SessionNotFoundError: If session_id doesn't exist

    Example:
        DELETE /api/sessions/sess-456
        Response: 204 No Content
    """
    registry = _get_registry(request)
    tmux_orch = _get_tmux(request)

    # Find session across all projects
    session = None
    parent_project_id = None

    for project in registry.list_all():
        if session_id in project.sessions:
            session = project.sessions[session_id]
            parent_project_id = project.id
            break

    if session is None or parent_project_id is None:
        raise SessionNotFoundError(session_id)

    # Kill tmux pane
    try:
        tmux_orch.kill_pane(session.tmux_target)
    except Exception as e:
        # Pane may already be dead, continue with cleanup
        logger.debug("Failed to kill pane (may already be dead): %s", e)

    # Remove session from project
    registry.remove_session(parent_project_id, session_id)

    return Response(status_code=204)
