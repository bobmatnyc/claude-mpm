"""Ticket data models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    """Ticket status enumeration."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    CLOSED = "closed"
    BLOCKED = "blocked"


class TicketPriority(str, Enum):
    """Ticket priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketBase(BaseModel):
    """Base ticket model."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None)
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM)
    labels: list[str] = Field(default_factory=list)


class TicketCreate(TicketBase):
    """Model for creating a ticket."""

    assignee: str | None = Field(default=None)
    parent_id: str | None = Field(default=None)


class TicketUpdate(BaseModel):
    """Model for updating a ticket."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None)
    status: TicketStatus | None = Field(default=None)
    priority: TicketPriority | None = Field(default=None)
    assignee: str | None = Field(default=None)
    labels: list[str] | None = Field(default=None)


class Ticket(TicketBase):
    """Full ticket model."""

    id: str
    status: TicketStatus = Field(default=TicketStatus.OPEN)
    assignee: str | None = Field(default=None)
    parent_id: str | None = Field(default=None)
    created_at: datetime
    updated_at: datetime
    created_by: str | None = Field(default=None)

    model_config = {
        "from_attributes": True,
    }
