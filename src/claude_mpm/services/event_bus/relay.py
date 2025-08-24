"""Socket.IO Relay - Consumes events from EventBus and relays to Socket.IO.

WHY separate relay component:
- Single point of Socket.IO connection management
- Isolates Socket.IO failures from event producers
- Enables graceful degradation when Socket.IO unavailable
- Simplifies testing by mocking just the relay
- Supports batching and retry logic in one place
"""

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

# Socket.IO imports
try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None

import contextlib

from .event_bus import EventBus

# Configure logger
logger = logging.getLogger(__name__)


class SocketIORelay:
    """Relay events from EventBus to Socket.IO clients.

    WHY relay pattern:
    - Decouples event production from Socket.IO emission
    - Handles connection failures without affecting producers
    - Provides single point for Socket.IO configuration
    - Enables event batching and optimization
    - Simplifies debugging with centralized logging
    """

    def __init__(self, port: Optional[int] = None):
        """Initialize the Socket.IO relay.

        Args:
            port: Socket.IO server port (defaults to env var or 8765)
        """
        self.port = port or int(os.environ.get("CLAUDE_MPM_SOCKETIO_PORT", "8765"))
        self.event_bus = EventBus.get_instance()
        self.client: Optional[Any] = None
        self.connected = False
        self.enabled = True
        self.debug = os.environ.get("CLAUDE_MPM_RELAY_DEBUG", "false").lower() == "true"

        # Connection retry settings
        self.max_retries = 3
        self.retry_delay = 0.5
        self.last_connection_attempt = 0
        self.connection_cooldown = 5.0  # Seconds between connection attempts

        # Statistics
        self.stats = {
            "events_relayed": 0,
            "events_failed": 0,
            "connection_failures": 0,
            "last_relay_time": None,
        }

        if not SOCKETIO_AVAILABLE:
            logger.warning("Socket.IO not available, relay will be disabled")
            self.enabled = False

    def enable(self) -> None:
        """Enable the relay."""
        if not SOCKETIO_AVAILABLE:
            logger.warning("Cannot enable relay: Socket.IO not available")
            return
        self.enabled = True
        logger.info("SocketIO relay enabled")

    def disable(self) -> None:
        """Disable the relay."""
        self.enabled = False
        if self.client and self.connected:
            with contextlib.suppress(Exception):
                self.client.disconnect()
        logger.info("SocketIO relay disabled")

    def _create_client(self) -> bool:
        """Create and connect Socket.IO client.

        Returns:
            bool: True if connection successful
        """
        if not SOCKETIO_AVAILABLE or not self.enabled:
            return False

        # Check connection cooldown
        current_time = time.time()
        if current_time - self.last_connection_attempt < self.connection_cooldown:
            return False

        self.last_connection_attempt = current_time

        try:
            # Create new client with better connection settings
            self.client = socketio.Client(
                reconnection=True,
                reconnection_attempts=5,
                reconnection_delay=2,
                reconnection_delay_max=10,
                logger=False,
                engineio_logger=False,
            )

            # Connect to server with longer timeout
            self.client.connect(
                f"http://localhost:{self.port}",
                wait=True,
                wait_timeout=10.0,  # Increase timeout for stability
                transports=["websocket", "polling"],
            )

            self.connected = True
            logger.info(f"SocketIO relay connected to port {self.port}")
            return True

        except Exception as e:
            self.stats["connection_failures"] += 1
            if self.debug:
                logger.debug(f"Failed to connect to Socket.IO server: {e}")
            self.connected = False
            self.client = None
            return False

    def _ensure_connection(self) -> bool:
        """Ensure Socket.IO client is connected.

        Returns:
            bool: True if connected or reconnected
        """
        if not self.enabled:
            return False

        # Check existing connection
        if self.client and self.connected:
            try:
                # Verify connection is still alive
                if self.client.connected:
                    return True
            except:
                pass

        # Need to create or reconnect
        return self._create_client()

    async def relay_event(self, event_type: str, data: Any) -> bool:
        """Relay an event to Socket.IO.

        Args:
            event_type: The event type
            data: The event data

        Returns:
            bool: True if successfully relayed
        """
        if not self.enabled:
            return False

        # Ensure we have a connection
        if not self._ensure_connection():
            self.stats["events_failed"] += 1
            return False

        try:
            # Emit to Socket.IO
            self.client.emit(
                "claude_event",
                {
                    "event": "claude_event",
                    "type": (
                        event_type.split(".")[0] if "." in event_type else event_type
                    ),
                    "subtype": (
                        event_type.split(".", 1)[1] if "." in event_type else "generic"
                    ),
                    "timestamp": data.get("timestamp", datetime.now().isoformat()),
                    "data": data,
                    "source": "event_bus",
                },
            )

            # Update statistics
            self.stats["events_relayed"] += 1
            self.stats["last_relay_time"] = datetime.now().isoformat()

            if self.debug:
                logger.debug(f"Relayed event to Socket.IO: {event_type}")

            return True

        except Exception as e:
            self.stats["events_failed"] += 1
            if self.debug:
                logger.debug(f"Failed to relay event {event_type}: {e}")
            # Mark connection as failed for retry
            self.connected = False
            return False

    def start(self) -> None:
        """Start the relay by subscribing to EventBus events.

        This sets up listeners for all hook events and relays them
        to Socket.IO clients.
        """
        if not self.enabled:
            logger.warning("Cannot start relay: disabled or Socket.IO not available")
            return

        # Define async handler for events
        async def handle_hook_event(event_type: str, data: Any):
            """Handle events from the event bus."""
            # Debug logging
            print(f"[Relay] Received event: {event_type}", flush=True)

            # Only relay hook events by default
            if event_type.startswith("hook."):
                print(f"[Relay] Relaying hook event: {event_type}", flush=True)
                await self.relay_event(event_type, data)

        # Subscribe to all hook events via wildcard
        # This will catch ALL hook.* events
        self.event_bus.on("hook.*", handle_hook_event)

        logger.info("SocketIO relay started and subscribed to events")
        print("[Relay] Started and subscribed to hook.* events", flush=True)

    def stop(self) -> None:
        """Stop the relay and clean up resources."""
        # Disconnect Socket.IO client
        if self.client and self.connected:
            with contextlib.suppress(Exception):
                self.client.disconnect()

        # Could remove event bus listeners here if needed
        # For now, let them be cleaned up naturally

        self.connected = False
        self.client = None
        logger.info("SocketIO relay stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get relay statistics.

        Returns:
            dict: Statistics about relay operation
        """
        return {
            **self.stats,
            "enabled": self.enabled,
            "connected": self.connected,
            "port": self.port,
        }


# Global relay instance
_relay_instance: Optional[SocketIORelay] = None


def get_relay(port: Optional[int] = None) -> SocketIORelay:
    """Get or create the global SocketIO relay instance.

    Args:
        port: Optional port number

    Returns:
        SocketIORelay: The relay instance
    """
    global _relay_instance
    if _relay_instance is None:
        _relay_instance = SocketIORelay(port)
    return _relay_instance


def start_relay(port: Optional[int] = None) -> SocketIORelay:
    """Start the global SocketIO relay.

    Args:
        port: Optional port number

    Returns:
        SocketIORelay: The started relay instance
    """
    relay = get_relay(port)
    relay.start()
    return relay


def stop_relay() -> None:
    """Stop the global SocketIO relay."""
    global _relay_instance
    if _relay_instance:
        _relay_instance.stop()
        _relay_instance = None
