#!/usr/bin/env python3
"""
Simple test to diagnose why events aren't appearing in the dashboard.
"""

import asyncio
import json
from datetime import datetime

import socketio

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


async def main():
    print(f"\n{BOLD}Testing SocketIO Event Flow{RESET}\n")

    # Create a SocketIO client
    sio = socketio.AsyncClient(logger=True, engineio_logger=True)

    # Track what we receive
    received_events = []
    connected = False

    @sio.event
    async def connect():
        nonlocal connected
        connected = True
        print(f"{GREEN}✓ Connected to server{RESET}")

    @sio.event
    async def disconnect():
        print(f"{YELLOW}⚠ Disconnected from server{RESET}")

    @sio.event
    async def connect_error(data):
        print(f"{RED}✗ Connection error: {data}{RESET}")

    @sio.event
    async def history(data):
        """Receive cached event history."""
        events = data.get("events", [])
        print(f"{BLUE}📚 Received history with {len(events)} events{RESET}")
        for event in events[:5]:  # Show first 5
            print(f"  - {event.get('event', 'unknown')}: {event.get('message', '')}")
        received_events.extend(events)

    @sio.event
    async def claude_event(data):
        """Receive real-time Claude events."""
        print(f"{GREEN}📨 Received claude_event:{RESET}")
        print(f"  Event: {data.get('event', 'unknown')}")
        print(f"  Data: {json.dumps(data, indent=2)}")
        received_events.append(data)

    @sio.event
    async def system_event(data):
        """Receive system events."""
        print(f"{BLUE}⚙️ Received system_event:{RESET}")
        print(f"  Event: {data.get('event', 'unknown')}")
        print(f"  Data: {json.dumps(data, indent=2)}")
        received_events.append(data)

    @sio.event
    async def status(data):
        """Receive status response."""
        print(f"{BLUE}📊 Received status:{RESET}")
        print(f"  {json.dumps(data, indent=2)}")

    try:
        # Connect to the server
        print(f"{YELLOW}Connecting to http://localhost:8765...{RESET}")
        await sio.connect("http://localhost:8765")

        if not connected:
            print(f"{RED}Failed to connect!{RESET}")
            return

        # Wait a moment for history event
        await asyncio.sleep(2)

        # Request status
        print(f"\n{YELLOW}Requesting server status...{RESET}")
        await sio.emit("get_status")
        await asyncio.sleep(1)

        # Send test events
        print(f"\n{YELLOW}Sending test events...{RESET}")

        test_events = [
            {
                "event": "TestStart",
                "message": "Starting diagnostic test",
                "timestamp": datetime.now().isoformat(),
                "source": "test_script",
            },
            {
                "event": "SubagentStart",
                "agent": "TestAgent",
                "task": "Testing event flow",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "event": "ToolCall",
                "tool": "Diagnostic",
                "args": {"test": True},
                "timestamp": datetime.now().isoformat(),
            },
            {
                "event": "SubagentStop",
                "agent": "TestAgent",
                "result": "Test completed",
                "timestamp": datetime.now().isoformat(),
            },
        ]

        for event in test_events:
            print(f"  Sending: {event['event']}")
            await sio.emit("claude_event", event)
            await asyncio.sleep(0.5)

        # Wait for responses
        print(f"\n{YELLOW}Waiting for event echo/broadcast...{RESET}")
        await asyncio.sleep(3)

        # Summary
        print(f"\n{BOLD}{'='*50}{RESET}")
        print(f"{BOLD}Summary:{RESET}")
        print(f"  Connected: {GREEN if connected else RED}{connected}{RESET}")
        print(f"  Events received: {len(received_events)}")

        if len(received_events) == 0:
            print(f"\n{RED}❌ No events received!{RESET}")
            print(f"\n{BOLD}Possible issues:{RESET}")
            print("  1. Server not broadcasting events")
            print("  2. Event handlers not registered")
            print("  3. Server internal error")
            print(f"\n{BOLD}Check server logs:{RESET}")
            print(
                "  tail -f /Users/masa/Projects/claude-mpm/.claude-mpm/socketio-server.log"
            )
        else:
            print(f"\n{GREEN}✅ Event flow is working!{RESET}")
            print(f"\n{BOLD}Next steps:{RESET}")
            print("  1. Open http://localhost:8765 in browser")
            print("  2. Check browser console for errors")
            print("  3. Verify events appear in dashboard")

        await sio.disconnect()

    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
