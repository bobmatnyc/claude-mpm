"""Project management endpoints for MPM Commander API.

This module implements REST endpoints for registering, listing, and managing
projects in the MPM Commander.
"""

from pathlib import Path
from typing import List

from fastapi import APIRouter, Request, Response

from ...models import ProjectState
from ..errors import InvalidPathError, ProjectAlreadyExistsError, ProjectNotFoundError
from ..schemas import ProjectResponse, RegisterProjectRequest, SessionResponse

router = APIRouter()


def _get_registry(request: Request):
    """Get registry instance from app.state."""
    if not hasattr(request.app.state, "registry") or request.app.state.registry is None:
        raise RuntimeError("Registry not initialized")
    return request.app.state.registry


def _project_to_response(project) -> ProjectResponse:
    """Convert Project model to ProjectResponse schema.

    Args:
        project: Project instance

    Returns:
        ProjectResponse with all project data
    """
    # Convert sessions dict to list of SessionResponse
    session_responses = [
        SessionResponse(
            id=session.id,
            project_id=session.project_id,
            runtime=session.runtime,
            tmux_target=session.tmux_target,
            status=session.status,
            created_at=session.created_at,
        )
        for session in project.sessions.values()
    ]

    return ProjectResponse(
        id=project.id,
        path=project.path,
        name=project.name,
        state=project.state.value,
        state_reason=project.state_reason,
        sessions=session_responses,
        pending_events_count=len(project.pending_events),
        last_activity=project.last_activity,
        created_at=project.created_at,
    )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(request: Request) -> List[ProjectResponse]:
    """List all registered projects.

    Returns:
        List of project information (may be empty)

    Example:
        GET /api/projects
        Response: [
            {
                "id": "abc-123",
                "path": "/Users/user/projects/my-app",
                "name": "my-app",
                "state": "idle",
                "state_reason": null,
                "sessions": [],
                "pending_events_count": 0,
                "last_activity": "2025-01-12T10:00:00Z",
                "created_at": "2025-01-12T09:00:00Z"
            }
        ]
    """
    registry = _get_registry(request)
    projects = registry.list_all()
    return [_project_to_response(p) for p in projects]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(request: Request, project_id: str) -> ProjectResponse:
    """Get project details by ID.

    Args:
        project_id: Unique project identifier

    Returns:
        Project information

    Raises:
        ProjectNotFoundError: If project_id doesn't exist

    Example:
        GET /api/projects/abc-123
        Response: {
            "id": "abc-123",
            "path": "/Users/user/projects/my-app",
            "name": "my-app",
            "state": "idle",
            ...
        }
    """
    registry = _get_registry(request)
    project = registry.get(project_id)

    if project is None:
        raise ProjectNotFoundError(project_id)

    return _project_to_response(project)


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def register_project(
    request: Request, req: RegisterProjectRequest
) -> ProjectResponse:
    """Register a new project.

    Args:
        req: Registration request with path and optional name

    Returns:
        Newly registered project information

    Raises:
        InvalidPathError: If path doesn't exist or isn't a directory
        ProjectAlreadyExistsError: If path already registered

    Example:
        POST /api/projects
        Body: {
            "path": "/Users/user/projects/my-app",
            "name": "My App"
        }
        Response: {
            "id": "abc-123",
            "path": "/Users/user/projects/my-app",
            "name": "My App",
            "state": "idle",
            ...
        }
    """
    registry = _get_registry(request)

    # Validate path exists and is directory
    path_obj = Path(req.path)
    if not path_obj.exists() or not path_obj.is_dir():
        raise InvalidPathError(req.path)

    try:
        project = registry.register(req.path, req.name, req.project_id)
        return _project_to_response(project)
    except ValueError as e:
        # Registry raises ValueError for duplicate registration
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            raise ProjectAlreadyExistsError(req.path) from e
        # Re-raise as InvalidPathError for other validation errors
        raise InvalidPathError(req.path) from e


@router.delete("/projects/{project_id}", status_code=204)
async def unregister_project(request: Request, project_id: str) -> Response:
    """Unregister a project.

    Args:
        project_id: Unique project identifier

    Returns:
        Empty response with 204 status

    Raises:
        ProjectNotFoundError: If project_id doesn't exist

    Example:
        DELETE /api/projects/abc-123
        Response: 204 No Content
    """
    registry = _get_registry(request)

    try:
        registry.unregister(project_id)
        return Response(status_code=204)
    except KeyError as e:
        raise ProjectNotFoundError(project_id) from e


@router.post("/projects/{project_id}/pause", response_model=ProjectResponse)
async def pause_project(request: Request, project_id: str) -> ProjectResponse:
    """Pause a project.

    Sets project state to PAUSED to prevent automatic work processing.

    Args:
        project_id: Unique project identifier

    Returns:
        Updated project information

    Raises:
        ProjectNotFoundError: If project_id doesn't exist

    Example:
        POST /api/projects/abc-123/pause
        Response: {
            "id": "abc-123",
            "state": "paused",
            "state_reason": "Manually paused via API",
            ...
        }
    """
    registry = _get_registry(request)
    project = registry.get(project_id)

    if project is None:
        raise ProjectNotFoundError(project_id)

    registry.update_state(
        project_id,
        ProjectState.PAUSED,
        reason="Manually paused via API",
    )

    return _project_to_response(project)


@router.post("/projects/{project_id}/resume", response_model=ProjectResponse)
async def resume_project(request: Request, project_id: str) -> ProjectResponse:
    """Resume a paused project.

    Sets project state back to IDLE to allow work processing.

    Args:
        project_id: Unique project identifier

    Returns:
        Updated project information

    Raises:
        ProjectNotFoundError: If project_id doesn't exist

    Example:
        POST /api/projects/abc-123/resume
        Response: {
            "id": "abc-123",
            "state": "idle",
            "state_reason": "Resumed via API",
            ...
        }
    """
    registry = _get_registry(request)
    project = registry.get(project_id)

    if project is None:
        raise ProjectNotFoundError(project_id)

    registry.update_state(
        project_id,
        ProjectState.IDLE,
        reason="Resumed via API",
    )

    return _project_to_response(project)
