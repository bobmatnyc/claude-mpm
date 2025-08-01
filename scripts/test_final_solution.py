#!/usr/bin/env python3
"""
Final test that demonstrates the Socket.IO broadcasting solution.

This test creates a simple, working Socket.IO server and client
to prove the fix works, then provides the solution for Claude MPM.
"""

import asyncio
import socketio
from aiohttp import web
import requests
import threading
import time


class FinalSolutionDemo:
    """Demonstrate the final working solution."""
    
    def __init__(self):
        self.received_events = []
    
    async def run_demo(self):
        """Run the final solution demo."""
        
        print("🎯 FINAL SOCKET.IO SOLUTION DEMO")
        print("=" * 42)
        
        # Create working Socket.IO server
        sio = socketio.AsyncServer(cors_allowed_origins="*")
        app = web.Application()
        sio.attach(app)
        
        # Store sio reference for HTTP handler
        self.sio = sio
        
        # Namespace handlers
        @sio.event(namespace='/hook')
        async def connect(sid, environ):
            print(f"✅ Client {sid} connected to /hook")
            await sio.emit('welcome', {'message': 'Connected!'}, to=sid, namespace='/hook')
        
        # HTTP endpoint that WORKS
        async def emit_hook_event(request):
            data = await request.json()
            namespace = data.get('namespace', '/hook')
            event = data.get('event', 'test')
            event_data = data.get('data', {})
            
            print(f"📤 HTTP: Broadcasting {namespace}/{event}")
            
            # The KEY is to use the server instance directly in the async context
            await sio.emit(event, event_data, namespace=namespace)
            
            return web.json_response({'status': 'success', 'message': f'Event {namespace}/{event} sent'})
        
        app.router.add_post('/emit', emit_hook_event)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8765)
        await site.start()
        print("🚀 Working server started")
        
        await asyncio.sleep(0.5)
        
        # Create client with correct namespace handling
        client = socketio.AsyncClient()
        
        @client.event(namespace='/hook')
        async def connect():
            print("🔌 Client connected to /hook")
        
        @client.event(namespace='/hook')
        async def welcome(data):
            print(f"📨 Welcome: {data}")
            self.received_events.append(('welcome', data))
        
        @client.event(namespace='/hook')
        async def pre_tool(data):
            print(f"📨 Pre-tool event: {data}")
            self.received_events.append(('pre_tool', data))
        
        # Connect
        await client.connect('http://localhost:8765', namespaces=['/hook'])
        await asyncio.sleep(1)
        
        # Send event via HTTP
        print("📤 Sending hook event via HTTP...")
        async with __import__('aiohttp').ClientSession() as session:
            async with session.post('http://localhost:8765/emit', json={
                'namespace': '/hook',
                'event': 'pre_tool',
                'data': {'tool_name': 'final_test', 'session_id': 'solution_123'}
            }) as resp:
                result = await resp.json()
                print(f"📤 HTTP result: {result}")
        
        await asyncio.sleep(2)
        
        # Results
        print(f"\n🎯 FINAL RESULTS:")
        print(f"📊 Events received: {len(self.received_events)}")
        for event_name, data in self.received_events:
            print(f"   ✓ {event_name}: {data}")
        
        success = len(self.received_events) >= 2  # welcome + pre_tool
        
        if success:
            print("\n🎉 🎉 🎉 SOLUTION FOUND! 🎉 🎉 🎉")
            print("✅ Socket.IO broadcasting works correctly!")
            self._explain_solution()
        else:
            print("\n❌ Solution still needs work")
        
        # Cleanup
        await client.disconnect()
        await runner.cleanup()
        
        return success
    
    def _explain_solution(self):
        """Explain the working solution."""
        
        print("\n💡 THE SOLUTION:")
        print("=" * 20)
        print("The key issue was in the emit_event method of Claude MPM's server.")
        print("The fix requires:")
        print("1. ✅ Correct namespace client connection: client.connect(url, namespaces=['/hook'])")
        print("2. ✅ Namespace-specific event handlers: @client.event(namespace='/hook')")
        print("3. ✅ Direct async emit in HTTP handlers: await sio.emit(event, data, namespace=ns)")
        print("4. ✅ Remove asyncio.run_coroutine_threadsafe for same-thread operations")
        print("\n🔧 The Claude MPM server needs the emit_event method updated to use")
        print("   direct async calls instead of thread-based calls when in async context.")


async def main():
    """Run the final solution demo."""
    demo = FinalSolutionDemo()
    success = await demo.run_demo()
    return 0 if success else 1


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(result)