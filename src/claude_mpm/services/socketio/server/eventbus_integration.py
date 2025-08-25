"""EventBus integration for Socket.IO server.

WHY this integration module:
- Adds EventBus relay to Socket.IO server without modifying core
- Maintains backward compatibility with existing server
- Easy to enable/disable via configuration
- Provides clean separation of concerns
"""

import logging
from typing import Optional

from claude_mpm.services.event_bus import EventBus
from claude_mpm.services.event_bus.config import get_config
from claude_mpm.services.event_bus.direct_relay import DirectSocketIORelay

logger = logging.getLogger(__name__)


class EventBusIntegration:
    """Integrates EventBus relay with Socket.IO server.

    WHY integration class:
    - Encapsulates EventBus setup and teardown
    - Provides lifecycle management for relay
    - Handles configuration and error cases
    - Can be easily added to existing server
    """

    def __init__(self, server_instance=None):
        """Initialize EventBus integration.

        Args:
            server_instance: Optional Socket.IO server instance
        """
        self.server = server_instance
        self.relay: Optional[DirectSocketIORelay] = None
        self.event_bus: Optional[EventBus] = None
        self.config = get_config()
        self.enabled = self.config.enabled and self.config.relay_enabled

    def setup(self, port: Optional[int] = None) -> bool:
        """Set up EventBus and relay.

        Args:
            port: Optional Socket.IO server port

        Returns:
            bool: True if setup successful
        """
        from datetime import datetime

        print(
            f"[{datetime.now().isoformat()}] EventBusIntegration.setup() called",
            flush=True,
        )

        if not self.enabled:
            logger.info("EventBus integration disabled by configuration")
            print(
                f"[{datetime.now().isoformat()}] EventBus integration disabled by configuration",
                flush=True,
            )
            return False

        try:
            # Get EventBus instance
            print(
                f"[{datetime.now().isoformat()}] Getting EventBus instance...",
                flush=True,
            )
            self.event_bus = EventBus.get_instance()
            print(
                f"[{datetime.now().isoformat()}] EventBus instance obtained", flush=True
            )

            # Apply configuration
            self.config.apply_to_eventbus(self.event_bus)

            # Create direct relay that uses server's broadcaster
            print(
                f"[{datetime.now().isoformat()}] Creating DirectSocketIORelay...",
                flush=True,
            )
            if self.server:
                self.relay = DirectSocketIORelay(self.server)
                print(
                    f"[{datetime.now().isoformat()}] DirectSocketIORelay created with server instance",
                    flush=True,
                )
            else:
                logger.warning("No server instance provided, relay won't work")
                print(
                    f"[{datetime.now().isoformat()}] WARNING: No server instance for relay",
                    flush=True,
                )
                return False

            # Start the relay
            print(f"[{datetime.now().isoformat()}] Starting relay...", flush=True)
            self.relay.start()
            print(f"[{datetime.now().isoformat()}] Relay started", flush=True)

            logger.info("EventBus integration setup complete with DirectSocketIORelay")
            print(
                f"[{datetime.now().isoformat()}] EventBus integration setup complete with DirectSocketIORelay",
                flush=True,
            )
            return True

        except Exception as e:
            logger.error(f"Failed to setup EventBus integration: {e}")
            print(
                f"[{datetime.now().isoformat()}] Failed to setup EventBus integration: {e}",
                flush=True,
            )
            import traceback

            traceback.print_exc()
            self.enabled = False
            return False

    def teardown(self) -> None:
        """Tear down EventBus integration."""
        if self.relay:
            try:
                self.relay.stop()
                logger.info("EventBus relay stopped")
            except Exception as e:
                logger.error(f"Error stopping relay: {e}")
            finally:
                self.relay = None

    def is_active(self) -> bool:
        """Check if integration is active.

        Returns:
            bool: True if relay is active and connected
        """
        return self.enabled and self.relay is not None and self.relay.enabled

    def get_stats(self) -> dict:
        """Get integration statistics.

        Returns:
            dict: Combined stats from EventBus and relay
        """
        stats = {"enabled": self.enabled, "active": self.is_active()}

        if self.event_bus:
            stats["eventbus"] = self.event_bus.get_stats()

        if self.relay:
            stats["relay"] = self.relay.get_stats()

        return stats


def integrate_with_server(
    server_instance, port: Optional[int] = None
) -> EventBusIntegration:
    """Helper function to integrate EventBus with a Socket.IO server.

    Args:
        server_instance: Socket.IO server instance
        port: Optional server port

    Returns:
        EventBusIntegration: The integration instance
    """
    integration = EventBusIntegration(server_instance)
    integration.setup(port or getattr(server_instance, "port", 8765))
    return integration


# Monkey-patch helper for existing server
def patch_socketio_server(server_class):
    """Monkey-patch an existing Socket.IO server class to add EventBus.

    WHY monkey-patching:
    - Allows integration without modifying existing code
    - Can be applied selectively based on configuration
    - Easy to remove or disable

    Args:
        server_class: The server class to patch
    """
    original_init = server_class.__init__
    original_start = getattr(server_class, "start_sync", None) or getattr(
        server_class, "start", None
    )
    original_stop = getattr(server_class, "stop_sync", None) or getattr(
        server_class, "stop", None
    )

    def patched_init(self, *args, **kwargs):
        """Patched __init__ that adds EventBus integration."""
        original_init(self, *args, **kwargs)
        self._eventbus_integration = EventBusIntegration(self)

    def patched_start(self, *args, **kwargs):
        """Patched start method that sets up EventBus."""
        # Call original start
        result = original_start(self, *args, **kwargs) if original_start else None

        # Setup EventBus integration
        if hasattr(self, "_eventbus_integration"):
            port = getattr(self, "port", 8765)
            self._eventbus_integration.setup(port)

        return result

    def patched_stop(self, *args, **kwargs):
        """Patched stop method that tears down EventBus."""
        # Teardown EventBus first
        if hasattr(self, "_eventbus_integration"):
            self._eventbus_integration.teardown()

        # Call original stop
        if original_stop:
            return original_stop(self, *args, **kwargs)
        return None

    # Apply patches
    server_class.__init__ = patched_init
    if original_start:
        setattr(
            server_class,
            "start_sync" if hasattr(server_class, "start_sync") else "start",
            patched_start,
        )
    if original_stop:
        setattr(
            server_class,
            "stop_sync" if hasattr(server_class, "stop_sync") else "stop",
            patched_stop,
        )

    logger.info(f"Patched {server_class.__name__} with EventBus integration")
