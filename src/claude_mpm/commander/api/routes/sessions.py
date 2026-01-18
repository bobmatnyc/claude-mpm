"""Session management endpoints for MPM Commander API.

This module implements REST endpoints for creating and managing tool sessions
(Claude Code, Aider, etc.) within projects.
"""

import asyncio
import json
import logging
import subprocess  # nosec B404 - required for tmux/osascript commands
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Response, WebSocket, WebSocketDisconnect

from ...models import ToolSession
from ..errors import (
    InvalidRuntimeError,
    ProjectNotFoundError,
    SessionNotFoundError,
    TmuxNoSpaceError,
)
from ..schemas import CreateSessionRequest, SessionResponse

# Type alias for JSON-serializable response dictionaries
JsonResponse = Dict[str, Any]

router = APIRouter()
logger = logging.getLogger(__name__)

# Valid runtime adapters (Phase 1: claude-code only)
VALID_RUNTIMES = {"claude-code"}

# Tmux session configuration
TMUX_MAIN_SESSION = "mpm-commander"
TMUX_COMMAND_TIMEOUT = 2  # seconds


def _get_registry() -> Any:
    """Get registry instance from app global.

    Returns:
        ProjectRegistry instance

    Raises:
        RuntimeError: If registry is not initialized
    """
    from ..app import registry

    if registry is None:
        raise RuntimeError("Registry not initialized")
    return registry


def _get_tmux() -> Any:
    """Get tmux orchestrator instance from app global.

    Returns:
        TmuxOrchestrator instance

    Raises:
        RuntimeError: If tmux orchestrator is not initialized
    """
    from ..app import tmux

    if tmux is None:
        raise RuntimeError("Tmux orchestrator not initialized")
    return tmux


def _find_session(session_id: str) -> Tuple[Optional[ToolSession], Optional[str]]:
    """Find a session across all projects.

    Args:
        session_id: Unique session identifier

    Returns:
        Tuple of (session, project_id) or (None, None) if not found
    """
    registry = _get_registry()
    for project in registry.list_all():
        if session_id in project.sessions:
            return project.sessions[session_id], project.id
    return None, None


def _get_session_or_raise(session_id: str) -> ToolSession:
    """Get a session or raise SessionNotFoundError.

    Args:
        session_id: Unique session identifier

    Returns:
        The ToolSession instance

    Raises:
        SessionNotFoundError: If session doesn't exist
    """
    session, _ = _find_session(session_id)
    if session is None:
        raise SessionNotFoundError(session_id)
    return session


