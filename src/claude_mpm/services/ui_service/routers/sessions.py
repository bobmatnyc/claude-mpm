"""Session management router.

Endpoints:
    GET  /sessions           — list all sessions
    POST /sessions           — create/resume a session
    GET  /sessions/{id}      — get session state
    DELETE /sessions/{id}    — terminate session
    PATCH /sessions/{id}     — update model/permission_mode/output_format
    POST /sessions/{id}/fork — fork session (sends /fork to stdin)
    POST /sessions/{id}/interrupt — send SIGINT
    PUT  /sessions/{id}/plan-mode — toggle plan mode
"""

from fastapi import APIRouter, HTTPException, Request

from claude_mpm.services.ui_service.models.session import SessionCreate, SessionUpdate

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _get_pm(request: Request):
    """Extract the ProcessManager from app state."""
    return request.app.state.process_manager


@router.get("", summary="List all sessions")
async def list_sessions(request: Request):
    """Return a list of all currently active managed sessions."""
    pm = _get_pm(request)
    sessions = pm.list_sessions()
    return [s.to_state().model_dump() for s in sessions]


@router.post("", status_code=201, summary="Create or resume a session")
async def create_session(request: Request, body: SessionCreate):
    """Spawn a new claude CLI subprocess (or resume an existing one).

    Optionally pass ``resume_id`` to attach to an existing Claude session,
    ``model`` to override the model, and ``bare`` to suppress the system prompt.
    """
    pm = _get_pm(request)
    try:
        session = await pm.create_session(body)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return session.to_state().model_dump()


@router.get("/{session_id}", summary="Get session state")
async def get_session(request: Request, session_id: str):
    """Return the current state of a session including token usage."""
    pm = _get_pm(request)
    try:
        session = pm.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return session.to_state().model_dump()


@router.delete("/{session_id}", status_code=204, summary="Terminate a session")
async def delete_session(request: Request, session_id: str):
    """Send SIGTERM to the subprocess and remove the session from tracking."""
    pm = _get_pm(request)
    try:
        pm.get_session(session_id)  # verify existence
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await pm.terminate(session_id)


@router.patch("/{session_id}", summary="Update session properties")
async def update_session(request: Request, session_id: str, body: SessionUpdate):
    """Update mutable session properties (model, permission_mode, output_format).

    Changes take effect on the next message sent to the session.
    """
    pm = _get_pm(request)
    try:
        session = pm.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if body.model is not None:
        session.model = body.model
    if body.permission_mode is not None:
        session.permission_mode = body.permission_mode

    return session.to_state().model_dump()


@router.post("/{session_id}/fork", status_code=201, summary="Fork a session")
async def fork_session(request: Request, session_id: str):
    """Send the /fork command to the session's stdin.

    The new session ID will appear in a subsequent stream-json system event.
    """
    pm = _get_pm(request)
    try:
        pm.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await pm.send_command(session_id, "/fork")
    return {"message": "Fork command sent", "session_id": session_id}


@router.post("/{session_id}/interrupt", summary="Interrupt a running session")
async def interrupt_session(request: Request, session_id: str):
    """Send SIGINT to the subprocess to interrupt a running operation."""
    pm = _get_pm(request)
    try:
        pm.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await pm.interrupt(session_id)
    return {"message": "Interrupt sent", "session_id": session_id}


@router.put("/{session_id}/plan-mode", summary="Toggle plan mode")
async def set_plan_mode(request: Request, session_id: str):
    """Send the plan mode toggle command to the session's stdin."""
    pm = _get_pm(request)
    try:
        pm.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await pm.send_command(session_id, "/plan")
    return {"message": "Plan mode toggled", "session_id": session_id}
