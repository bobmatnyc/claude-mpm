#!/usr/bin/env python3
"""
Test direct method calls to isolate the issue.
"""

import asyncio
import socketio
import time
import threading
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.websocket_server import SocketIOServer


async def direct_emit_test():
    """Test direct emit method calls."""
    
    print("🔬 DIRECT EMIT TEST")
    print("=" * 25)
    
    # Start server
    server = SocketIOServer(host="localhost", port=8765)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    await asyncio.sleep(2)
    
    # Create client
    client = socketio.AsyncClient()
    received_events = []
    
    @client.event(namespace='/hook')
    async def connect():
        print("✅ Connected to /hook")
    
    @client.event(namespace='/hook')
    async def pre_tool(data):
        print(f"📨 DIRECT PRE_TOOL: {data}")
        received_events.append(('pre_tool', data))
    
    # Connect
    await client.connect('http://localhost:8765', namespaces=['/hook'])
    await asyncio.sleep(1)
    
    print("📤 Calling server.hook_pre_tool() directly...")
    
    # Call the server method directly (bypasses HTTP)
    server.hook_pre_tool("direct_test_tool", "direct_session_123")
    
    # Wait for event
    await asyncio.sleep(2)
    
    print(f"\n🔬 DIRECT TEST RESULTS:")
    print(f"📊 Events received: {len(received_events)}")
    for event_name, data in received_events:
        print(f"   - {event_name}: {data}")
    
    # Cleanup
    await client.disconnect()
    server.stop()
    
    return len(received_events) > 0


if __name__ == "__main__":
    success = asyncio.run(direct_emit_test())
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILURE'}: Direct emit test")
    exit(0 if success else 1)