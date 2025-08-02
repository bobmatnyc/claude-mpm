#!/usr/bin/env python3
"""
Quick Socket.IO connection test.
"""

import asyncio
import sys
from pathlib import Path
import socketio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


async def quick_test():
    """Quick Socket.IO connection test."""
    sio = socketio.AsyncClient()
    
    connected = False
    events = []
    
    @sio.event
    async def connect():
        nonlocal connected
        connected = True
        print("✅ Connected to Socket.IO server")
        
    @sio.event
    async def welcome(data):
        events.append(('welcome', data))
        print(f"📨 Welcome event: {data}")
        
    @sio.event  
    async def status(data):
        events.append(('status', data))
        print(f"📊 Status: Server={data.get('server')}, Clients={data.get('clients_connected')}")
        
    @sio.event
    async def claude_event(data):
        events.append(('claude_event', data))
        event_type = data.get('type', 'unknown')
        print(f"🔧 Claude event: {event_type}")
    
    try:
        # Connect
        print("🔌 Connecting to Socket.IO server at http://localhost:8765...")
        await sio.connect('http://localhost:8765')
        
        # Wait a bit to receive events
        await asyncio.sleep(2)
        
        # Send a test event
        print("\n📤 Sending test event...")
        await sio.emit('test', {'message': 'Hello from test!'})
        
        # Wait for any responses
        await asyncio.sleep(1)
        
        # Print summary
        print(f"\n📊 Summary:")
        print(f"  Connected: {'✅ Yes' if connected else '❌ No'}")
        print(f"  Transport: {sio.transport()}")
        print(f"  Session ID: {sio.sid}")
        print(f"  Events received: {len(events)}")
        
        if events:
            print("\n  Event types:")
            event_types = {}
            for event_type, _ in events:
                event_types[event_type] = event_types.get(event_type, 0) + 1
            for event_type, count in event_types.items():
                print(f"    - {event_type}: {count}")
        
        # Disconnect
        await sio.disconnect()
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(quick_test())
    sys.exit(0 if success else 1)