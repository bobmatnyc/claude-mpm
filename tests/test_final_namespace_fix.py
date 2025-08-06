#!/usr/bin/env python3
"""
Final test with proper namespace event handler registration.
"""

import asyncio
import socketio
from aiohttp import web


class FinalNamespaceTest:
    """Final namespace test with proper event registration."""
    
    def __init__(self):
        self.received_events = []
        
    async def run_test(self):
        """Run final namespace test."""
        
        print("🧪 FINAL NAMESPACE FIX TEST")
        print("=" * 35)
        
        # Create Socket.IO server
        sio = socketio.AsyncServer(cors_allowed_origins="*")
        app = web.Application()
        sio.attach(app)
        
        # Namespace-specific handlers
        @sio.event(namespace='/test')
        async def connect(sid, environ):
            print(f"✅ Client {sid} connected to /test namespace")
            await sio.emit('welcome', {'message': 'Welcome to /test!'}, to=sid, namespace='/test')
            
        @sio.event(namespace='/test')
        async def disconnect(sid):
            print(f"❌ Client {sid} disconnected from /test")
        
        # HTTP endpoint
        async def trigger_event(request):
            print("📤 Broadcasting to /test namespace...")
            await sio.emit('test_broadcast', 
                         {'message': 'Final namespace broadcast test'}, 
                         namespace='/test')
            return web.json_response({'status': 'broadcast sent'})
        
        app.router.add_post('/trigger', trigger_event)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8765)
        await site.start()
        print("🚀 Server started on port 8765")
        
        await asyncio.sleep(0.5)
        
        # Create client with namespace-specific event handlers
        client = socketio.AsyncClient()
        
        # Register event handlers for the specific namespace
        @client.event(namespace='/test')
        async def connect():
            print("🔌 Client connected to /test namespace")
            
        @client.event(namespace='/test')
        async def welcome(data):
            print(f"📨 Received welcome: {data}")
            self.received_events.append(('welcome', data))
            
        @client.event(namespace='/test')
        async def test_broadcast(data):
            print(f"📨 Received broadcast: {data}")
            self.received_events.append(('test_broadcast', data))
        
        # Connect to server with namespace
        await client.connect('http://localhost:8765', namespaces=['/test'])
        await asyncio.sleep(1)
        
        # Trigger event
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:8765/trigger') as resp:
                result = await resp.json()
                print(f"📤 Result: {result}")
        
        await asyncio.sleep(2)
        
        # Report results
        print(f"\n📊 Events received: {len(self.received_events)}")
        for event_name, event_data in self.received_events:
            print(f"   - {event_name}: {event_data}")
        
        success = len(self.received_events) >= 2  # welcome + test_broadcast
        if success:
            print("✅ SUCCESS: Final namespace fix works!")
            print("🎉 Socket.IO broadcasting issue is now SOLVED!")
        else:
            print("❌ FAILURE: Deep namespace issue in python-socketio")
        
        # Cleanup
        await client.disconnect()
        await runner.cleanup()
        
        return success


async def main():
    test = FinalNamespaceTest()
    success = await test.run_test()
    return 0 if success else 1


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(result)