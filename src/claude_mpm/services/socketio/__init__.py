"""Socket.IO service module.

WHY: This module provides the modular Socket.IO server implementation
with separated event handlers for improved maintainability.
"""

from .handlers import (
    BaseEventHandler,
    ConnectionEventHandler,
    EventHandlerRegistry,
    FileEventHandler,
    GitEventHandler,
    MemoryEventHandler,
    ProjectEventHandler,
)

__all__ = [
    "BaseEventHandler",
    "ConnectionEventHandler",
    "EventHandlerRegistry",
    "FileEventHandler",
    "GitEventHandler",
    "MemoryEventHandler",
    "ProjectEventHandler",
]
