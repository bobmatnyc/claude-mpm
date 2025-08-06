#!/usr/bin/env python3
"""
Debug test to see exactly what events are being sent and received.
"""

import asyncio
import requests
import socketio
import time
import threading
import sys
from pathlib import Path

# Add project root to path  
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.websocket_server import SocketIOServer


async def debug_test():
    """Debug the event flow."""
    
    print("🔍 DEBUG EVENT FLOW TEST")
    print("=" * 30)
    
    # Start server
    server = SocketIOServer(host="localhost", port=8765)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    # Wait for server
    await asyncio.sleep(2)
    
    # Create client for /hook namespace
    client = socketio.AsyncClient()
    received_events = []
    
    # Listen for ALL events (not just specific ones)
    @client.event(namespace='/hook')
    async def connect():
        print("✅ Connected to /hook")
    
    # Catch-all event handler to see what we receive
    original_on = client.on
    def debug_on(event, handler=None, namespace=None):
        if handler is None:
            # This is a decorator
            def decorator_wrapper(func):
                print(f"🎧 Registering handler for '{event}' in namespace '{namespace}'")
                async def debug_wrapper(*args, **kwargs):
                    print(f"📨 DEBUG: Received '{event}' with args: {args}")
                    received_events.append((event, args))
                    return await func(*args, **kwargs)
                return original_on(event, debug_wrapper, namespace)
            return decorator_wrapper
        else:
            # Direct call
            print(f"🎧 Registering handler for '{event}' in namespace '{namespace}'")
            async def debug_wrapper(*args, **kwargs):
                print(f"📨 DEBUG: Received '{event}' with args: {args}")
                received_events.append((event, args))
                return await handler(*args, **kwargs)
            return original_on(event, debug_wrapper, namespace)
    
    client.on = debug_on
    
    # Register specific handlers
    @client.on('pre_tool', namespace='/hook')
    async def on_pre_tool(data):
        print(f"📨 PRE_TOOL: {data}")
    
    @client.on('test_connection', namespace='/hook')
    async def on_test_connection(data):
        print(f"📨 TEST_CONNECTION: {data}")
    
    # Connect
    await client.connect('http://localhost:8765', namespaces=['/hook'])
    await asyncio.sleep(1)
    
    # Send event via HTTP
    print("📤 Sending hook event via HTTP...")
    response = requests.post(
        "http://localhost:8765/emit",
        json={
            "namespace": "/hook",
            "event": "pre_tool",
            "data": {"tool_name": "debug_test", "session_id": "debug_123"}
        },
        timeout=5.0
    )
    
    print(f"📤 HTTP Response: {response.status_code} - {response.json()}")
    
    # Wait and see what we received
    await asyncio.sleep(3)
    
    print(f"\n🔍 DEBUG RESULTS:")
    print(f"📊 Total events received: {len(received_events)}")
    for event_name, args in received_events:
        print(f"   - {event_name}: {args}")
    
    # Cleanup
    await client.disconnect()
    server.stop()


if __name__ == "__main__":
    asyncio.run(debug_test())