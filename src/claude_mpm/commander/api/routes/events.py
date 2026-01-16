"""REST API routes for event resolution.

Provides HTTP endpoints for resolving events and managing event responses.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...events.manager import EventManager

router = APIRouter()


def get_event_manager() -> EventManager:
    """Dependency to get the global event manager instance.

    Returns:
        The global event manager instance

    Raises:
        RuntimeError: If event manager is not initialized
    """
    from ..app import event_manager

    if event_manager is None:
        raise RuntimeError("Event manager not initialized")
    return event_manager


def get_event_handler():
    """Dependency to get the global event handler instance.

    Returns:
        The global event handler instance

    Raises:
        RuntimeError: If event handler is not initialized
    """
    from ..app import event_handler

    if event_handler is None:
        raise RuntimeError("Event handler not initialized")
    return event_handler


class EventResponse(BaseModel):
    """Request model for event resolution.

    Attributes:
        response: User's response to the event
    """

    response: str


class EventResolutionResponse(BaseModel):
    """Response model for event resolution.

    Attributes:
        event_id: ID of resolved event
        status: Resolution status
        session_resumed: Whether project session was resumed
    """

    event_id: str
    status: str
    session_resumed: bool


class PendingEventResponse(BaseModel):
    """Response model for pending event.

    Attributes:
        event_id: Unique event identifier
        project_id: Project that raised this event
        event_type: Type of event
        priority: Urgency level
        status: Current lifecycle status
        title: Short event summary
        content: Detailed event message
        options: For DECISION_NEEDED events, list of choices
        is_blocking: Whether event blocks progress
    """

    event_id: str
    project_id: str
    event_type: str
    priority: str
    status: str
    title: str
    content: str
    options: Optional[List[str]]
    is_blocking: bool


@router.post("/events/{event_id}/resolve", response_model=EventResolutionResponse)
async def resolve_event(
    event_id: str,
    response: EventResponse,
    event_handler=Depends(get_event_handler),
) -> EventResolutionResponse:
    """Resolve an event with user response.

    Marks the event as resolved and resumes the project session if it was
    paused for this event.

    Args:
        event_id: ID of event to resolve
        response: User's response to the event

    Returns:
        Resolution status and whether session was resumed

    Raises:
        HTTPException: If event not found (404) or resolution fails (500)

    Example:
        POST /api/events/evt_123/resolve
        {
            "response": "Use authlib for OAuth2"
        }

        Response:
        {
            "event_id": "evt_123",
            "status": "resolved",
            "session_resumed": true
        }
    """
    try:
        session_resumed = await event_handler.resolve_event(event_id, response.response)
        return EventResolutionResponse(
            event_id=event_id,
            status="resolved",
            session_resumed=session_resumed,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=404, detail=f"Event not found: {event_id}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to resolve event: {e!s}"
        ) from e


@router.get("/events/pending", response_model=List[PendingEventResponse])
async def get_pending_events(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    event_handler=Depends(get_event_handler),
) -> List[PendingEventResponse]:
    """Get pending events requiring resolution.

    Returns all unresolved events, optionally filtered by project.
    Events are sorted by priority (high to low) then created time (old to new).

    Args:
        project_id: If provided, only return events for this project

    Returns:
        List of pending events

    Example:
        GET /api/events/pending
        GET /api/events/pending?project_id=proj_123
    """
    events = await event_handler.get_pending_events(project_id)

    return [
        PendingEventResponse(
            event_id=event.id,
            project_id=event.project_id,
            event_type=event.type.value,
            priority=event.priority.value,
            status=event.status.value,
            title=event.title,
            content=event.content,
            options=event.options,
            is_blocking=event_handler.is_blocking(event),
        )
        for event in events
    ]
