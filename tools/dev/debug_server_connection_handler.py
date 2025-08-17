#!/usr/bin/env python3
"""
Debug script to test the Socket.IO server's connection handler and history transmission.

WHY: The automatic history transmission appears to be broken. This script will:
1. Add detailed logging to the connection process
2. Test if _send_event_history is being called on connection
3. Debug the count/total_available bug in history responses
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.socketio_server import SocketIOServer

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class DebugSocketIOServer(SocketIOServer):
    """Extended Socket.IO server with detailed debugging."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection_debug = True

    def _register_events(self):
        """Override to add debugging to connection handler."""

        @self.sio.event
        async def connect(sid, environ, *args):
            """Debug version of connection handler."""
            self.logger.info(f"🔧 DEBUG: Connection handler called for {sid}")

            # Original connection logic
            self.clients.add(sid)
            client_addr = environ.get("REMOTE_ADDR", "unknown")
            user_agent = environ.get("HTTP_USER_AGENT", "unknown")
            self.logger.info(f"🔗 NEW CLIENT CONNECTED: {sid} from {client_addr}")
            self.logger.info(f"📱 User Agent: {user_agent[:100]}...")
            self.logger.info(f"📈 Total clients now: {len(self.clients)}")

            # Send initial status
            status_data = {
                "server": "claude-mpm-python-socketio",
                "timestamp": self.datetime.utcnow().isoformat() + "Z",
                "clients_connected": len(self.clients),
                "session_id": self.session_id,
                "claude_status": self.claude_status,
                "claude_pid": self.claude_pid,
                "server_version": "2.0.0",
                "client_id": sid,
            }

            try:
                await self.sio.emit("status", status_data, room=sid)
                await self.sio.emit(
                    "welcome",
                    {
                        "message": "Connected to Claude MPM Socket.IO server",
                        "client_id": sid,
                        "server_time": self.datetime.utcnow().isoformat() + "Z",
                    },
                    room=sid,
                )

                # DEBUG: Check event history before sending
                self.logger.info(f"🔧 DEBUG: About to send event history to {sid}")
                self.logger.info(
                    f"🔧 DEBUG: Event history length: {len(self.event_history)}"
                )
                if len(self.event_history) > 0:
                    first_event = list(self.event_history)[0]
                    self.logger.info(
                        f"🔧 DEBUG: First event type: {first_event.get('type', 'unknown')}"
                    )

                # Call the history method with debugging
                await self._debug_send_event_history(sid, limit=50)

                self.logger.debug(
                    f"✅ Sent welcome messages and event history to client {sid}"
                )
            except Exception as e:
                self.logger.error(f"❌ Failed to send welcome to client {sid}: {e}")
                import traceback

                self.logger.error(f"Stack trace: {traceback.format_exc()}")

        # Add other event handlers
        @self.sio.event
        async def disconnect(sid):
            if sid in self.clients:
                self.clients.remove(sid)
                self.logger.info(f"🔌 CLIENT DISCONNECTED: {sid}")
                self.logger.info(f"📉 Total clients now: {len(self.clients)}")

        @self.sio.event
        async def get_history(sid, data=None):
            """Debug version of get_history handler."""
            self.logger.info(f"🔧 DEBUG: get_history called by {sid} with data: {data}")
            params = data or {}
            event_types = params.get("event_types", [])
            limit = min(params.get("limit", 100), len(self.event_history))

            await self._debug_send_event_history(
                sid, event_types=event_types, limit=limit
            )

    async def _debug_send_event_history(
        self, sid: str, event_types: list = None, limit: int = 50
    ):
        """Debug version of _send_event_history with detailed logging."""
        try:
            self.logger.info(f"🔧 DEBUG: _debug_send_event_history called for {sid}")
            self.logger.info(
                f"🔧 DEBUG: Parameters - event_types: {event_types}, limit: {limit}"
            )
            self.logger.info(
                f"🔧 DEBUG: self.event_history length: {len(self.event_history)}"
            )

            if not self.event_history:
                self.logger.debug(f"No event history to send to client {sid}")
                return

            # Debug: Show what's in event_history
            sample_events = list(self.event_history)[:3]
            for i, event in enumerate(sample_events):
                self.logger.info(
                    f"🔧 DEBUG: Event {i}: {event.get('type', 'unknown')} - {event.get('timestamp', 'no timestamp')}"
                )

            # Limit to reasonable number to avoid overwhelming client
            limit = min(limit, 100)
            self.logger.info(f"🔧 DEBUG: Using limit: {limit}")

            # Get the most recent events, filtered by type if specified
            history = []
            for event in reversed(self.event_history):
                if not event_types or event.get("type") in event_types:
                    history.append(event)
                    if len(history) >= limit:
                        break

            # Reverse to get chronological order (oldest first)
            history = list(reversed(history))

            self.logger.info(f"🔧 DEBUG: Filtered history length: {len(history)}")
            self.logger.info(f"🔧 DEBUG: Total available: {len(self.event_history)}")

            if history:
                response_data = {
                    "events": history,
                    "count": len(history),
                    "total_available": len(self.event_history),
                }

                self.logger.info(f"🔧 DEBUG: About to emit 'history' event with:")
                self.logger.info(
                    f"🔧 DEBUG: - events count: {len(response_data['events'])}"
                )
                self.logger.info(f"🔧 DEBUG: - reported count: {response_data['count']}")
                self.logger.info(
                    f"🔧 DEBUG: - total_available: {response_data['total_available']}"
                )

                # Send as 'history' event that the client expects
                await self.sio.emit("history", response_data, room=sid)

                self.logger.info(
                    f"📚 Sent {len(history)} historical events to client {sid}"
                )
            else:
                self.logger.debug(
                    f"No matching events found for client {sid} with filters: {event_types}"
                )

        except Exception as e:
            self.logger.error(f"❌ Failed to send event history to client {sid}: {e}")
            import traceback

            self.logger.error(f"Stack trace: {traceback.format_exc()}")


async def main():
    """Test the debug server."""
    print("🧪 Starting Debug Socket.IO Server")
    print("=" * 50)

    # Create debug server
    server = DebugSocketIOServer(host="localhost", port=8766)  # Use different port

    try:
        # Add some sample events to the history for testing
        import json
        from datetime import datetime

        sample_events = [
            {
                "type": "test.sample1",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": {"message": "Test event 1"},
            },
            {
                "type": "test.sample2",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": {"message": "Test event 2"},
            },
        ]

        for event in sample_events:
            server.event_history.append(event)

        print(f"✅ Added {len(sample_events)} sample events to history")
        print(f"📊 Total events in history: {len(server.event_history)}")

        # Start server
        server.start()
        print("✅ Debug server started on port 8766")
        print("🧪 Connect a client to test automatic history transmission")
        print("💡 Press Ctrl+C to stop")

        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping debug server...")
        server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(0)
