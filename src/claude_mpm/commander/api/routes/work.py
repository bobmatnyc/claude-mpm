"""Work queue management endpoints for MPM Commander API.

This module implements REST endpoints for managing work items
in project work queues.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ...models.work import WorkPriority, WorkState
from ...work import WorkQueue
from ..schemas import CreateWorkRequest, WorkItemResponse

router = APIRouter()


def _get_registry(request: Request):
    """Get registry instance from app.state."""
    if not hasattr(request.app.state, "registry") or request.app.state.registry is None:
        raise RuntimeError("Registry not initialized")
    return request.app.state.registry


def _get_work_queues(request: Request) -> Dict:
    """Get work queues dict from app.state (shared with daemon)."""
    if (
        not hasattr(request.app.state, "work_queues")
        or request.app.state.work_queues is None
    ):
        raise RuntimeError("Work queues not initialized")
    return request.app.state.work_queues


def _get_daemon(request: Request):
    """Get daemon instance from app.state."""
    if not hasattr(request.app.state, "daemon_instance"):
        return None
    return request.app.state.daemon_instance


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
async def add_work(
    request: Request, project_id: str, work: CreateWorkRequest
) -> WorkItemResponse:
    """Add work item to project queue.

    Args:
        request: FastAPI request (for accessing app.state)
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
    registry = _get_registry(request)
    work_queues = _get_work_queues(request)
    daemon = _get_daemon(request)

    # Get project
    project = registry.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Get or create work queue (shared with daemon)
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"work_queues dict id: {id(work_queues)}, keys: {list(work_queues.keys())}"
    )

    if project_id not in work_queues:
        logger.info(f"Creating new work queue for {project_id}")
        work_queues[project_id] = WorkQueue(project_id)
        logger.info(f"After creation, work_queues keys: {list(work_queues.keys())}")

    queue = work_queues[project_id]

    # Convert priority int to enum
    priority = WorkPriority(work.priority)

    # Add work item
    work_item = queue.add(
        content=work.content, priority=priority, depends_on=work.depends_on
    )

    # Ensure daemon has a session for this project (creates if needed)
    if daemon and not daemon.sessions.get(project_id):
        # Session creation will be handled by daemon's main loop
        # when it detects work in the queue
        pass

    return _work_item_to_response(work_item)


@router.get("/projects/{project_id}/work", response_model=List[WorkItemResponse])
async def list_work(
    request: Request,
    project_id: str,
    state: Optional[str] = Query(None, description="Filter by state"),
) -> List[WorkItemResponse]:
    """List work items for project.

    Args:
        request: FastAPI request (for accessing app.state)
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
    registry = _get_registry(request)
    work_queues = _get_work_queues(request)

    # Get project
    project = registry.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Get work queue (shared with daemon)
    if project_id not in work_queues:
        # Return empty list if no work queue exists yet
        return []

    queue = work_queues[project_id]

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
async def get_work(request: Request, project_id: str, work_id: str) -> WorkItemResponse:
    """Get work item details.

    Args:
        request: FastAPI request (for accessing app.state)
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
    registry = _get_registry(request)
    work_queues = _get_work_queues(request)

    # Get project
    project = registry.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Get work queue (shared with daemon)
    if project_id not in work_queues:
        raise HTTPException(status_code=404, detail="Work queue not found")

    queue = work_queues[project_id]

    # Get work item
    work_item = queue.get(work_id)
    if not work_item:
        raise HTTPException(status_code=404, detail=f"Work item {work_id} not found")

    return _work_item_to_response(work_item)


@router.post("/projects/{project_id}/work/{work_id}/cancel")
async def cancel_work(request: Request, project_id: str, work_id: str) -> dict:
    """Cancel pending work item.

    Args:
        request: FastAPI request (for accessing app.state)
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
    registry = _get_registry(request)
    work_queues = _get_work_queues(request)

    # Get project
    project = registry.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Get work queue (shared with daemon)
    if project_id not in work_queues:
        raise HTTPException(status_code=404, detail="Work queue not found")

    queue = work_queues[project_id]

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