@dataclass
class TmuxWindowTarget:
    """Represents a tmux window target with session and index."""

    session_name: str
    window_index: str

    @classmethod
    def from_pane_id(cls, pane_id: str) -> "TmuxWindowTarget":
        """Resolve a pane ID to its window target in the main session.

        Uses list-windows to search for the pane, avoiding the issue where
        tmux display returns client-session names instead of the main session.

        Args:
            pane_id: Tmux pane identifier (e.g., "%26")

        Returns:
            TmuxWindowTarget with session name and window index
        """
        try:
            result = subprocess.run(  # nosec B603 B607 - trusted tmux command
                [
                    "tmux",
                    "list-windows",
                    "-t",
                    TMUX_MAIN_SESSION,
                    "-F",
                    "#{window_index}:#{pane_id}",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=TMUX_COMMAND_TIMEOUT,
            )

            # Find the window containing our pane
            for line in result.stdout.strip().split("\n"):
                if pane_id in line:
                    window_index = line.split(":")[0]
                    logger.debug(
                        "Resolved pane %s to window %s:%s",
                        pane_id,
                        TMUX_MAIN_SESSION,
                        window_index,
                    )
                    return cls(
                        session_name=TMUX_MAIN_SESSION, window_index=window_index
                    )

            logger.warning(
                "Pane %s not found in %s, using window 0", pane_id, TMUX_MAIN_SESSION
            )

        except subprocess.CalledProcessError as e:
            logger.warning("Failed to list tmux windows: %s", e)
        except subprocess.TimeoutExpired:
            logger.warning("Timeout listing tmux windows")

        # Fallback to first window
        return cls(session_name=TMUX_MAIN_SESSION, window_index="0")

    def __str__(self) -> str:
        """Return the full target string (e.g., 'mpm-commander:1')."""
        return f"{self.session_name}:{self.window_index}"


def _build_tmux_grouped_session_command(target: TmuxWindowTarget) -> str:
    """Build a tmux command that creates a grouped session with correct window.

    Grouped sessions share windows with the main session but maintain independent
    active window state. This prevents multiple terminal windows from interfering
    with each other's window selection.

    IMPORTANT: The tmux `new-session -A -t SESSION:WINDOW` command ignores the
    window index and always opens window 0. We must use three separate commands:
    1. Create the grouped session detached (-d)
    2. Select the correct window
    3. Attach to the session

    Args:
        target: TmuxWindowTarget specifying the window to open

    Returns:
        Shell command string that creates and attaches to the grouped session
    """
    client_id = f"client-{uuid.uuid4().hex[:8]}"

    return (
        f"tmux new-session -d -t {target.session_name} -s {client_id} && "
        f"tmux select-window -t {client_id}:{target.window_index} && "
        f"tmux attach -t {client_id}"
    )


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
async def sync_sessions() -> JsonResponse:
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


def _get_applescript_for_terminal(terminal: str, tmux_cmd: str) -> str:
    """Get the AppleScript to open a terminal and run a tmux command.

    Args:
        terminal: Terminal name (iterm, terminal, warp, alacritty, kitty)
        tmux_cmd: The tmux command to execute

    Returns:
        AppleScript string for the specified terminal
    """
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
    return applescripts.get(terminal, applescripts["iterm"])


@router.post("/sessions/{session_id}/open-terminal")
async def open_session_in_terminal(
    session_id: str, terminal: str = "iterm"
) -> JsonResponse:
    """Open the session's tmux window in the specified terminal.

    Creates a grouped tmux session that shares windows with the main session
    but maintains independent active window state. This prevents multiple
    terminal windows from interfering with each other's window selection.

    Args:
        session_id: Unique session identifier
        terminal: Terminal to use (iterm, terminal, warp, alacritty, kitty)

    Returns:
        dict: Success status with session details, or error information

    Raises:
        SessionNotFoundError: If session_id doesn't exist or has no tmux_target

    Example:
        POST /api/sessions/sess-456/open-terminal?terminal=iterm
        Response: {
            "status": "opened",
            "session_id": "sess-456",
            "terminal": "iterm",
            "pane_target": "%26",
            "window_target": "mpm-commander:1"
        }
    """
    session = _get_session_or_raise(session_id)

    pane_target = session.tmux_target
    if not pane_target:
        raise SessionNotFoundError(f"Session {session_id} has no tmux_target")

    # Resolve pane ID to window target
    window_target = TmuxWindowTarget.from_pane_id(pane_target)
    logger.info(
        "Opening terminal for session %s: pane=%s, window=%s",
        session_id,
        pane_target,
        window_target,
    )

    # Build the tmux command for grouped session
    tmux_cmd = _build_tmux_grouped_session_command(window_target)

    # Get and execute terminal-specific AppleScript
    applescript = _get_applescript_for_terminal(terminal, tmux_cmd)

    try:
        subprocess.run(  # nosec B603 B607 - trusted osascript command
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return {
            "status": "opened",
            "session_id": session_id,
            "terminal": terminal,
            "pane_target": pane_target,
            "window_target": str(window_target),
        }
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        logger.error(
            "Failed to open %s for session %s: %s", terminal, session_id, error_msg
        )
        return {
            "status": "error",
            "terminal": terminal,
            "error": error_msg,
        }
    except subprocess.TimeoutExpired:
        logger.error("Timeout opening %s for session %s", terminal, session_id)
        return {
            "status": "error",
            "terminal": terminal,
            "error": "Timeout executing AppleScript",
        }


@router.post("/sessions/{session_id}/keys")
async def send_keys_to_session(
    session_id: str, keys: str, enter: bool = True
) -> JsonResponse:
    """Send keystrokes to a session's tmux pane.

    Args:
        session_id: Unique session identifier
        keys: Keys to send (use special values: "C-c" for Ctrl+C, "Escape" for ESC)
        enter: Whether to send Enter after keys (default: True)

    Returns:
        dict: Success status or error information

    Raises:
        SessionNotFoundError: If session_id doesn't exist

    Example:
        POST /api/sessions/sess-456/keys?keys=hello&enter=true
        Response: {"status": "sent", "keys": "hello", "enter": true}
    """
    session = _get_session_or_raise(session_id)
    tmux_orch = _get_tmux()

    try:
        tmux_orch.send_keys(session.tmux_target, keys, enter=enter)
        return {"status": "sent", "keys": keys, "enter": enter}
    except Exception as e:
        logger.warning("Failed to send keys to session %s: %s", session_id, e)
        return {"status": "error", "error": str(e)}


@router.get("/sessions/{session_id}/output")
async def get_session_output(session_id: str, lines: int = 100) -> JsonResponse:
    """Get terminal output from a session.

    Captures the recent output from the session's tmux pane.

    Args:
        session_id: Unique session identifier
        lines: Number of lines to capture (default: 100, max: 10000)

    Returns:
        dict: Session output and metadata

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
    session = _get_session_or_raise(session_id)
    tmux_orch = _get_tmux()

    # Clamp lines to reasonable bounds
    lines = max(1, min(lines, 10000))

    try:
        output = tmux_orch.capture_output(session.tmux_target, lines=lines)
    except Exception as e:
        logger.warning("Failed to capture output for session %s: %s", session_id, e)
        output = f"[Error capturing output: {e}]"

    return {"session_id": session_id, "output": output, "lines": lines}


# ============================================================================
# Activity Tracking Endpoints
# ============================================================================


def _get_activity_tracker() -> Any:
    """Get activity tracker instance from app global.

    Returns:
        ActivityTracker instance

    Raises:
        RuntimeError: If activity tracker is not initialized
    """
    from ..app import activity_tracker

    if activity_tracker is None:
        raise RuntimeError("Activity tracker not initialized")
    return activity_tracker


@router.get("/sessions/{session_id}/activity")
async def get_session_activity(session_id: str) -> JsonResponse:
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
        dict: Activity metrics

    Example:
        GET /api/sessions/sess-456/activity
        Response: {
            "session_id": "sess-456",
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
    session = _get_session_or_raise(session_id)
    tracker = _get_activity_tracker()

    # Auto-register session if not tracked yet
    stats = tracker.get_stats(session_id)
    if stats is None:
        tracker.register_session(session_id, session.tmux_target)
        stats = tracker.get_stats(session_id)

    return {"session_id": session_id, **stats}


@router.get("/sessions/activity/all")
async def get_all_sessions_activity() -> JsonResponse:
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
async def record_user_prompt(session_id: str, prompt: str) -> JsonResponse:
    """Record a user prompt event (for hook integration).

    This endpoint is called by the Claude Code hook system when
    a UserPromptSubmit event occurs.

    Args:
        session_id: Unique session identifier
        prompt: The user's prompt text

    Returns:
        dict: Updated activity stats with status confirmation
    """
    session = _get_session_or_raise(session_id)
    tracker = _get_activity_tracker()

    tracker.on_user_prompt(session_id, session.tmux_target, prompt)

    return {
        "status": "recorded",
        "session_id": session_id,
        **tracker.get_stats(session_id),
    }


@router.post("/sessions/{session_id}/activity/stop")
async def record_agent_stop(session_id: str, response: str = "") -> JsonResponse:
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


# ============================================================================
# Browser Terminal WebSocket Endpoint
# ============================================================================


@router.websocket("/sessions/{session_id}/terminal")
async def terminal_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for Browser Terminal.

    Connects a browser-based xterm.js terminal directly to the session's tmux pane
    using capture-pane for output and send-keys for input. This provides a direct
    view of the pane without tmux's own UI/statusbar getting in the way.

    Protocol:
    - Text messages: Input to send via tmux send-keys
    - JSON messages with "resize": {"cols": N, "rows": M} → Resize tmux pane

    Args:
        websocket: The WebSocket connection
        session_id: Unique session identifier

    Raises:
        WebSocketDisconnect: When client disconnects
    """
    await websocket.accept()

    # Validate session and get pane_id
    try:
        session = _get_session_or_raise(session_id)
    except SessionNotFoundError:
        await websocket.close(code=4000, reason="Session not found")
        return

    pane_id = session.tmux_target
    if not pane_id:
        await websocket.close(code=4001, reason="Session has no tmux target")
        return

    logger.info(
        "Browser terminal connecting to session %s (pane %s)", session_id, pane_id
    )

    # Get actual tmux pane dimensions
    # We send these to the browser so xterm.js can match the pane size
    # instead of the browser trying to resize the tmux pane
    pane_size_result = subprocess.run(  # nosec B603 B607 - trusted tmux command
        [
            "tmux",
            "display-message",
            "-t",
            pane_id,
            "-p",
            "#{pane_width} #{pane_height}",
        ],
        capture_output=True,
        text=True,
        timeout=2,
        check=False,
    )
    if pane_size_result.returncode == 0:
        try:
            parts = pane_size_result.stdout.strip().split()
            pane_cols = int(parts[0])
            pane_rows = int(parts[1])
        except (ValueError, IndexError):
            pane_cols, pane_rows = 80, 24
    else:
        pane_cols, pane_rows = 80, 24

    logger.info("Tmux pane %s has size %dx%d", pane_id, pane_cols, pane_rows)

    running = True
    last_content = ""
    current_cols = pane_cols
    current_rows = pane_rows
    frame_count = 0

    async def capture_output() -> None:
        """Continuously capture pane output and send to WebSocket."""
        nonlocal running, last_content, current_rows, frame_count

        # Send pane size to browser first so it can configure xterm.js to match
        # The browser should NOT resize the tmux pane - it adapts to the pane size
        await websocket.send_text(
            json.dumps({"type": "pane_size", "cols": pane_cols, "rows": pane_rows})
        )

        # Small delay to let browser configure xterm.js
        await asyncio.sleep(0.1)

        while running:
            try:
                await asyncio.sleep(
                    0.1
                )  # 100ms polling - balance between responsiveness and CPU

                # Capture pane content with ANSI colors
                # -S 0 means start from the first visible line
                # -E '' means end at last line
                result = subprocess.run(  # nosec B603 B607 - trusted tmux command
                    [
                        "tmux",
                        "capture-pane",
                        "-t",
                        pane_id,
                        "-p",  # Print to stdout
                        "-e",  # Include escape sequences (colors)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )

                if result.returncode == 0:
                    content = result.stdout

                    # Fix 2: Remove trailing whitespace from each line
                    # tmux capture-pane pads lines to full width which causes layout issues
                    lines = content.split("\n")
                    content = "\n".join(line.rstrip() for line in lines)

                    # Only send if changed
                    if content != last_content:
                        frame_count += 1

                        # Send frame update with cursor positioning only
                        # \x1b[H = cursor to home position (1,1)
                        #
                        # We don't use \x1b[2J (clear screen) because it can cause
                        # flickering and rendering issues. Instead, we just position
                        # the cursor at home and let the content overwrite.
                        # The content from tmux capture-pane already fills the screen.
                        frame_data = f"\x1b[H{content}"
                        await websocket.send_text(frame_data)
                        last_content = content

            except subprocess.TimeoutExpired:
                pass
            except WebSocketDisconnect:
                break
            except Exception as e:
                if running:
                    logger.debug("Capture error: %s", e)
                await asyncio.sleep(0.2)

        running = False

    async def handle_input() -> None:
        """Receive WebSocket input and send to tmux pane."""
        nonlocal running, current_cols, current_rows

        try:
            while running:
                try:
                    data = await asyncio.wait_for(websocket.receive(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue

                if data.get("type") == "websocket.disconnect":
                    break

                if "text" in data:
                    text = data["text"]

                    # Check for resize message - we now ignore these to prevent
                    # the browser from resizing the tmux pane (which breaks Claude Code UI)
                    if text.startswith('{"resize":'):
                        try:
                            msg = json.loads(text)
                            cols = msg["resize"]["cols"]
                            rows = msg["resize"]["rows"]
                            logger.debug(
                                "Browser requested resize to %dx%d (ignored - using pane size %dx%d)",
                                cols,
                                rows,
                                pane_cols,
                                pane_rows,
                            )
                            # DO NOT resize tmux pane - we want the browser to adapt to the pane
                            # not the other way around
                        except (json.JSONDecodeError, KeyError):
                            pass
                    else:
                        # Send input to tmux pane via send-keys
                        # nosec B603 B607 - all subprocess calls here use trusted
                        # tmux commands with validated pane_id from session lookup
                        for char in text:
                            if char == "\r":
                                # Enter key
                                subprocess.run(  # nosec B603 B607
                                    ["tmux", "send-keys", "-t", pane_id, "Enter"],
                                    capture_output=True,
                                    timeout=1,
                                    check=False,
                                )
                            elif char in ("\x7f", "\b"):
                                # Backspace
                                subprocess.run(  # nosec B603 B607
                                    ["tmux", "send-keys", "-t", pane_id, "BSpace"],
                                    capture_output=True,
                                    timeout=1,
                                    check=False,
                                )
                            elif char == "\x1b":
                                # Escape
                                subprocess.run(  # nosec B603 B607
                                    ["tmux", "send-keys", "-t", pane_id, "Escape"],
                                    capture_output=True,
                                    timeout=1,
                                    check=False,
                                )
                            elif char == "\x03":
                                # Ctrl+C
                                subprocess.run(  # nosec B603 B607
                                    ["tmux", "send-keys", "-t", pane_id, "C-c"],
                                    capture_output=True,
                                    timeout=1,
                                    check=False,
                                )
                            elif char == "\x04":
                                # Ctrl+D
                                subprocess.run(  # nosec B603 B607
                                    ["tmux", "send-keys", "-t", pane_id, "C-d"],
                                    capture_output=True,
                                    timeout=1,
                                    check=False,
                                )
                            elif char == "\t":
                                # Tab
                                subprocess.run(  # nosec B603 B607
                                    ["tmux", "send-keys", "-t", pane_id, "Tab"],
                                    capture_output=True,
                                    timeout=1,
                                    check=False,
                                )
                            elif ord(char) < 32:
                                # Other control characters
                                ctrl_char = chr(ord(char) + 64)
                                subprocess.run(  # nosec B603 B607
                                    [
                                        "tmux",
                                        "send-keys",
                                        "-t",
                                        pane_id,
                                        f"C-{ctrl_char.lower()}",
                                    ],
                                    capture_output=True,
                                    timeout=1,
                                    check=False,
                                )
                            else:
                                # Regular character - send literally
                                subprocess.run(  # nosec B603 B607
                                    ["tmux", "send-keys", "-t", pane_id, "-l", char],
                                    capture_output=True,
                                    timeout=1,
                                    check=False,
                                )

        except WebSocketDisconnect:
            logger.info("Browser terminal disconnected from session %s", session_id)
        finally:
            running = False

    # Run capture and input handler in parallel
    try:
        await asyncio.gather(capture_output(), handle_input(), return_exceptions=True)
    finally:
        running = False
        logger.info("Browser terminal closed for session %s", session_id)
