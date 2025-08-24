"""Event Bus Service for decoupled event handling.

This module provides a centralized event bus that decouples event producers
(like hooks) from consumers (like Socket.IO). It uses pyee's AsyncIOEventEmitter
to support both synchronous publishing and asynchronous consumption.

WHY event bus architecture:
- Decouples hooks from Socket.IO implementation details
- Allows multiple consumers for the same events
- Enables easy testing without Socket.IO dependencies
- Provides event filtering and routing capabilities
- Supports both sync (hooks) and async (Socket.IO) contexts
"""

from .event_bus import EventBus
from .relay import SocketIORelay

__all__ = ["EventBus", "SocketIORelay"]
