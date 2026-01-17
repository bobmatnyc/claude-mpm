"""Session management endpoints for MPM Commander API.

This module implements REST endpoints for creating and managing tool sessions
(Claude Code, Aider, etc.) within projects.
"""

import logging
import uuid
from typing import List

from fastapi import APIRouter, Response

from ...models import ToolSession
from ..errors import InvalidRuntimeError, ProjectNotFoundError, SessionNotFoundError
from ..schemas import CreateSessionRequest, SessionResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Valid runtime adapters (Phase 1: claude-code only)
VALID_RUNTIMES = {"claude-code"}


def _get_registry():
    """Get registry instance from app global."""
    from ..app import registry

    if registry is None:
        raise RuntimeError("Registry not initialized")
    return registry


def _get_tmux():
    """Get tmux orchestrator instance from app global."""
    from ..app import tmux

    if tmux is None:
        raise RuntimeError("Tmux orchestrator not initialized")
    return tmux


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
async def list_sessions(project_id: str) -> List[SessionResponse]:
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
    registry = _get_registry()
    project = registry.get(project_id)

    if project is None:
        raise ProjectNotFoundError(project_id)

    # Convert sessions dict to list of responses
    return [_session_to_response(s) for s in project.sessions.values()]


@router.post(
    "/projects/{project_id}/sessions", response_model=SessionResponse, status_code=201
)
async def create_session(project_id: str, req: CreateSessionRequest) -> SessionResponse:
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
    registry = _get_registry()
    tmux_orch = _get_tmux()

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
    tmux_target = tmux_orch.create_pane(
        pane_id=f"{project.name}-{req.runtime}",
        working_dir=project.path,
    )

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
async def stop_session(session_id: str) -> Response:
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
    registry = _get_registry()
    tmux_orch = _get_tmux()

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


@router.post("/sessions/sync")
async def sync_sessions():
    """Synchronize sessions with tmux windows.

    Checks which tmux windows exist and updates session status accordingly.
    Sessions with missing windows are marked as 'stopped'.

    Returns:
        Sync results with status for each session

    Example:
        POST /api/sessions/sync
        Response: {
            "synced": 3,
            "results": {
                "my-project-claude-code": "found",
                "old-project-claude-code": "missing"
            }
        }
    """
    registry = _get_registry()
    tmux_orch = _get_tmux()

    results = tmux_orch.sync_windows_with_registry(registry)

    return {
        "synced": len(results),
        "results": results
    }


@router.post("/sessions/{session_id}/open-iterm")
async def open_session_in_iterm(session_id: str):
    """Open the session's tmux window in iTerm.

    Uses AppleScript to open iTerm and attach to the tmux session.

    Args:
        session_id: Unique session identifier

    Returns:
        Success status

    Raises:
        SessionNotFoundError: If session_id doesn't exist
    """
    import subprocess

    registry = _get_registry()
    tmux_orch = _get_tmux()

    # Find session across all projects
    session = None
    for project in registry.list_all():
        if session_id in project.sessions:
            session = project.sessions[session_id]
            break

    if session is None:
        raise SessionNotFoundError(session_id)

    # AppleScript to open iTerm and attach to tmux session
    applescript = f'''
    tell application "iTerm"
        activate
        create window with default profile
        tell current session of current window
            write text "tmux attach -t {tmux_orch.session_name}"
        end tell
    end tell
    '''

    try:
        subprocess.run(["osascript", "-e", applescript], check=True, capture_output=True)  # nosec B603
        return {"status": "opened", "session_id": session_id, "tmux_session": tmux_orch.session_name}
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to open iTerm for session {session_id}: {e}")
        return {"status": "error", "error": str(e.stderr.decode() if e.stderr else e)}


@router.post("/sessions/{session_id}/keys")
async def send_keys_to_session(session_id: str, keys: str, enter: bool = True):
    """Send keystrokes to a session's tmux pane.

    Args:
        session_id: Unique session identifier
        keys: Keys to send (use special values: "C-c" for Ctrl+C, "Escape" for ESC)
        enter: Whether to send Enter after keys (default: True)

    Returns:
        Success status

    Raises:
        SessionNotFoundError: If session_id doesn't exist

    Example:
        POST /api/sessions/sess-456/keys?keys=hello&enter=true
    """
    registry = _get_registry()
    tmux_orch = _get_tmux()

    # Find session across all projects
    session = None
    for project in registry.list_all():
        if session_id in project.sessions:
            session = project.sessions[session_id]
            break

    if session is None:
        raise SessionNotFoundError(session_id)

    # Send keys to tmux
    try:
        tmux_orch.send_keys(session.tmux_target, keys, enter=enter)
        return {"status": "sent", "keys": keys, "enter": enter}
    except Exception as e:
        logger.warning(f"Failed to send keys to session {session_id}: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/sessions/{session_id}/output")
async def get_session_output(session_id: str, lines: int = 100):
    """Get terminal output from a session.

    Captures the recent output from the session's tmux pane.

    Args:
        session_id: Unique session identifier
        lines: Number of lines to capture (default: 100)

    Returns:
        Session output and metadata

    Raises:
        SessionNotFoundError: If session_id doesn't exist

    Example:
        GET /api/sessions/sess-456/output?lines=50
        Response: {
            "session_id": "sess-456",
            "output": "$ claude\\nHello! How can I help?\\n",
            "lines": 50
        }
    """
    registry = _get_registry()
    tmux_orch = _get_tmux()

    # Find session across all projects
    session = None
    for project in registry.list_all():
        if session_id in project.sessions:
            session = project.sessions[session_id]
            break

    if session is None:
        raise SessionNotFoundError(session_id)

    # Capture output from tmux pane
    try:
        output = tmux_orch.capture_output(session.tmux_target, lines=lines)
    except Exception as e:
        logger.warning(f"Failed to capture output for session {session_id}: {e}")
        output = f"[Error capturing output: {e}]"

    return {
        "session_id": session_id,
        "output": output,
        "lines": lines
    }
