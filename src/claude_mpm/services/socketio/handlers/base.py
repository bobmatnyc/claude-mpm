"""Base event handler class for Socket.IO events.

WHY: This provides common functionality for all event handlers, including
logging, error handling, and access to the server instance. All handler
classes inherit from this to ensure consistent behavior.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ....core.logger import get_logger
from ....core.typing_utils import EventData, EventName, SocketId

if TYPE_CHECKING:
    from logging import Logger

    import socketio

    from ..server import SocketIOServer


class BaseEventHandler:
    """Base class for Socket.IO event handlers.

    WHY: Provides common functionality and structure for all event handlers,
    ensuring consistent error handling, logging, and server access patterns.
    Each handler focuses on a specific domain while sharing common infrastructure.
    """

    def __init__(self, server: "SocketIOServer") -> None:
        """Initialize the base handler.

        Args:
            server: The SocketIOServer instance that owns this handler
        """
        self.server: SocketIOServer = server
        self.sio: socketio.AsyncServer = server.sio
        self.logger: Logger = get_logger(self.__class__.__name__)
        self.clients: Dict[SocketId, Dict[str, Any]] = server.clients
        self.event_history: List[Dict[str, Any]] = server.event_history

    def register_events(self) -> None:
        """Register all events handled by this handler.

        WHY: This method must be implemented by each handler subclass
        to register its specific events with the Socket.IO server.
        """
        raise NotImplementedError("Subclasses must implement register_events()")

    async def emit_to_client(
        self, sid: SocketId, event: EventName, data: EventData
    ) -> None:
        """Emit an event to a specific client.

        WHY: Centralizes client communication with consistent error handling
        and logging for debugging connection issues.

        Args:
            sid: Socket.IO session ID of the client
            event: Event name to emit
            data: Data to send with the event
        """
        try:
            await self.sio.emit(event, data, room=sid)
            self.logger.debug(f"Sent {event} to client {sid}")
        except Exception as e:
            self.logger.error(f"Failed to emit {event} to client {sid}: {e}")
            import traceback

            self.logger.error(f"Stack trace: {traceback.format_exc()}")

    async def broadcast_event(
        self, event: EventName, data: EventData, skip_sid: Optional[SocketId] = None
    ) -> None:
        """Broadcast an event to all connected clients.

        WHY: Provides consistent broadcasting with optional exclusion
        of the originating client.

        Args:
            event: Event name to broadcast
            data: Data to send with the event
            skip_sid: Optional session ID to skip
        """
        try:
            self.logger.info(f"🔔 Broadcasting {event} (skip_sid={skip_sid})")
            if skip_sid:
                await self.sio.emit(event, data, skip_sid=skip_sid)
            else:
                await self.sio.emit(event, data)
            self.logger.info(f"✅ Broadcasted {event} to all clients")
        except Exception as e:
            self.logger.error(f"Failed to broadcast {event}: {e}")
            import traceback

            self.logger.error(f"Stack trace: {traceback.format_exc()}")

    def add_to_history(self, event_type: str, data: EventData) -> None:
        """Add an event to the server's event history.

        WHY: Maintains a history of events for new clients to receive
        when they connect, ensuring they have context.

        Args:
            event_type: Type of the event
            data: Event data
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "data": data,
        }
        self.event_history.append(event)
        self.logger.debug(
            f"Added {event_type} to history (total: {len(self.event_history)})"
        )

    def log_error(
        self, operation: str, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an error with context.

        WHY: Provides consistent error logging with context information
        for debugging issues in production.

        Args:
            operation: Description of the operation that failed
            error: The exception that occurred
            context: Optional context information
        """
        self.logger.error(f"Error in {operation}: {error}")
        if context:
            self.logger.error(f"Context: {context}")
        import traceback

        self.logger.error(f"Stack trace: {traceback.format_exc()}")
