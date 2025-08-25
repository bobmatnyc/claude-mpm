#!/usr/bin/env python3
"""
Socket.IO Event Monitor - Listen and display events from the Socket.IO server.

WHY: This script acts as a Socket.IO client that connects to the server and
displays all events being broadcast, helping debug the event pipeline.

USAGE:
    python scripts/monitor_socketio_events.py [--host localhost] [--port 8765]
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List

# Socket.IO client import
try:
    import socketio

    SOCKETIO_CLIENT_AVAILABLE = True
except ImportError:
    print(
        "❌ python-socketio not installed. Install with: pip install python-socketio[client]"
    )
    SOCKETIO_CLIENT_AVAILABLE = False
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SocketIOMonitor")


class SocketIOMonitor:
    """Monitor Socket.IO events from the server."""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self.sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        self.connected = False
        self.event_count = 0
        self.event_history: List[Dict[str, Any]] = []
        self.event_types = {}

        # Setup event handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup Socket.IO event handlers."""

        @self.sio.event
        async def connect():
            """Handle connection event."""
            self.connected = True
            print("\n" + "=" * 80)
            print(f"✅ CONNECTED to Socket.IO server at {self.url}")
            print("=" * 80)
            print("📡 Listening for events...")
            print("=" * 80 + "\n")

        @self.sio.event
        async def disconnect():
            """Handle disconnection event."""
            self.connected = False
            print("\n" + "=" * 80)
            print("❌ DISCONNECTED from Socket.IO server")
            print(f"📊 Total events received: {self.event_count}")
            print("=" * 80 + "\n")

        @self.sio.event
        async def connect_error(data):
            """Handle connection error."""
            print(f"\n❌ Connection error: {data}")

        # Handler for normalized events
        @self.sio.on("claude_event")
        async def on_claude_event(data):
            """Handle claude_event (normalized events)."""
            self._process_event("claude_event", data)

        # Handler for system events
        @self.sio.on("system_event")
        async def on_system_event(data):
            """Handle system_event."""
            self._process_event("system_event", data)

        # Handler for hook events (legacy)
        @self.sio.on("hook_event")
        async def on_hook_event(data):
            """Handle hook_event (legacy format)."""
            self._process_event("hook_event", data)

        # Handler for session events
        @self.sio.on("session_event")
        async def on_session_event(data):
            """Handle session_event."""
            self._process_event("session_event", data)

        # Handler for file events
        @self.sio.on("file_event")
        async def on_file_event(data):
            """Handle file_event."""
            self._process_event("file_event", data)

        # Handler for connection events
        @self.sio.on("connection_event")
        async def on_connection_event(data):
            """Handle connection_event."""
            self._process_event("connection_event", data)

        # Catch-all handler for any other events
        @self.sio.on("*")
        async def catch_all(event, *args):
            """Catch all other events."""
            if event not in [
                "connect",
                "disconnect",
                "connect_error",
                "claude_event",
                "system_event",
                "hook_event",
                "session_event",
                "file_event",
                "connection_event",
            ]:
                self._process_event(event, args[0] if args else None)

    def _process_event(self, event_name: str, data: Any):
        """Process and display an event."""
        self.event_count += 1

        # Store in history
        event_record = {
            "index": self.event_count,
            "timestamp": datetime.now().isoformat(),
            "event_name": event_name,
            "data": data,
        }
        self.event_history.append(event_record)

        # Track event types
        if isinstance(data, dict):
            event_type = data.get("type", "unknown")
            event_subtype = data.get("subtype", "")
            full_type = f"{event_type}.{event_subtype}" if event_subtype else event_type
            self.event_types[full_type] = self.event_types.get(full_type, 0) + 1
        else:
            self.event_types[event_name] = self.event_types.get(event_name, 0) + 1

        # Display the event
        self._display_event(event_record)

    def _display_event(self, event: Dict[str, Any]):
        """Display an event with formatting."""
        print(f"\n{'='*60}")
        print(f"📨 EVENT #{event['index']} | {event['timestamp']}")
        print(f"{'='*60}")
        print(f"Event Name: {event['event_name']}")

        data = event["data"]
        if isinstance(data, dict):
            # Display normalized event fields
            if "source" in data:
                print(f"Source: {data.get('source', 'N/A')}")
            if "type" in data:
                print(f"Type: {data.get('type', 'N/A')}")
            if "subtype" in data:
                print(f"Subtype: {data.get('subtype', 'N/A')}")
            if "timestamp" in data:
                print(f"Event Time: {data.get('timestamp', 'N/A')}")

            # Display data payload
            if "data" in data:
                print("\nPayload:")
                payload = data["data"]
                if isinstance(payload, dict):
                    for key, value in payload.items():
                        if isinstance(value, (dict, list)):
                            print(f"  {key}: {json.dumps(value, indent=4)}")
                        else:
                            print(f"  {key}: {value}")
                else:
                    print(f"  {payload}")
            else:
                # Display all non-metadata fields
                print("\nData:")
                for key, value in data.items():
                    if key not in ["source", "type", "subtype", "timestamp", "event"]:
                        if isinstance(value, (dict, list)):
                            print(f"  {key}: {json.dumps(value, indent=4)}")
                        else:
                            print(f"  {key}: {value}")
        else:
            print(f"Data: {data}")

    def print_summary(self):
        """Print a summary of received events."""
        print("\n" + "=" * 80)
        print("📊 EVENT SUMMARY")
        print("=" * 80)
        print(f"Total Events: {self.event_count}")
        print("\nEvent Types:")
        for event_type, count in sorted(self.event_types.items()):
            print(f"  {event_type}: {count}")
        print("=" * 80)

    async def connect(self):
        """Connect to the Socket.IO server."""
        print(f"\n🔌 Connecting to {self.url}...")
        try:
            await self.sio.connect(self.url)
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the Socket.IO server."""
        if self.connected:
            await self.sio.disconnect()

    async def run(self, duration: int = None):
        """Run the monitor for a specified duration or until interrupted.

        Args:
            duration: Optional duration in seconds to run the monitor
        """
        if not await self.connect():
            return

        try:
            if duration:
                print(f"\n⏱️  Monitoring for {duration} seconds...")
                await asyncio.sleep(duration)
            else:
                print("\n⏱️  Monitoring... (Press Ctrl+C to stop)")
                while self.connected:
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping monitor...")

        finally:
            await self.disconnect()
            self.print_summary()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor Socket.IO events from the server"
    )
    parser.add_argument(
        "--host", default="localhost", help="Server host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="Server port (default: 8765)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Duration to monitor in seconds (default: run until interrupted)",
    )

    args = parser.parse_args()

    monitor = SocketIOMonitor(args.host, args.port)
    await monitor.run(args.duration)


if __name__ == "__main__":
    if not SOCKETIO_CLIENT_AVAILABLE:
        sys.exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped")
