"""REST API routes for inbox system.

Provides HTTP endpoints for querying and managing the event inbox.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ...inbox import Inbox
from ...models.events import EventPriority, EventType

router = APIRouter()


def get_inbox() -> Inbox:
    """Dependency to get the global inbox instance.

    Returns:
        The global inbox instance

    Raises:
        RuntimeError: If inbox is not initialized
    """
    from ..app import inbox

    if inbox is None:
        raise RuntimeError("Inbox not initialized")
    return inbox


class InboxItemResponse(BaseModel):
    """Response model for inbox item.

    Attributes:
        event_id: Unique event identifier
        project_id: Project that raised this event
        project_name: Human-readable project name
        project_path: Filesystem path to project
        event_type: Type of event (decision, error, status, etc.)
        priority: Urgency level (critical, high, normal, low, info)
        status: Current lifecycle status
        title: Short event summary
        content: Detailed event message
        options: For DECISION_NEEDED events, list of choices
        age_display: Human-readable age (e.g., "5m ago")
        created_at: When event was created
        session_runtime: Optional session runtime identifier
    """

    event_id: str
    project_id: str
    project_name: str
    project_path: str
    event_type: str
    priority: str
    status: str
    title: str
    content: str
    options: Optional[List[str]]
    age_display: str
    created_at: datetime
    session_runtime: Optional[str]


class InboxCountsResponse(BaseModel):
    """Response model for inbox counts.

    Attributes:
        critical: Count of CRITICAL priority events
        high: Count of HIGH priority events
        normal: Count of NORMAL priority events
        low: Count of LOW priority events
        info: Count of INFO priority events
        total: Total count of all pending events
    """

    critical: int
    high: int
    normal: int
    low: int
    info: int
    total: int


@router.get("/inbox", response_model=List[InboxItemResponse])
async def get_inbox_items(
    limit: int = Query(50, ge=1, le=100, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    priority: Optional[str] = Query(None, description="Filter by priority level"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    inbox: Inbox = Depends(get_inbox),
) -> List[InboxItemResponse]:
    """Get inbox items with optional filtering and pagination.

    Returns a list of inbox items sorted by priority (high to low) then
    created time (old to new). Supports filtering by priority, project,
    and event type.

    Args:
        limit: Maximum number of items to return (1-100, default: 50)
        offset: Number of items to skip for pagination (default: 0)
        priority: Filter by priority (critical, high, normal, low, info)
        project_id: Filter by project ID
        event_type: Filter by event type (decision_needed, error, etc.)

    Returns:
        List of inbox items matching the filters

    Example:
        GET /api/inbox?limit=20&priority=critical
        GET /api/inbox?project_id=proj_123&event_type=error
        GET /api/inbox?offset=50&limit=50  # Pagination
    """
    # Parse enum values if provided
    pri = EventPriority(priority) if priority else None
    evt = EventType(event_type) if event_type else None

    items = inbox.get_items(
        limit=limit,
        offset=offset,
        priority=pri,
        project_id=project_id,
        event_type=evt,
    )

    return [
        InboxItemResponse(
            event_id=item.event.id,
            project_id=item.event.project_id,
            project_name=item.project_name,
            project_path=item.project_path,
            event_type=item.event.type.value,
            priority=item.event.priority.value,
            status=item.event.status.value,
            title=item.event.title,
            content=item.event.content,
            options=item.event.options,
            age_display=item.age_display,
            created_at=item.event.created_at,
            session_runtime=item.session_runtime,
        )
        for item in items
    ]


@router.get("/inbox/counts", response_model=InboxCountsResponse)
async def get_inbox_counts(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    inbox: Inbox = Depends(get_inbox),
) -> InboxCountsResponse:
    """Get count of pending events by priority.

    Returns summary statistics showing how many events exist at each
    priority level. Optionally filtered to a specific project.

    Args:
        project_id: If provided, only count events for this project

    Returns:
        Breakdown of event counts by priority

    Example:
        GET /api/inbox/counts
        GET /api/inbox/counts?project_id=proj_123
    """
    counts = inbox.get_counts(project_id)
    return InboxCountsResponse(**counts.__dict__)
