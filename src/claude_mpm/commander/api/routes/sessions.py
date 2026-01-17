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

    return {"synced": len(results), "results": results}


@router.post("/sessions/{session_id}/open-terminal")
async def open_session_in_terminal(session_id: str, terminal: str = "iterm"):
    """Open the session's tmux window in the specified terminal.

    Uses AppleScript (macOS) to open the terminal and attach to the tmux session.

    Args:
        session_id: Unique session identifier
        terminal: Terminal to use (iterm, terminal, warp, alacritty, kitty)

    Returns:
        Success status

    Raises:
        SessionNotFoundError: If session_id doesn't exist
    """
    import subprocess  # nosec B404 - required for osascript

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

    # Get the pane target from session (e.g., "%26" for pane ID)
    pane_target = session.tmux_target if session.tmux_target else None

    if not pane_target:
        raise SessionNotFoundError(f"Session {session_id} has no tmux_target")

    # Convert pane ID to window target (e.g., "%26" -> "mpm-commander2:17")
    # This is needed because select-window works with window targets, not pane IDs
    try:
        result = subprocess.run(  # nosec B603 B607 - trusted tmux command
            [
                "tmux",
                "display",
                "-p",
                "-t",
                pane_target,
                "#{session_name}:#{window_index}",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        window_target = result.stdout.strip()
        session_name = window_target.split(":")[0]
        logger.info(f"Resolved pane {pane_target} to window {window_target}")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to resolve pane {pane_target}: {e}")
        # Fallback: use pane_target directly (might work for some targets)
        window_target = pane_target
        session_name = tmux_orch.session_name

    # Open terminal and attach - select-window is ONLY in the attach command
    # This ensures existing attached terminals are NOT affected
    tmux_cmd = f"tmux attach -t {session_name} \\\\; select-window -t {window_target}"

    # Terminal-specific AppleScripts
    applescripts = {
        "iterm": f"""
            tell application "iTerm"
                activate
                create window with default profile
                tell current session of current window
                    write text "{tmux_cmd}"
                end tell
            end tell
        """,
        "terminal": f"""
            tell application "Terminal"
                activate
                do script "{tmux_cmd}"
            end tell
        """,
        "warp": f"""
            tell application "Warp"
                activate
            end tell
            delay 0.5
            tell application "System Events"
                tell process "Warp"
                    keystroke "{tmux_cmd}"
                    keystroke return
                end tell
            end tell
        """,
        "alacritty": f"""
            do shell script "open -a Alacritty"
            delay 0.5
            tell application "System Events"
                tell process "Alacritty"
                    keystroke "{tmux_cmd}"
                    keystroke return
                end tell
            end tell
        """,
        "kitty": f"""
            do shell script "open -a Kitty"
            delay 0.5
            tell application "System Events"
                tell process "kitty"
                    keystroke "{tmux_cmd}"
                    keystroke return
                end tell
            end tell
        """,
    }

    applescript = applescripts.get(terminal, applescripts["iterm"])

    try:
        subprocess.run(  # nosec B603 B607 - trusted osascript command
            ["osascript", "-e", applescript], check=True, capture_output=True
        )
        return {
            "status": "opened",
            "session_id": session_id,
            "terminal": terminal,
            "pane_target": pane_target,
            "window_target": window_target,
        }
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to open {terminal} for session {session_id}: {e}")
        return {
            "status": "error",
            "terminal": terminal,
            "error": str(e.stderr.decode() if e.stderr else e),
        }


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

    return {"session_id": session_id, "output": output, "lines": lines}


# ============================================================================
# Activity Tracking Endpoints
# ============================================================================


def _get_activity_tracker():
    """Get activity tracker instance from app global."""
    from ..app import activity_tracker

    if activity_tracker is None:
        raise RuntimeError("Activity tracker not initialized")
    return activity_tracker


@router.get("/sessions/{session_id}/activity")
async def get_session_activity(session_id: str):
    """Get activity metrics for a session.

    Returns real-time metrics for monitoring agent state:
    - total_lines: Total lines in scrollback
    - lines_since_prompt: New lines since last user prompt
    - seconds_since_change: Time since last output
    - seconds_since_prompt: Time since last user input
    - last_user_input: The last prompt sent by user
    - last_agent_output: Last agent response OR "working..." if active
    - status: Derived status (active/thinking/stalled/finished/idle)

    Args:
        session_id: Unique session identifier

    Returns:
        Activity metrics dict

    Example:
        GET /api/sessions/sess-456/activity
        Response: {
            "total_lines": 1523,
            "lines_since_prompt": 45,
            "seconds_since_change": 2.3,
            "seconds_since_prompt": 15.7,
            "last_user_input": "Explain Python decorators",
            "last_agent_output": "working...",
            "is_working": true,
            "status": "active"
        }
    """
    tracker = _get_activity_tracker()
    registry = _get_registry()

    # Find session to verify it exists and get tmux_target
    session = None
    for project in registry.list_all():
        if session_id in project.sessions:
            session = project.sessions[session_id]
            break

    if session is None:
        raise SessionNotFoundError(session_id)

    # Auto-register session if not tracked yet
    stats = tracker.get_stats(session_id)
    if stats is None:
        tracker.register_session(session_id, session.tmux_target)
        stats = tracker.get_stats(session_id)

    return {"session_id": session_id, **stats}


@router.get("/sessions/activity/all")
async def get_all_sessions_activity():
    """Get activity metrics for all tracked sessions.

    Returns:
        Dict mapping session_id to activity metrics

    Example:
        GET /api/sessions/activity/all
        Response: {
            "sessions": {
                "sess-123": {...activity metrics...},
                "sess-456": {...activity metrics...}
            },
            "count": 2
        }
    """
    tracker = _get_activity_tracker()

    all_stats = tracker.get_all_stats()
    return {"sessions": all_stats, "count": len(all_stats)}


@router.post("/sessions/{session_id}/activity/prompt")
async def record_user_prompt(session_id: str, prompt: str):
    """Record a user prompt event (for hook integration).

    This endpoint is called by the Claude Code hook system when
    a UserPromptSubmit event occurs.

    Args:
        session_id: Unique session identifier
        prompt: The user's prompt text

    Returns:
        Updated activity stats
    """
    tracker = _get_activity_tracker()
    registry = _get_registry()

    # Find session to get tmux_target
    session = None
    for project in registry.list_all():
        if session_id in project.sessions:
            session = project.sessions[session_id]
            break

    if session is None:
        raise SessionNotFoundError(session_id)

    tracker.on_user_prompt(session_id, session.tmux_target, prompt)

    return {
        "status": "recorded",
        "session_id": session_id,
        **tracker.get_stats(session_id),
    }


@router.post("/sessions/{session_id}/activity/stop")
async def record_agent_stop(session_id: str, response: str = ""):
    """Record an agent stop event (for hook integration).

    This endpoint is called by the Claude Code hook system when
    a Stop event occurs (agent finished responding).

    Args:
        session_id: Unique session identifier
        response: The agent's response text (optional)

    Returns:
        Updated activity stats
    """
    tracker = _get_activity_tracker()

    stats = tracker.get_stats(session_id)
    if stats is None:
        raise SessionNotFoundError(session_id)

    tracker.on_agent_stop(session_id, response)

    return {
        "status": "recorded",
        "session_id": session_id,
        **tracker.get_stats(session_id),
    }
