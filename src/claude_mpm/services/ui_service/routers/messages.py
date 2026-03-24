"""Messages router.

Endpoints:
    GET    /sessions/{id}/messages         — conversation history
    POST   /sessions/{id}/messages         — send message (SSE or JSON)
    DELETE /sessions/{id}/messages         — clear conversation (/clear)
    POST   /sessions/{id}/messages/compact — compact context (/compact)

    GET    /sessions/{id}/context          — token usage
    POST   /context/count-tokens           — proxy token count
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request  # noqa: TC002
from fastapi.responses import StreamingResponse

from claude_mpm.services.ui_service.models.message import (  # noqa: TC001
    CompactRequest,
    MessageCreate,
)

if TYPE_CHECKING:
    from claude_mpm.services.ui_service.models.message import StreamEvent

router = APIRouter(tags=["Messages"])


def _get_pm(request: Request):
    return request.app.state.process_manager


# ---------------------------------------------------------------------------
# Message history
# ---------------------------------------------------------------------------


@router.get(
    "/sessions/{session_id}/messages",
    summary="Get conversation history",
)
async def get_messages(request: Request, session_id: str):
    """Return the full in-memory conversation history for a session."""
    pm = _get_pm(request)
    try:
        session = pm.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"messages": session.message_history}


@router.post(
    "/sessions/{session_id}/messages",
    summary="Send a message to a session",
)
async def send_message(request: Request, session_id: str, body: MessageCreate):
    """Send a message to a session.

    When ``stream=true``, returns a ``text/event-stream`` (SSE) response
    with one JSON-encoded StreamEvent per line.  Otherwise collects all
    events and returns them as a JSON array.
    """
    pm = _get_pm(request)
    try:
        pm.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if body.stream:

        async def event_generator():
            async for event in pm.send_message(session_id, body.content):
                yield f"data: {event.model_dump_json()}\n\n"
            yield 'data: {"type": "message_stop"}\n\n'

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming: collect all events
    events: list[StreamEvent] = []
    async for event in pm.send_message(session_id, body.content):
        events.append(event)

    return {"events": [e.model_dump() for e in events]}


@router.delete(
    "/sessions/{session_id}/messages",
    status_code=204,
    summary="Clear conversation history",
)
async def clear_messages(request: Request, session_id: str):
    """Send /clear to the session stdin and wipe the in-memory history."""
    pm = _get_pm(request)
    try:
        session = pm.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await pm.send_command(session_id, "/clear")
    session.message_history.clear()


@router.post(
    "/sessions/{session_id}/messages/compact",
    summary="Compact context window",
)
async def compact_messages(
    request: Request, session_id: str, body: CompactRequest | None = None
):
    """Send /compact to the session, optionally with a retain hint.

    The retain hint is appended to the command:  ``/compact <hint>``
    """
    pm = _get_pm(request)
    try:
        session = pm.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    cmd = "/compact"
    if body and body.retain_hint:
        cmd = f"/compact {body.retain_hint}"

    session.status = session.status.__class__("compacting")
    await pm.send_command(session_id, cmd)
    return {"message": "Compact command sent", "command": cmd}


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


@router.get(
    "/sessions/{session_id}/context",
    summary="Get context window usage",
)
async def get_context(request: Request, session_id: str):
    """Return token usage and compaction recommendation for a session."""
    pm = _get_pm(request)
    try:
        session = pm.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pct = (
        (session.context_tokens_used / session.context_tokens_total * 100)
        if session.context_tokens_total > 0
        else 0.0
    )
    compaction_recommended = pct > 75.0

    return {
        "tokens_used": session.context_tokens_used,
        "tokens_total": session.context_tokens_total,
        "percent_used": round(pct, 2),
        "compaction_recommended": compaction_recommended,
    }


@router.post(
    "/context/count-tokens",
    summary="Count tokens for a message",
)
async def count_tokens(request: Request):
    """Proxy to Anthropic token count API (or return a stub estimate).

    Accepts any JSON body and forwards it to the Anthropic messages endpoint
    with ``count_tokens: true``.  Falls back to a character-based estimate
    when httpx or the API key is unavailable.
    """
    import math

    body = await request.json()
    content = body.get("content") or body.get("messages", [])

    # Try real API call if key is available
    api_key = request.app.state.config.anthropic_api_key
    if api_key:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages/count_tokens",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=body,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass  # fall through to estimate

    # Character-based estimate: ~4 chars per token
    text = json.dumps(content) if not isinstance(content, str) else content
    estimated = max(1, math.ceil(len(text) / 4))
    return {"input_tokens": estimated, "estimated": True}
