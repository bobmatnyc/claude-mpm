"""Event models for MPM Commander (Phase 2).

This module defines the complete event model supporting all event types,
priorities, and statuses for the inbox system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class EventType(Enum):
    """Types of events that can be raised by projects."""

    DECISION_NEEDED = "decision_needed"  # Tool asking which option
    CLARIFICATION = "clarification"  # Tool needs more info
    ERROR = "error"  # Something failed
    APPROVAL = "approval"  # Destructive action pending
    TASK_COMPLETE = "task_complete"  # Work item finished
    MILESTONE = "milestone"  # Significant progress
    STATUS = "status"  # General update
    PROJECT_IDLE = "project_idle"  # Project has no work
    INSTANCE_STARTING = "instance_starting"  # Instance is starting up
    INSTANCE_READY = "instance_ready"  # Instance is ready for work
    INSTANCE_ERROR = "instance_error"  # Instance encountered an error


class EventPriority(Enum):
    """Priority levels for events, ordered from highest to lowest."""

    CRITICAL = "critical"  # Blocking all progress
    HIGH = "high"  # Blocking this project
    NORMAL = "normal"  # Needs response, not blocking
    LOW = "low"  # Informational, can batch
    INFO = "info"  # No response needed

    def __lt__(self, other: "EventPriority") -> bool:
        """Enable priority comparison for sorting."""
        order = [self.CRITICAL, self.HIGH, self.NORMAL, self.LOW, self.INFO]
        return order.index(self) < order.index(other)


class EventStatus(Enum):
    """Lifecycle status of an event."""

    PENDING = "pending"  # Awaiting response
    ACKNOWLEDGED = "acknowledged"  # Seen but not resolved
    RESOLVED = "resolved"  # Response provided
    DISMISSED = "dismissed"  # Intentionally ignored


# Default priority by event type
DEFAULT_PRIORITIES: Dict[EventType, EventPriority] = {
    EventType.ERROR: EventPriority.CRITICAL,
    EventType.DECISION_NEEDED: EventPriority.HIGH,
    EventType.APPROVAL: EventPriority.HIGH,
    EventType.CLARIFICATION: EventPriority.NORMAL,
    EventType.TASK_COMPLETE: EventPriority.LOW,
    EventType.MILESTONE: EventPriority.LOW,
    EventType.STATUS: EventPriority.INFO,
    EventType.PROJECT_IDLE: EventPriority.INFO,
    EventType.INSTANCE_STARTING: EventPriority.INFO,
    EventType.INSTANCE_READY: EventPriority.INFO,
    EventType.INSTANCE_ERROR: EventPriority.HIGH,
}


# Which event types block progress and their scope
BLOCKING_EVENTS: Dict[EventType, str] = {
    EventType.ERROR: "all",  # Blocks all projects
    EventType.DECISION_NEEDED: "project",  # Blocks this project
    EventType.APPROVAL: "project",  # Blocks this project
}


@dataclass
class Event:
    """Represents an event in the MPM Commander system.

    Events are raised by projects to communicate with the user or
    system about state changes, decisions needed, or progress updates.

    Attributes:
        id: Unique event identifier
        project_id: ID of project that raised this event
        type: Type of event (decision, error, status, etc.)
        priority: Urgency level
        title: Short summary of the event
        session_id: Optional session ID if event is session-specific
        status: Current lifecycle status
        content: Detailed event message or description
        context: Additional structured data about the event
        options: For DECISION_NEEDED events, list of choices
        response: User's response to the event
        responded_at: When the response was recorded
        created_at: When the event was created
    """

    id: str
    project_id: str
    type: EventType
    priority: EventPriority
    title: str
    session_id: Optional[str] = None
    status: EventStatus = EventStatus.PENDING
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    options: Optional[List[str]] = None
    response: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utc_now)

    @property
    def is_blocking(self) -> bool:
        """Check if this event blocks progress."""
        return self.type in BLOCKING_EVENTS and self.status == EventStatus.PENDING

    @property
    def blocking_scope(self) -> Optional[str]:
        """Get the scope this event blocks ('all' or 'project')."""
        return BLOCKING_EVENTS.get(self.type)
