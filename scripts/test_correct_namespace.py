#!/usr/bin/env python3
"""
Test the correct way to handle namespaces in python-socketio.
"""

import asyncio
import socketio
from aiohttp import web


class CorrectNamespaceTest:
    """Correct namespace test based on python-socketio docs."""
    
    def __init__(self):
        self.received_events = []
        
    async def run_test(self):
        """Run correct namespace test."""
        
        print("🧪 CORRECT NAMESPACE TEST")
        print("=" * 32)
        
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
                         {'message': 'Correct namespace broadcast'}, 
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
        
        # Create client - proper namespace connection
        client = socketio.AsyncClient()
        
        @client.event
        async def connect():
            print("🔌 Client connected to namespace")
            
        @client.event
        async def welcome(data):
            print(f"📨 Received welcome: {data}")
            self.received_events.append(('welcome', data))
            
        @client.event
        async def test_broadcast(data):
            print(f"📨 Received broadcast: {data}")
            self.received_events.append(('test_broadcast', data))
        
        # Connect to server first, then namespace
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
            print("✅ SUCCESS: Correct namespace handling works!")
        else:
            print("❌ FAILURE: Still not working correctly")
        
        # Cleanup
        await client.disconnect()
        await runner.cleanup()
        
        return success


async def main():
    test = CorrectNamespaceTest()
    success = await test.run_test()
    return 0 if success else 1


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(result)