"""
SocketIO Server package for claude-mpm.

WHY: This package contains the modular SocketIO server components that were
extracted from the monolithic socketio_server.py file.

DESIGN DECISION: Split the massive SocketIOServer class into focused modules:
- core.py: Server lifecycle and static file management
- broadcaster.py: Event broadcasting to clients
- event_registry.py: Event handler registration (if needed)

This improves maintainability, testability, and code organization.
"""

from .broadcaster import SocketIOEventBroadcaster
from .core import SocketIOServerCore

__all__ = ["SocketIOEventBroadcaster", "SocketIOServerCore"]
