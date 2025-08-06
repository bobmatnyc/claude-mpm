#!/usr/bin/env python3
"""
Test Socket.IO with namespaces to identify the namespace issue.
"""

import asyncio
import socketio
from aiohttp import web
import threading
import time


class NamespaceSocketIOTest:
    """Socket.IO namespace test."""
    
    def __init__(self):
        self.received_events = []
        
    async def run_test(self):
        """Run namespace test."""
        
        print("🧪 NAMESPACE SOCKET.IO TEST")
        print("=" * 35)
        
        # Create Socket.IO server
        sio = socketio.AsyncServer(cors_allowed_origins="*")
        app = web.Application()
        sio.attach(app)
        
        # Namespace event handlers
        @sio.event(namespace='/test')
        async def connect(sid, environ):
            print(f"✅ Client {sid} connected to /test namespace")
            # Send immediate test event
            await sio.emit('welcome', {'message': 'Hello from /test namespace!'}, to=sid, namespace='/test')
            
        @sio.event(namespace='/test')
        async def disconnect(sid):
            print(f"❌ Client {sid} disconnected from /test namespace")
        
        # HTTP endpoint to trigger namespace events
        async def trigger_event(request):
            print("📤 Triggering namespace event...")
            await sio.emit('test_broadcast', {'message': 'Namespace broadcast test'}, namespace='/test')
            return web.json_response({'status': 'namespace event sent'})
        
        app.router.add_post('/trigger', trigger_event)
        
        # Start server in background
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8765)
        await site.start()
        print("🚀 Namespace server started on port 8765")
        
        # Give server time to start
        await asyncio.sleep(0.5)
        
        # Create client for /test namespace
        client = socketio.AsyncClient()
        
        @client.event
        async def connect():
            print("🔌 Client connected to /test namespace")
            
        @client.event
        async def welcome(data):
            print(f"📨 Received welcome: {data}")
            self.received_events.append(('welcome', data))
            
        @client.event
        async def test_broadcast(data):
            print(f"📨 Received broadcast: {data}")
            self.received_events.append(('test_broadcast', data))
        
        # Connect client to /test namespace
        await client.connect('http://localhost:8765/test')
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
            print("✅ SUCCESS: Namespace Socket.IO functionality works!")
        else:
            print("❌ FAILURE: Namespace Socket.IO functionality broken")
            print("🔧 This confirms the namespace broadcasting issue")
        
        # Cleanup
        await client.disconnect()
        await runner.cleanup()
        
        return len(self.received_events) >= 2


async def main():
    """Run the namespace test."""
    test = NamespaceSocketIOTest()
    success = await test.run_test()
    return 0 if success else 1


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(result)