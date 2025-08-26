"""Direct EventBus to Socket.IO relay that uses server broadcaster.

This module provides a relay that connects EventBus directly to the
Socket.IO server's broadcaster, avoiding the client loopback issue.

IMPORTANT - Claude Event Format:
Claude sends hook events with these REQUIRED fields:
- hook_event_name: The event type (UserPromptSubmit, PreToolUse, PostToolUse, etc.)
- hook_event_type: Usually same as hook_event_name
- hook_input_data: Contains the actual event data
- sessionId: Session identifier
- timestamp: ISO format timestamp

DO NOT use "event" or "type" fields - use "hook_event_name" instead!
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
        self.connection_retries = 0
        self.max_retries = 10
        self.retry_delay = 1.0  # Start with 1 second

    def start(self) -> None:
        """Start the relay by subscribing to EventBus events with retry logic."""
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

        # Check and log broadcaster availability with retry logic
        broadcaster_available = self._check_broadcaster_with_retry()

        logger.info(
            f"[DirectRelay] Server broadcaster available: {broadcaster_available}"
        )
        if not broadcaster_available:
            if not self.server:
                logger.warning(
                    "[DirectRelay] No server instance provided - events will not be relayed!"
                )
            elif not hasattr(self.server, "broadcaster"):
                logger.warning(
                    "[DirectRelay] Server has no broadcaster attribute - events will not be relayed!"
                )
            else:
                logger.warning(
                    "[DirectRelay] Server broadcaster is None after retries - events will not be relayed!"
                )

        logger.info(f"[DirectRelay] EventBus instance: {self.event_bus is not None}")

        # Mark as connected after successful subscription
        self.connected = broadcaster_available
        logger.info(f"[DirectRelay] Started with connection status: {self.connected}")

    def _check_broadcaster_with_retry(self) -> bool:
        """Check broadcaster availability with exponential backoff retry.

        Returns:
            True if broadcaster is available, False after max retries
        """
        import time

        retry_delay = self.retry_delay

        for attempt in range(self.max_retries):
            broadcaster_available = (
                self.server
                and hasattr(self.server, "broadcaster")
                and self.server.broadcaster is not None
            )

            if broadcaster_available:
                self.connection_retries = 0  # Reset counter on success
                return True

            if attempt < self.max_retries - 1:
                logger.info(
                    f"[DirectRelay] Broadcaster not ready, retry {attempt + 1}/{self.max_retries} "
                    f"in {retry_delay:.1f}s"
                )
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30.0)  # Exponential backoff, max 30s
            else:
                logger.error(
                    f"[DirectRelay] Broadcaster not available after {self.max_retries} attempts"
                )

        return False

    def _handle_hook_event(self, event_type: str, data: Any):
        """Internal method to handle hook events and broadcast them.

        Args:
            event_type: The event type (e.g., "hook.pre_tool")
            data: The event data
        """
        try:
            # Enhanced debug logging for troubleshooting
            if self.debug:
                logger.debug(f"[DirectRelay] Received event: {event_type}")
                logger.debug(f"[DirectRelay] Event data type: {type(data).__name__}")
                logger.debug(
                    f"[DirectRelay] Event data keys: {list(data.keys()) if isinstance(data, dict) else 'not-dict'}"
                )
                logger.debug(
                    f"[DirectRelay] Relay state - enabled: {self.enabled}, connected: {self.connected}"
                )
                logger.debug(
                    f"[DirectRelay] Server state - has_server: {self.server is not None}, has_broadcaster: {self.server and hasattr(self.server, 'broadcaster') and self.server.broadcaster is not None}"
                )

            # Always log reception of important events
            if event_type in [
                "hook.pre_tool",
                "hook.post_tool",
                "hook.user_prompt",
                "hook.subagent_stop",
            ]:
                logger.info(f"[DirectRelay] Processing important event: {event_type}")

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
                    try:
                        self.server.broadcaster.broadcast_event(
                            event_type, broadcast_data
                        )
                        self.stats["events_relayed"] += 1
                        self.stats["last_relay_time"] = datetime.now().isoformat()

                        # Reset retry counter on successful broadcast
                        if self.connection_retries > 0:
                            self.connection_retries = 0
                            self.connected = True
                            logger.info("[DirectRelay] Connection restored")

                        if self.debug:
                            logger.debug(
                                f"[DirectRelay] Broadcasted hook event: {event_type}"
                            )
                    except Exception as broadcast_error:
                        logger.error(
                            f"[DirectRelay] Broadcast failed for {event_type}: {broadcast_error}"
                        )
                        self.stats["events_failed"] += 1

                        # Try to reconnect if broadcast fails
                        if self.connection_retries < self.max_retries:
                            self.connection_retries += 1
                            self.connected = self._check_broadcaster_with_retry()
                            if self.connected:
                                # Retry the broadcast
                                try:
                                    self.server.broadcaster.broadcast_event(
                                        event_type, broadcast_data
                                    )
                                    self.stats["events_relayed"] += 1
                                    self.stats[
                                        "events_failed"
                                    ] -= 1  # Undo the failure count
                                    logger.info(
                                        f"[DirectRelay] Retry successful for {event_type}"
                                    )
                                except:
                                    pass  # Already counted as failed
                else:
                    # Enhanced logging when broadcaster is not available
                    logger.warning(
                        f"[DirectRelay] Server broadcaster not available for {event_type}"
                    )
                    if self.server:
                        logger.warning(
                            "[DirectRelay] Server exists but broadcaster is None"
                        )
                        logger.warning(
                            f"[DirectRelay] Server type: {type(self.server).__name__}"
                        )
                        logger.warning(
                            f"[DirectRelay] Server has broadcaster attr: {hasattr(self.server, 'broadcaster')}"
                        )
                        if hasattr(self.server, "broadcaster"):
                            logger.warning(
                                f"[DirectRelay] Broadcaster value: {self.server.broadcaster}"
                            )
                    else:
                        logger.warning("[DirectRelay] Server is None")
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
