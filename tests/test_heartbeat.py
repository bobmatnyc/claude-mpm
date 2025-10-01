#!/usr/bin/env python3
"""
Test script to verify Socket.IO heartbeat functionality
"""

import asyncio
import time
from datetime import datetime, timezone

import socketio


async def test_heartbeat():
    """Test heartbeat events from the server"""

    # Create a Socket.IO client
    sio = socketio.AsyncClient()

    heartbeat_received = False
    heartbeat_data = None

    @sio.on("connect")
    async def on_connect():
        print(f"[{datetime.now(timezone.utc).isoformat()}] Connected to server")
        print("Waiting for heartbeat events (every 3 minutes)...")
        print(
            "Note: For testing, you may want to temporarily reduce the interval in server.py"
        )

    @sio.on("disconnect")
    async def on_disconnect():
        print(f"[{datetime.now(timezone.utc).isoformat()}] Disconnected from server")

    @sio.on("heartbeat")
    async def on_heartbeat(data):
        nonlocal heartbeat_received, heartbeat_data
        heartbeat_received = True
        heartbeat_data = data
        print(f"\n🫀 HEARTBEAT RECEIVED at {datetime.now(timezone.utc).isoformat()}")
        print(f"  - Heartbeat #{data.get('heartbeat_number', 'unknown')}")
        print(f"  - Server uptime: {data.get('server_uptime_formatted', 'unknown')}")
        print(f"  - Connected clients: {data.get('connected_clients', 'unknown')}")
        print(f"  - Message: {data.get('message', 'No message')}")
        print(f"  - Port: {data.get('port', 'unknown')}")
        print("")

    # Connect to the server
    try:
        print(
            f"[{datetime.now(timezone.utc).isoformat()}] Connecting to Socket.IO server at http://localhost:8765..."
        )
        await sio.connect("http://localhost:8765")

        # Wait for heartbeat (3 minutes = 180 seconds, plus some buffer)
        print(
            f"[{datetime.now(timezone.utc).isoformat()}] Connected! Waiting up to 200 seconds for heartbeat..."
        )

        # Check every second for up to 200 seconds
        for i in range(200):
            if heartbeat_received:
                print("\n✅ SUCCESS: Heartbeat functionality is working!")
                break
            await asyncio.sleep(1)
            if i % 30 == 0 and i > 0:
                print(
                    f"[{datetime.now(timezone.utc).isoformat()}] Still waiting... ({i} seconds elapsed)"
                )

        if not heartbeat_received:
            print("\n⚠️ WARNING: No heartbeat received after 200 seconds")
            print("This might be normal if the server just started.")
            print("The heartbeat is sent every 3 minutes (180 seconds).")
            print(
                "\nTo test quickly, you can temporarily change the interval in server.py:"
            )
            print("  Change: await asyncio.sleep(180)")
            print("  To:     await asyncio.sleep(10)  # For testing")

        # Disconnect
        await sio.disconnect()

    except Exception as e:
        print(f"\n❌ ERROR: Failed to connect or receive heartbeat: {e}")
        print("\nMake sure the Socket.IO server is running:")
        print("  ./scripts/claude-mpm monitor --start")


if __name__ == "__main__":
    print("=" * 60)
    print("Socket.IO Heartbeat Test")
    print("=" * 60)
    print("\nThis script tests the heartbeat functionality added to the server.")
    print("Heartbeats are sent every 3 minutes to confirm Socket.IO is working.\n")

    asyncio.run(test_heartbeat())
