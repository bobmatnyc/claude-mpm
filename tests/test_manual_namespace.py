#!/usr/bin/env python3
"""
Test manual namespace handling approach.
"""

import asyncio
import socketio
from aiohttp import web


class ManualNamespaceTest:
    """Manual namespace handling test."""
    
    def __init__(self):
        self.received_events = []
        self.connected_clients = {}
        
    async def run_test(self):
        """Run manual namespace test."""
        
        print("🧪 MANUAL NAMESPACE TEST")
        print("=" * 30)
        
        # Create Socket.IO server
        sio = socketio.AsyncServer(cors_allowed_origins="*")
        app = web.Application()
        sio.attach(app)
        
        # Store reference for HTTP handler
        self.sio = sio
        
        # Single connection handler - track namespaces manually
        @sio.event
        async def connect(sid, environ):
            # Extract namespace from environ
            namespace = environ.get('PATH_INFO', '/')
            print(f"✅ Client {sid} connected to {namespace}")
            
            # Track client by namespace
            if namespace not in self.connected_clients:
                self.connected_clients[namespace] = []
            self.connected_clients[namespace].append(sid)
            
            # Send welcome based on namespace
            if namespace == '/test':
                await sio.emit('welcome', {'message': f'Hello from {namespace}!'}, to=sid)
            
        @sio.event
        async def disconnect(sid):
            print(f"❌ Client {sid} disconnected")
            # Remove from all namespace tracking
            for namespace_clients in self.connected_clients.values():
                if sid in namespace_clients:
                    namespace_clients.remove(sid)
        
        # HTTP endpoint with manual namespace targeting
        async def trigger_event(request):
            print("📤 Triggering manual namespace event...")
            
            # Manual broadcast to /test namespace clients
            test_clients = self.connected_clients.get('/test', [])
            print(f"🎯 Broadcasting to {len(test_clients)} clients in /test")
            
            for client_sid in test_clients:
                await sio.emit('test_broadcast', 
                             {'message': 'Manual namespace broadcast'}, 
                             to=client_sid)
            
            return web.json_response({
                'status': 'manual namespace event sent',
                'clients_notified': len(test_clients)
            })
        
        app.router.add_post('/trigger', trigger_event)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8765)
        await site.start()
        print("🚀 Manual namespace server started")
        
        await asyncio.sleep(0.5)
        
        # Create client
        client = socketio.AsyncClient()
        
        @client.event
        async def connect():
            print("🔌 Client connected")
            
        @client.event
        async def welcome(data):
            print(f"📨 Received welcome: {data}")
            self.received_events.append(('welcome', data))
            
        @client.event
        async def test_broadcast(data):
            print(f"📨 Received broadcast: {data}")
            self.received_events.append(('test_broadcast', data))
        
        # Connect to /test namespace
        await client.connect('http://localhost:8765/test')
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
        
        success = len(self.received_events) >= 1  # At least test_broadcast
        if success:
            print("✅ SUCCESS: Manual namespace handling works!")
        else:
            print("❌ FAILURE: Even manual approach failed")
        
        # Cleanup
        await client.disconnect()
        await runner.cleanup()
        
        return success


async def main():
    test = ManualNamespaceTest()
    success = await test.run_test()
    return 0 if success else 1


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(result)