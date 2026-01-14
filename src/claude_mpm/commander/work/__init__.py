"""Work queue and execution module for MPM Commander.

This module provides work queue management and execution capabilities:
- WorkItem: Data model for work items
- WorkState: Lifecycle states (PENDING, QUEUED, IN_PROGRESS, etc.)
- WorkPriority: Priority levels (CRITICAL, HIGH, MEDIUM, LOW)
- WorkQueue: Queue management with priority and dependencies
- WorkExecutor: Execution via RuntimeExecutor

Example:
    >>> from claude_mpm.commander.work import (
    ...     WorkQueue, WorkExecutor, WorkItem, WorkState, WorkPriority
    ... )
    >>> queue = WorkQueue("proj-123")
    >>> work = queue.add("Implement feature", WorkPriority.HIGH)
    >>> executor = WorkExecutor(runtime, queue)
    >>> await executor.execute_next()
"""

from ..models.work import WorkItem, WorkPriority, WorkState
from .executor import WorkExecutor
from .queue import WorkQueue

__all__ = [
    "WorkExecutor",
    "WorkItem",
    "WorkPriority",
    "WorkQueue",
    "WorkState",
]
