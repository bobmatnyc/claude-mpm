"""Work queue management endpoints for MPM Commander API.

This module implements REST endpoints for managing work items
in project work queues.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ...models.work import WorkPriority, WorkState
from ...work import WorkQueue
from ..errors import ProjectNotFoundError
from ..schemas import CreateWorkRequest, WorkItemResponse

router = APIRouter()


def _get_registry():
    """Get registry instance from app global."""
    from ..app import registry

    if registry is None:
        raise RuntimeError("Registry not initialized")
    return registry


def _work_item_to_response(work_item) -> WorkItemResponse:
    """Convert WorkItem model to WorkItemResponse schema.

    Args:
        work_item: WorkItem instance

    Returns:
        WorkItemResponse with all work item data
    """
    return WorkItemResponse(
        id=work_item.id,
        project_id=work_item.project_id,
        content=work_item.content,
        state=work_item.state.value,
        priority=work_item.priority.value,
        created_at=work_item.created_at,
        started_at=work_item.started_at,
        completed_at=work_item.completed_at,
        result=work_item.result,
        error=work_item.error,
        depends_on=work_item.depends_on,
        metadata=work_item.metadata,
    )


@router.post("/projects/{project_id}/work", response_model=WorkItemResponse)
async def add_work(project_id: str, work: CreateWorkRequest) -> WorkItemResponse:
    """Add work item to project queue.

    Args:
        project_id: Project identifier
        work: Work item creation request

    Returns:
        Created work item

    Raises:
        HTTPException: 404 if project not found

    Example:
        POST /api/projects/proj-123/work
        Request: {
            "content": "Implement OAuth2 authentication",
            "priority": 3,
            "depends_on": ["work-abc"]
        }
        Response: {
            "id": "work-xyz",
            "project_id": "proj-123",
            "content": "Implement OAuth2 authentication",
            "state": "queued",
            "priority": 3,
            ...
        }
    """
    registry = _get_registry()

    # Get project
    try:
        project = registry.get(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Get or create work queue for project
    # Note: In full implementation, this would be managed by ProjectSession
    # For now, we'll need to integrate with project's work queue
    # Access or create work queue
    if not hasattr(project, "_work_queue"):
        project._work_queue = WorkQueue(project_id)

    queue = project._work_queue

    # Convert priority int to enum
    priority = WorkPriority(work.priority)

    # Add work item
    work_item = queue.add(
        content=work.content, priority=priority, depends_on=work.depends_on
    )

    return _work_item_to_response(work_item)


@router.get("/projects/{project_id}/work", response_model=List[WorkItemResponse])
async def list_work(
    project_id: str, state: Optional[str] = Query(None, description="Filter by state")
) -> List[WorkItemResponse]:
    """List work items for project.

    Args:
        project_id: Project identifier
        state: Optional state filter (pending, queued, in_progress, etc.)

    Returns:
        List of work items (may be empty)

    Raises:
        HTTPException: 404 if project not found, 400 if invalid state

    Example:
        GET /api/projects/proj-123/work
        Response: [
            {"id": "work-1", "state": "queued", ...},
            {"id": "work-2", "state": "in_progress", ...}
        ]

        GET /api/projects/proj-123/work?state=queued
        Response: [
            {"id": "work-1", "state": "queued", ...}
        ]
    """
    registry = _get_registry()

    # Get project
    try:
        project = registry.get(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Get work queue
    if not hasattr(project, "_work_queue"):
        project._work_queue = WorkQueue(project_id)

    queue = project._work_queue

    # Parse state filter
    state_filter = None
    if state:
        try:
            state_filter = WorkState(state)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state: {state}. "
                f"Valid states: {[s.value for s in WorkState]}",
            ) from e

    # List work items
    items = queue.list(state=state_filter)

    return [_work_item_to_response(item) for item in items]


@router.get("/projects/{project_id}/work/{work_id}", response_model=WorkItemResponse)
async def get_work(project_id: str, work_id: str) -> WorkItemResponse:
    """Get work item details.

    Args:
        project_id: Project identifier
        work_id: Work item identifier

    Returns:
        Work item details

    Raises:
        HTTPException: 404 if project or work item not found

    Example:
        GET /api/projects/proj-123/work/work-xyz
        Response: {
            "id": "work-xyz",
            "project_id": "proj-123",
            "state": "in_progress",
            ...
        }
    """
    registry = _get_registry()

    # Get project
    try:
        project = registry.get(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Get work queue
    if not hasattr(project, "_work_queue"):
        raise HTTPException(status_code=404, detail="Work queue not found")

    queue = project._work_queue

    # Get work item
    work_item = queue.get(work_id)
    if not work_item:
        raise HTTPException(status_code=404, detail=f"Work item {work_id} not found")

    return _work_item_to_response(work_item)


@router.post("/projects/{project_id}/work/{work_id}/cancel")
async def cancel_work(project_id: str, work_id: str) -> dict:
    """Cancel pending work item.

    Args:
        project_id: Project identifier
        work_id: Work item identifier

    Returns:
        Success message

    Raises:
        HTTPException: 404 if project/work not found, 400 if invalid state

    Example:
        POST /api/projects/proj-123/work/work-xyz/cancel
        Response: {"status": "cancelled", "id": "work-xyz"}
    """
    registry = _get_registry()

    # Get project
    try:
        project = registry.get(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Get work queue
    if not hasattr(project, "_work_queue"):
        raise HTTPException(status_code=404, detail="Work queue not found")

    queue = project._work_queue

    # Cancel work item
    if not queue.cancel(work_id):
        work_item = queue.get(work_id)
        if not work_item:
            raise HTTPException(
                status_code=404, detail=f"Work item {work_id} not found"
            )
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel work item in state {work_item.state.value}",
        )

    return {"status": "cancelled", "id": work_id}
