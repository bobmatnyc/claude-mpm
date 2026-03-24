"""Pydantic models for messages and streaming events."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    """Request body for sending a message to a session.

    Attributes:
        content: The message text to send.
        stream: If True, respond with text/event-stream SSE.
    """

    model_config = ConfigDict(from_attributes=True)

    content: str = Field(..., description="Message content to send to Claude")
    stream: bool = Field(False, description="Stream response as SSE")


class Message(BaseModel):
    """A single message in the conversation history.

    Attributes:
        id: Message UUID.
        role: 'user' or 'assistant'.
        content: Message text content.
        created_at: When the message was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class StreamEvent(BaseModel):
    """A streaming event from the Claude subprocess (stream-json format).

    Attributes:
        type: Event type from stream-json protocol.
        session_id: Claude session ID (present on 'system' events).
        content: Text content (for assistant events).
        usage: Token usage dict (for assistant events with usage).
        data: Raw event data for pass-through.
    """

    model_config = ConfigDict(from_attributes=True)

    type: str
    session_id: str | None = None
    content: str | None = None
    usage: dict[str, Any] | None = None
    data: dict[str, Any] | None = None


class CompactRequest(BaseModel):
    """Request body for /compact command.

    Attributes:
        retain_hint: Optional hint about what context to retain.
    """

    model_config = ConfigDict(from_attributes=True)

    retain_hint: str | None = Field(None, description="Context to retain after compact")
