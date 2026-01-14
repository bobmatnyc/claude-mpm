"""Work item models for MPM Commander work queue.

This module defines work items that represent tasks to be executed
by the Commander daemon across multiple projects.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class WorkState(Enum):
    """Lifecycle states of a work item."""

    PENDING = "pending"  # Created but not yet queued
    QUEUED = "queued"  # In queue, waiting for execution
    IN_PROGRESS = "in_progress"  # Currently being executed
    BLOCKED = "blocked"  # Paused due to blocking event
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Failed with error
    CANCELLED = "cancelled"  # Manually cancelled


class WorkPriority(Enum):
    """Priority levels for work items, ordered from highest to lowest."""

    CRITICAL = 4  # Execute immediately
    HIGH = 3  # Execute as soon as possible
    MEDIUM = 2  # Normal priority
    LOW = 1  # Execute when idle

    def __lt__(self, other: "WorkPriority") -> bool:
        """Enable priority comparison for sorting (higher value = higher priority)."""
        if not isinstance(other, WorkPriority):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: "WorkPriority") -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, WorkPriority):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: "WorkPriority") -> bool:
        """Greater than comparison."""
        if not isinstance(other, WorkPriority):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: "WorkPriority") -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, WorkPriority):
            return NotImplemented
        return self.value >= other.value


@dataclass
class WorkItem:
    """Represents a work item to be executed by the Commander.

    Work items are queued tasks that will be executed by RuntimeExecutor.
    They support priority-based execution and dependency chains.

    Attributes:
        id: Unique work item identifier
        project_id: ID of project this work belongs to
        content: The message/task to send to Claude
        state: Current lifecycle state
        priority: Execution priority
        created_at: When the work item was created
        started_at: When execution started (if IN_PROGRESS or later)
        completed_at: When execution completed (if COMPLETED/FAILED)
        result: Result output on completion
        error: Error message if FAILED
        depends_on: List of work item IDs that must complete first
        metadata: Additional structured data about the work

    Example:
        >>> work = WorkItem(
        ...     id="work-123",
        ...     project_id="proj-abc",
        ...     content="Implement OAuth2 authentication",
        ...     priority=WorkPriority.HIGH
        ... )
        >>> work.can_start({"work-122"})  # Check if dependencies satisfied
        True
    """

    id: str
    project_id: str
    content: str
    state: WorkState = WorkState.PENDING
    priority: WorkPriority = WorkPriority.MEDIUM
    created_at: datetime = field(default_factory=_utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_start(self, completed_ids: set[str]) -> bool:
        """Check if dependencies are satisfied.

        Args:
            completed_ids: Set of work item IDs that have completed

        Returns:
            True if all dependencies in completed_ids, False otherwise

        Example:
            >>> work = WorkItem(id="w1", project_id="p1", content="Task",
            ...                 depends_on=["w0"])
            >>> work.can_start({"w0"})
            True
            >>> work.can_start(set())
            False
        """
        if not self.depends_on:
            return True
        return all(dep_id in completed_ids for dep_id in self.depends_on)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence.

        Returns:
            Dictionary representation suitable for JSON serialization

        Example:
            >>> work = WorkItem(id="w1", project_id="p1", content="Task")
            >>> data = work.to_dict()
            >>> data["id"]
            'w1'
        """
        return {
            "id": self.id,
            "project_id": self.project_id,
            "content": self.content,
            "state": self.state.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "result": self.result,
            "error": self.error,
            "depends_on": self.depends_on,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkItem":
        """Deserialize from persistence.

        Args:
            data: Dictionary from to_dict()

        Returns:
            Reconstructed WorkItem instance

        Raises:
            ValueError: If required fields missing or invalid

        Example:
            >>> data = {"id": "w1", "project_id": "p1", "content": "Task",
            ...         "state": "pending", "priority": 2}
            >>> work = WorkItem.from_dict(data)
            >>> work.id
            'w1'
        """
        # Parse enums
        try:
            state = WorkState(data["state"])
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid or missing state: {e}") from e

        # Priority can be int or string
        priority_val = data.get("priority", 2)
        if isinstance(priority_val, str):
            priority = WorkPriority[priority_val.upper()]
        else:
            priority = WorkPriority(priority_val)

        # Parse datetimes
        def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
            if not dt_str:
                return None
            return datetime.fromisoformat(dt_str)

        created_at = parse_datetime(data.get("created_at"))
        if not created_at:
            created_at = _utc_now()

        return cls(
            id=data["id"],
            project_id=data["project_id"],
            content=data["content"],
            state=state,
            priority=priority,
            created_at=created_at,
            started_at=parse_datetime(data.get("started_at")),
            completed_at=parse_datetime(data.get("completed_at")),
            result=data.get("result"),
            error=data.get("error"),
            depends_on=data.get("depends_on", []),
            metadata=data.get("metadata", {}),
        )
