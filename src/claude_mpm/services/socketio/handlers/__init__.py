"""Socket.IO event handlers module.

WHY: This module provides a modular, maintainable structure for Socket.IO event handling,
replacing the monolithic _register_events() method with focused handler classes.
Each handler class manages a specific domain of functionality, improving testability
and maintainability.
"""

from .base import BaseEventHandler
from .connection import ConnectionEventHandler
from .project import ProjectEventHandler
from .memory import MemoryEventHandler
from .file import FileEventHandler
from .git import GitEventHandler
from .registry import EventHandlerRegistry

__all__ = [
    "BaseEventHandler",
    "ConnectionEventHandler",
    "ProjectEventHandler",
    "MemoryEventHandler",
    "FileEventHandler",
    "GitEventHandler",
    "EventHandlerRegistry",
]