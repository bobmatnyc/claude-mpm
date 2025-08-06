#!/usr/bin/env python3
"""
Minimal Socket.IO test to identify the core issue.

This test creates the simplest possible Socket.IO server and client
to verify basic functionality is working.
"""

import asyncio
import socketio
from aiohttp import web
import threading
import time


class MinimalSocketIOTest:
    """Minimal Socket.IO test."""
    
    def __init__(self):
        self.received_events = []
        
    async def run_test(self):
        """Run minimal test."""
        
        print("🧪 MINIMAL SOCKET.IO TEST")
        print("=" * 30)
        
        # Create Socket.IO server
        sio = socketio.AsyncServer(cors_allowed_origins="*")
        app = web.Application()
        sio.attach(app)
        
        # Event handlers
        @sio.event
        async def connect(sid, environ):
            print(f"✅ Client {sid} connected")
            # Send immediate test event
            await sio.emit('welcome', {'message': 'Hello from server!'}, to=sid)
            
        @sio.event
        async def disconnect(sid):
            print(f"❌ Client {sid} disconnected")
        
        # HTTP endpoint to trigger events
        async def trigger_event(request):
            await sio.emit('test_broadcast', {'message': 'Broadcast test'})
            return web.json_response({'status': 'event sent'})
        
        app.router.add_post('/trigger', trigger_event)
        
        # Start server in background
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8765)
        await site.start()
        print("🚀 Minimal server started on port 8765")
        
        # Give server time to start
        await asyncio.sleep(0.5)
        
        # Create client
        client = socketio.AsyncClient()
        
        @client.event
        async def connect():
            print("🔌 Client connected to server")
            
        @client.event
        async def welcome(data):
            print(f"📨 Received welcome: {data}")
            self.received_events.append(('welcome', data))
            
        @client.event
        async def test_broadcast(data):
            print(f"📨 Received broadcast: {data}")
            self.received_events.append(('test_broadcast', data))
        
        # Connect client
        await client.connect('http://localhost:8765')
        await asyncio.sleep(1)
        
        # Test HTTP trigger
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:8765/trigger') as resp:
                result = await resp.json()
                print(f"📤 Trigger result: {result}")
        
        # Wait for events
        await asyncio.sleep(2)
        
        # Report results
        print(f"\n📊 Events received: {len(self.received_events)}")
        for event_name, event_data in self.received_events:
            print(f"   - {event_name}: {event_data}")
        
        if len(self.received_events) >= 2:  # welcome + test_broadcast
            print("✅ SUCCESS: Basic Socket.IO functionality works!")
        else:
            print("❌ FAILURE: Basic Socket.IO functionality broken")
        
        # Cleanup
        await client.disconnect()
        await runner.cleanup()
        
        return len(self.received_events) >= 2


async def main():
    """Run the minimal test."""
    test = MinimalSocketIOTest()
    success = await test.run_test()
    return 0 if success else 1


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(result)