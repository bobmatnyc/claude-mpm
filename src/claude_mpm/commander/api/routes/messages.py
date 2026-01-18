"""Message and thread management endpoints for MPM Commander API.

This module implements REST endpoints for sending messages and retrieving
conversation threads for projects.
"""

import uuid
from typing import List

from fastapi import APIRouter, Request

from ...models import ThreadMessage
from ..errors import ProjectNotFoundError
from ..schemas import MessageResponse, SendMessageRequest

router = APIRouter()


def _get_registry(request: Request):
    """Get registry instance from app.state."""
    if not hasattr(request.app.state, "registry") or request.app.state.registry is None:
        raise RuntimeError("Registry not initialized")
    return request.app.state.registry


def _message_to_response(message: ThreadMessage) -> MessageResponse:
    """Convert ThreadMessage model to MessageResponse schema.

    Args:
        message: ThreadMessage instance

    Returns:
        MessageResponse with message data
    """
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        session_id=message.session_id,
        timestamp=message.timestamp,
    )


@router.get("/projects/{project_id}/thread", response_model=List[MessageResponse])
async def get_thread(request: Request, project_id: str) -> List[MessageResponse]:
    """Get conversation thread for a project.

    Returns all messages in chronological order.

    Args:
        project_id: Unique project identifier

    Returns:
        List of messages in thread (may be empty)

    Raises:
        ProjectNotFoundError: If project_id doesn't exist

    Example:
        GET /api/projects/abc-123/thread
        Response: [
            {
                "id": "msg-1",
                "role": "user",
                "content": "Fix the login bug",
                "session_id": null,
                "timestamp": "2025-01-12T10:00:00Z"
            },
            {
                "id": "msg-2",
                "role": "assistant",
                "content": "I'll investigate the login issue",
                "session_id": "sess-456",
                "timestamp": "2025-01-12T10:00:30Z"
            }
        ]
    """
    registry = _get_registry(request)
    project = registry.get(project_id)

    if project is None:
        raise ProjectNotFoundError(project_id)

    # Convert thread messages to responses
    return [_message_to_response(m) for m in project.thread]


@router.post(
    "/projects/{project_id}/messages", response_model=MessageResponse, status_code=201
)
async def send_message(
    request: Request, project_id: str, req: SendMessageRequest
) -> MessageResponse:
    """Send a message to a project's active session.

    Adds message to conversation thread and sends to specified or active session.

    Args:
        project_id: Unique project identifier
        req: Message request with content and optional session_id

    Returns:
        Created message information

    Raises:
        ProjectNotFoundError: If project_id doesn't exist

    Example:
        POST /api/projects/abc-123/messages
        Body: {
            "content": "Fix the login bug",
            "session_id": "sess-456"
        }
        Response: {
            "id": "msg-1",
            "role": "user",
            "content": "Fix the login bug",
            "session_id": "sess-456",
            "timestamp": "2025-01-12T10:00:00Z"
        }
    """
    registry = _get_registry(request)
    project = registry.get(project_id)

    if project is None:
        raise ProjectNotFoundError(project_id)

    # Generate message ID
    message_id = str(uuid.uuid4())

    # Create message object
    message = ThreadMessage(
        id=message_id,
        role="user",
        content=req.content,
        session_id=req.session_id,
    )

    # Add to project thread
    project.thread.append(message)

    # Update last activity
    registry.touch(project_id)

    # TODO: Send to session/runtime adapter (Phase 2)
    # For Phase 1, message is just stored in thread

    return _message_to_response(message)
