#!/usr/bin/env python3
"""Monitor dashboard events to verify hook event flow.

This script connects to the dashboard and monitors incoming events
to verify that Claude hook events are being properly received.
"""

import asyncio
import json
import signal
import sys
from datetime import datetime

try:
    import aiohttp
    import socketio
except ImportError:
    print("Please install required packages: pip install aiohttp python-socketio")
    sys.exit(1)


class DashboardMonitor:
    """Monitor dashboard events."""

    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.sio = socketio.AsyncClient()
        self.event_count = 0
        self.running = True

        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register SocketIO event handlers."""

        @self.sio.event
        async def connect():
            print(f"✅ Connected to dashboard at {self.base_url}")
            print("Monitoring for events...")
            print("-" * 60)

        @self.sio.event
        async def disconnect():
            print("\n❌ Disconnected from dashboard")

        @self.sio.event
        async def connect_error(data):
            print(f"❌ Connection error: {data}")

        # Monitor various event types
        @self.sio.on("*")
        async def catch_all(event, data):
            """Catch all events."""
            self.event_count += 1
            timestamp = datetime.now().isoformat()
            print(f"\n[{timestamp}] Event #{self.event_count}")
            print(f"  Type: {event}")

            # Pretty print the data
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        print(f"  {key}: {json.dumps(value, indent=4)}")
                    else:
                        print(f"  {key}: {value}")
            else:
                print(f"  Data: {data}")
            print("-" * 60)

        # Specific handlers for known event types
        @self.sio.on("user_prompt")
        async def on_user_prompt(data):
            print(f"📝 User Prompt: {data.get('prompt_preview', 'N/A')}")

        @self.sio.on("pre_tool")
        async def on_pre_tool(data):
            print(f"🔧 Pre-Tool: {data.get('tool_name', 'N/A')}")
            if data.get("tool_name") == "Task":
                details = data.get("delegation_details", {})
                print(
                    f"   → Delegating to {details.get('agent_type', 'unknown')} agent"
                )

        @self.sio.on("post_tool")
        async def on_post_tool(data):
            status = "✅" if data.get("success") else "❌"
            print(f"🔧 Post-Tool: {data.get('tool_name', 'N/A')} {status}")

        @self.sio.on("subagent_start")
        async def on_subagent_start(data):
            print(f"🤖 Subagent Start: {data.get('agent_type', 'N/A')}")

        @self.sio.on("subagent_stop")
        async def on_subagent_stop(data):
            print(
                f"🤖 Subagent Stop: {data.get('agent_type', 'N/A')} - {data.get('reason', 'N/A')}"
            )

        @self.sio.on("stop")
        async def on_stop(data):
            print(f"🛑 Stop: {data.get('reason', 'N/A')}")

    async def check_health(self) -> bool:
        """Check if dashboard is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"Dashboard health: {data}")
                        return True
                    print(f"Dashboard health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"Failed to check dashboard health: {e}")
            return False

    async def test_http_endpoint(self):
        """Test the HTTP event endpoint."""
        print("\nTesting HTTP event endpoint...")
        test_event = {
            "hook_event_name": "TestEvent",
            "type": "test",
            "data": {"message": "Testing HTTP endpoint"},
            "timestamp": datetime.now().isoformat(),
        }

        try:
            async with aiohttp.ClientSession() as session, session.post(
                f"{self.base_url}/api/events",
                json=test_event,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 204:
                    print("✅ HTTP endpoint test successful (204 No Content)")
                    return True
                text = await response.text()
                print(f"❌ HTTP endpoint returned {response.status}: {text}")
                return False
        except Exception as e:
            print(f"❌ Failed to test HTTP endpoint: {e}")
            return False

    async def monitor(self):
        """Start monitoring dashboard events."""
        print(f"\nConnecting to dashboard at {self.base_url}...")

        # Check health first
        if not await self.check_health():
            print("⚠️ Dashboard may not be healthy, attempting connection anyway...")

        # Test HTTP endpoint
        await self.test_http_endpoint()

        # Connect via SocketIO
        try:
            await self.sio.connect(self.base_url, namespaces=["/", "/hook", "/claude"])

            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Failed to connect: {e}")
        finally:
            if self.sio.connected:
                await self.sio.disconnect()

    def stop(self):
        """Stop monitoring."""
        self.running = False


async def main():
    """Main entry point."""
    monitor = DashboardMonitor()

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\nStopping monitor...")
        monitor.stop()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        await monitor.monitor()
    except KeyboardInterrupt:
        print("\n\nMonitor stopped by user")

    print(f"\nTotal events received: {monitor.event_count}")


if __name__ == "__main__":
    print("=" * 60)
    print("Dashboard Event Monitor")
    print("=" * 60)
    print("\nThis tool monitors events coming into the dashboard.")
    print("Run the test script in another terminal to send events.")
    print("\nPress Ctrl+C to stop monitoring\n")

    asyncio.run(main())
