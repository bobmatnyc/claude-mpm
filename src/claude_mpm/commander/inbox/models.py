"""Inbox item model for event display enrichment.

Combines event data with project information for inbox rendering.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..models.events import Event


@dataclass
class InboxItem:
    """Enriched event for inbox display.

    Combines Event with project metadata and computed display fields.

    Attributes:
        event: The underlying event
        project_name: Human-readable project name
        project_path: Filesystem path to project
        session_runtime: Optional runtime identifier for the session

    Example:
        >>> item = InboxItem(
        ...     event=event,
        ...     project_name="My App",
        ...     project_path="/Users/masa/Projects/my-app",
        ...     session_runtime="python-agent"
        ... )
        >>> item.age_display
        '5m ago'
    """

    event: Event
    project_name: str
    project_path: str
    session_runtime: Optional[str] = None

    @property
    def age(self) -> timedelta:
        """Time since event was created.

        Returns:
            Timedelta representing event age
        """
        return datetime.now(timezone.utc) - self.event.created_at

    @property
    def age_display(self) -> str:
        """Human-readable age string.

        Returns age formatted as:
        - "Xs ago" for under 60 seconds
        - "Xm ago" for under 60 minutes
        - "Xh ago" for under 24 hours
        - "Xd ago" for 24+ hours

        Returns:
            Formatted age string (e.g., "5m ago", "2h ago", "3d ago")
        """
        seconds = int(self.age.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"
