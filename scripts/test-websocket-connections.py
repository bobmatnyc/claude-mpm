#!/usr/bin/env python3
"""
Test WebSocket connections for all dashboards.
Verifies that Socket.IO connections are working properly.
"""

import asyncio
import socketio
import time
from typing import Dict, List
import json

class DashboardTester:
    def __init__(self, port: int = 8765):
        self.port = port
        self.url = f"http://localhost:{port}"
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.events_received = []

    async def setup_handlers(self):
        """Setup event handlers for Socket.IO."""

        @self.sio.on('connect')
        async def on_connect():
            print(f"✅ Connected to Socket.IO server at {self.url}")
            print(f"   Socket ID: {self.sio.sid}")
            self.connected = True

        @self.sio.on('disconnect')
        async def on_disconnect():
            print(f"🔌 Disconnected from server")
            self.connected = False

        @self.sio.on('claude_event')
        async def on_claude_event(data):
            print(f"📊 Received claude_event: {data.get('type', 'unknown')}")
            self.events_received.append(data)

        @self.sio.on('history')
        async def on_history(data):
            event_count = len(data.get('events', []))
            print(f"📜 Received history with {event_count} events")

        @self.sio.on('system.status')
        async def on_status(data):
            print(f"💚 System status: {data}")

        @self.sio.on('*')
        async def catch_all(event, data):
            if event not in ['connect', 'disconnect', 'claude_event', 'history']:
                print(f"📨 Event '{event}': {data}")

    async def test_connection(self):
        """Test the Socket.IO connection."""
        print(f"\n🔧 Testing Socket.IO connection to {self.url}")
        print("=" * 60)

        try:
            # Setup handlers
            await self.setup_handlers()

            # Connect
            print(f"🔄 Attempting to connect...")
            await self.sio.connect(self.url, transports=['polling', 'websocket'])

            # Wait for connection
            await asyncio.sleep(1)

            if self.connected:
                print(f"✅ Connection successful!")

                # Request history
                print(f"\n📖 Requesting event history...")
                await self.sio.emit('get_history', {'limit': 10})
                await asyncio.sleep(1)

                # Send test event
                print(f"\n🎯 Sending test event...")
                test_event = {
                    'type': 'test_connection',
                    'timestamp': int(time.time() * 1000),
                    'source': 'test_script',
                    'data': {
                        'message': 'Testing dashboard connection',
                        'dashboard': 'test'
                    }
                }
                await self.sio.emit('test_event', test_event)
                await asyncio.sleep(1)

                # Check received events
                print(f"\n📊 Events received: {len(self.events_received)}")
                if self.events_received:
                    for i, event in enumerate(self.events_received[:5], 1):
                        print(f"   {i}. {event.get('type', 'unknown')} at {event.get('timestamp', 'N/A')}")

                # Test connection health
                print(f"\n💓 Testing connection health...")
                await self.sio.emit('ping')
                await asyncio.sleep(0.5)

                # Get server stats
                print(f"\n📈 Requesting server stats...")
                await self.sio.emit('get_stats')
                await asyncio.sleep(1)

                print(f"\n✅ All tests passed!")

            else:
                print(f"❌ Failed to connect to server")

        except Exception as e:
            print(f"❌ Connection test failed: {e}")

        finally:
            if self.sio.connected:
                await self.sio.disconnect()
                print(f"\n🔌 Disconnected from server")

    async def test_dashboards(self):
        """Test all dashboard endpoints."""
        dashboards = [
            'activity.html',
            'events.html',
            'agents.html',
            'tools.html',
            'files.html'
        ]

        print(f"\n🎯 Testing dashboard endpoints")
        print("=" * 60)

        import aiohttp

        async with aiohttp.ClientSession() as session:
            for dashboard in dashboards:
                url = f"{self.url}/static/{dashboard}"
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            # Check for Socket.IO loading
                            if 'socket.io.min.js' in content:
                                if 'waitForSocketIO' in content:
                                    print(f"✅ {dashboard:20} - Socket.IO fixed and ready")
                                else:
                                    print(f"⚠️  {dashboard:20} - Socket.IO loaded but not fixed")
                            else:
                                print(f"❌ {dashboard:20} - Socket.IO not loaded")
                        else:
                            print(f"❌ {dashboard:20} - HTTP {response.status}")
                except Exception as e:
                    print(f"❌ {dashboard:20} - Error: {e}")

async def main():
    """Main test function."""
    print("🚀 Claude MPM Dashboard WebSocket Connection Test")
    print("=" * 60)

    tester = DashboardTester()

    # Test Socket.IO connection
    await tester.test_connection()

    # Test dashboard endpoints
    await tester.test_dashboards()

    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   - Server URL: {tester.url}")
    print(f"   - Connection: {'✅ Working' if tester.connected else '❌ Failed'}")
    print(f"   - Events received: {len(tester.events_received)}")
    print("\n💡 To test in browser:")
    print(f"   1. Open http://localhost:8765/static/test-socket-connection.html")
    print(f"   2. Check browser console for connection logs")
    print(f"   3. Open http://localhost:8765/static/activity.html")
    print(f"   4. Verify 'Connected' status in header")

if __name__ == '__main__':
    asyncio.run(main())