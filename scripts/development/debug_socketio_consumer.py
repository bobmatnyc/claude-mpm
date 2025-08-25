#!/usr/bin/env python3
"""
Socket.IO Debug Consumer for EventBus → Dashboard pipeline testing.

WHY: This consumer subscribes to EventBus events and emits them to the Socket.IO
server in the correct format for the dashboard. It provides debugging output
to verify the event flow.

DESIGN: Acts as a bridge between EventBus and Socket.IO server, normalizing
events and providing detailed logging for debugging.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.event_bus.event_bus import EventBus
from claude_mpm.services.socketio.event_normalizer import EventNormalizer, EventSource
from claude_mpm.services.socketio.server.core import SocketIOServerCore

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SocketIODebugConsumer")


class SocketIODebugConsumer:
    """Debug consumer that bridges EventBus to Socket.IO server.

    WHY: This consumer provides visibility into the event flow and ensures
    events are properly formatted for the dashboard.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.event_bus = EventBus.get_instance()
        self.normalizer = EventNormalizer()
        self.server = None
        self.stats = {
            "events_received": 0,
            "events_emitted": 0,
            "events_failed": 0,
            "events_by_type": {},
        }
        self.running = False

    async def start(self):
        """Start the consumer and Socket.IO server."""
        logger.info("=" * 80)
        logger.info("Starting Socket.IO Debug Consumer")
        logger.info(f"Server: http://{self.host}:{self.port}")
        logger.info(f"Dashboard: http://{self.host}:{self.port}/")
        logger.info("=" * 80)

        # Start Socket.IO server
        self.server = SocketIOServerCore(self.host, self.port)
        self.server.start_sync()

        # Wait for server to be ready
        await asyncio.sleep(2)

        # Subscribe to all EventBus events
        self._subscribe_to_events()

        self.running = True
        logger.info("✅ Consumer started and listening for events")

    def _subscribe_to_events(self):
        """Subscribe to various event types on the EventBus."""
        # Hook events
        hook_events = [
            "hook.pre_tool",
            "hook.post_tool",
            "hook.pre_response",
            "hook.post_response",
            "hook.user_prompt",
            "hook.assistant_response",
        ]
        for event in hook_events:
            self.event_bus.on(event, self._handle_event)
            logger.debug(f"Subscribed to: {event}")

        # System events
        system_events = [
            "system.heartbeat",
            "system.status",
            "session.started",
            "session.ended",
            "file.created",
            "file.modified",
            "file.deleted",
            "connection.connected",
            "connection.disconnected",
        ]
        for event in system_events:
            self.event_bus.on(event, self._handle_event)
            logger.debug(f"Subscribed to: {event}")

        # Agent events
        agent_events = [
            "agent.started",
            "agent.stopped",
            "agent.delegated",
            "agent.completed",
            "subagent.start",
            "subagent.stop",
        ]
        for event in agent_events:
            self.event_bus.on(event, self._handle_event)
            logger.debug(f"Subscribed to: {event}")

        # Test events
        test_events = ["test.event", "test.start", "test.end"]
        for event in test_events:
            self.event_bus.on(event, self._handle_event)
            logger.debug(f"Subscribed to: {event}")

        logger.info(
            f"✅ Subscribed to {len(hook_events + system_events + agent_events + test_events)} event types"
        )

    def _handle_event(self, event_name: str, event_data: Any):
        """Handle an event from the EventBus.

        Args:
            event_name: The name of the event
            event_data: The event data payload
        """
        self.stats["events_received"] += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"📥 RECEIVED EVENT: {event_name}")
        logger.debug(f"Raw data: {json.dumps(event_data, default=str, indent=2)}")

        try:
            # Determine source based on event name
            source = self._determine_source(event_name)

            # Create event data in format expected by normalizer
            if isinstance(event_data, dict):
                # If data already has type/subtype, use it
                event_dict = event_data.copy()
            else:
                # Wrap simple data
                event_dict = {"value": event_data}

            # Add event name for normalizer to process
            if "." in event_name:
                parts = event_name.split(".", 1)
                event_dict["type"] = parts[0]
                event_dict["subtype"] = parts[1]
            else:
                event_dict["event"] = event_name

            # Normalize the event
            normalized = self.normalizer.normalize(event_dict, source=source)

            logger.info("📝 NORMALIZED EVENT:")
            logger.info(f"  Source: {normalized.source}")
            logger.info(f"  Type: {normalized.type}")
            logger.info(f"  Subtype: {normalized.subtype}")
            logger.debug(
                f"  Data: {json.dumps(normalized.data, default=str, indent=2)}"
            )

            # Emit to Socket.IO server
            self._emit_to_socketio(normalized.to_dict())

            # Update stats
            event_type = f"{normalized.type}.{normalized.subtype}"
            self.stats["events_by_type"][event_type] = (
                self.stats["events_by_type"].get(event_type, 0) + 1
            )
            self.stats["events_emitted"] += 1

            logger.info("✅ Event emitted successfully")

        except Exception as e:
            self.stats["events_failed"] += 1
            logger.error(f"❌ Failed to process event: {e}", exc_info=True)

    def _determine_source(self, event_name: str) -> str:
        """Determine the source based on event name."""
        if event_name.startswith("hook."):
            return EventSource.HOOK.value
        if event_name.startswith("test."):
            return EventSource.TEST.value
        if event_name.startswith("agent.") or event_name.startswith("subagent."):
            return EventSource.AGENT.value
        if event_name in ["system.heartbeat", "session.started", "session.ended"]:
            return EventSource.SYSTEM.value
        return EventSource.SYSTEM.value

    def _emit_to_socketio(self, event_data: Dict[str, Any]):
        """Emit an event to the Socket.IO server.

        WHY: This method handles the actual emission to Socket.IO,
        ensuring the event is in the correct format.
        """
        if not self.server or not self.server.running:
            logger.warning("Server not running, cannot emit event")
            return

        # Get the event loop from the server thread
        if self.server.loop and not self.server.loop.is_closed():
            # Schedule the emission in the server's event loop
            future = asyncio.run_coroutine_threadsafe(
                self._async_emit(event_data), self.server.loop
            )
            # Wait for completion (with timeout)
            try:
                future.result(timeout=5.0)
            except Exception as e:
                logger.error(f"Failed to emit event: {e}")

    async def _async_emit(self, event_data: Dict[str, Any]):
        """Asynchronously emit event to Socket.IO clients."""
        if self.server.sio:
            # Use the normalized event name
            await self.server.sio.emit("claude_event", event_data)
            logger.debug("📤 Emitted to Socket.IO: claude_event")

    def print_stats(self):
        """Print current statistics."""
        print(f"\n{'='*60}")
        print("📊 CONSUMER STATISTICS")
        print(f"  Events Received: {self.stats['events_received']}")
        print(f"  Events Emitted: {self.stats['events_emitted']}")
        print(f"  Events Failed: {self.stats['events_failed']}")
        print("\n  Events by Type:")
        for event_type, count in sorted(self.stats["events_by_type"].items()):
            print(f"    {event_type}: {count}")
        print("=" * 60)

    async def run(self):
        """Run the consumer."""
        await self.start()

        try:
            # Keep running and print stats periodically
            while self.running:
                await asyncio.sleep(30)
                self.print_stats()

        except KeyboardInterrupt:
            logger.info("\n⏹️  Shutting down consumer...")
            self.running = False
            if self.server:
                self.server.stop_sync()
            self.print_stats()


async def main():
    """Main entry point."""
    consumer = SocketIODebugConsumer()
    await consumer.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Consumer stopped")
