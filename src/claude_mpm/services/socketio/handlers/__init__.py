"""Socket.IO event handlers module.

WHY: This module provides a modular, maintainable structure for Socket.IO event handling,
replacing the monolithic _register_events() method with focused handler classes.
Each handler class manages a specific domain of functionality, improving testability
and maintainability.
"""

from .base import BaseEventHandler

# NOTE: CodeAnalysisEventHandler (File Tree interface) was removed from the dashboard.
from .connection import ConnectionEventHandler
from .file import FileEventHandler
from .git import GitEventHandler
from .memory import MemoryEventHandler
from .project import ProjectEventHandler
from .registry import EventHandlerRegistry

__all__ = [
    "BaseEventHandler",
    # DISABLED: File Tree interface removed from dashboard
    # "CodeAnalysisEventHandler",
    "ConnectionEventHandler",
    "EventHandlerRegistry",
    "FileEventHandler",
    "GitEventHandler",
    "MemoryEventHandler",
    "ProjectEventHandler",
]
