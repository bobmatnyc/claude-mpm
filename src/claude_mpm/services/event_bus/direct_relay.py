"""Direct EventBus to Socket.IO relay that uses server broadcaster.

This module provides a relay that connects EventBus directly to the
Socket.IO server's broadcaster, avoiding the client loopback issue.
"""

import logging
from datetime import datetime
from typing import Any

from .event_bus import EventBus

logger = logging.getLogger(__name__)


class DirectSocketIORelay:
    """Relay EventBus events directly to Socket.IO broadcaster.

    WHY: The original SocketIORelay creates a client connection back to the server,
    which causes events to not reach the dashboard properly. This direct relay
    uses the server's broadcaster directly for proper event emission.
    """

    def __init__(self, server_instance):
        """Initialize the direct relay.

        Args:
            server_instance: The SocketIOServer instance with broadcaster
        """
        self.server = server_instance
        self.event_bus = EventBus.get_instance()
        self.enabled = True
        self.connected = False  # Track connection state
        self.stats = {
            "events_relayed": 0,
            "events_failed": 0,
            "last_relay_time": None,
        }
        self.debug = logger.isEnabledFor(logging.DEBUG)

    def start(self) -> None:
        """Start the relay by subscribing to EventBus events."""
        if not self.enabled:
            logger.warning("DirectSocketIORelay is disabled")
            return

        # Create handler for wildcard events
        def handle_wildcard_hook_event(event_type: str, data: Any):
            """Handle wildcard hook events from the event bus.

            Wildcard handlers receive both event_type and data.
            This is the primary handler that knows the correct event type.
            """
            self._handle_hook_event(event_type, data)

        # Subscribe to all hook events via wildcard
        # This single subscription handles all hook.* events efficiently
        self.event_bus.on("hook.*", handle_wildcard_hook_event)

        # Add debug logging for verification
        logger.info("[DirectRelay] Subscribed to hook.* events on EventBus")
        logger.info(
            f"[DirectRelay] Server broadcaster available: {self.server and self.server.broadcaster is not None}"
        )
        logger.info(f"[DirectRelay] EventBus instance: {self.event_bus is not None}")

        # Mark as connected after successful subscription
        self.connected = True
        logger.info("[DirectRelay] Started and subscribed to hook events")

    def _handle_hook_event(self, event_type: str, data: Any):
        """Internal method to handle hook events and broadcast them.

        Args:
            event_type: The event type (e.g., "hook.pre_tool")
            data: The event data
        """
        try:
            # Log the event reception
            if self.debug:
                logger.debug(f"[DirectRelay] Received event: {event_type}")

            # Only relay hook events
            if event_type.startswith("hook."):
                # Extract the event subtype from the event_type (e.g., "hook.pre_tool" -> "pre_tool")
                event_subtype = (
                    event_type.split(".", 1)[1] if "." in event_type else event_type
                )

                # The data passed to us is the raw event data from the publisher
                # We don't need to extract anything - just use it as is
                actual_data = data

                # Always log important hook events for debugging
                if event_subtype in [
                    "pre_tool",
                    "post_tool",
                    "user_prompt",
                    "subagent_stop",
                ]:
                    logger.info(f"[DirectRelay] Processing {event_type} event")

                # Use the server's broadcaster directly
                if self.server and self.server.broadcaster:
                    # Log debug info about the broadcaster state
                    if self.debug:
                        has_sio = (
                            hasattr(self.server.broadcaster, "sio")
                            and self.server.broadcaster.sio is not None
                        )
                        has_loop = (
                            hasattr(self.server.broadcaster, "loop")
                            and self.server.broadcaster.loop is not None
                        )
                        logger.debug(
                            f"[DirectRelay] Broadcaster state - has_sio: {has_sio}, has_loop: {has_loop}"
                        )
                        logger.debug(
                            f"[DirectRelay] Event subtype: {event_subtype}, data keys: {list(actual_data.keys()) if isinstance(actual_data, dict) else 'not-dict'}"
                        )

                    # The broadcaster's broadcast_event expects an event_type string and data dict
                    # The EventNormalizer will map dotted event names like "hook.pre_tool" correctly
                    # So we pass the full event_type (e.g., "hook.pre_tool") as the event name
                    # This way the normalizer will correctly extract type="hook" and subtype="pre_tool"

                    # Prepare the broadcast data - just the actual event data
                    broadcast_data = (
                        actual_data
                        if isinstance(actual_data, dict)
                        else {"data": actual_data}
                    )

                    # Use the full event_type (e.g., "hook.pre_tool") as the event name
                    # The normalizer handles dotted names and will extract type and subtype correctly
                    self.server.broadcaster.broadcast_event(event_type, broadcast_data)

                    self.stats["events_relayed"] += 1
                    self.stats["last_relay_time"] = datetime.now().isoformat()

                    if self.debug:
                        logger.debug(
                            f"[DirectRelay] Broadcasted hook event: {event_type}"
                        )
                else:
                    logger.warning(
                        f"[DirectRelay] Server broadcaster not available for {event_type}"
                    )
                    self.stats["events_failed"] += 1

        except Exception as e:
            self.stats["events_failed"] += 1
            logger.error(f"[DirectRelay] Failed to relay event {event_type}: {e}")

    def stop(self) -> None:
        """Stop the relay."""
        self.enabled = False
        self.connected = False
        # EventBus doesn't provide an off() method, so listeners remain
        # but the enabled flag prevents processing
        logger.info("[DirectRelay] Stopped")

    def get_stats(self) -> dict:
        """Get relay statistics."""
        return {
            "enabled": self.enabled,
            "connected": self.connected,
            "events_relayed": self.stats["events_relayed"],
            "events_failed": self.stats["events_failed"],
            "last_relay_time": self.stats["last_relay_time"],
            "has_server": self.server is not None,
            "has_broadcaster": self.server and self.server.broadcaster is not None,
        }
