#!/usr/bin/env python3
"""
Test browser connection simulation for Claude MPM dashboard.
This script tests Socket.IO connection similar to how a browser would connect.
"""

import asyncio
import sys

import socketio


async def test_connection():
    """Test Socket.IO connection to the dashboard server"""
    sio = socketio.AsyncClient()
    
    @sio.event
    async def connect():
        print(f"✅ Connected to Socket.IO server! ID: {sio.sid}")
        print(f"🔗 Transport: {sio.transport()}")
        
    @sio.event
    async def disconnect():
        print("❌ Disconnected from server")
        
    @sio.event
    async def connect_error(data):
        print(f"🚫 Connection error: {data}")
        
    @sio.event
    async def event(data):
        print(f"📨 Received event: {data}")
        
    try:
        print("🚀 Attempting to connect to http://localhost:8765...")
        print("   Using transports: ['websocket', 'polling']")
        print("   Connection timeout: 10 seconds")
        
        # Connect with similar settings to the test page
        await sio.connect(
            'http://localhost:8765',
            transports=['websocket', 'polling'],
            wait_timeout=10
        )
        
        print("✅ Connection established successfully!")
        print("🔄 Waiting 5 seconds for any incoming events...")
        await asyncio.sleep(5)
        
        print("🔌 Disconnecting...")
        await sio.disconnect()
        print("✅ Test completed successfully!")
        return True
        
    except socketio.exceptions.ConnectionError as e:
        print(f"🚫 Socket.IO connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_http_endpoints():
    """Test basic HTTP endpoints are accessible"""
    import aiohttp
    
    endpoints = [
        'http://localhost:8765/',
        'http://localhost:8765/static/dist/dashboard.js',
        'http://localhost:8765/static/js/dashboard.js'
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        print(f"✅ {endpoint} - OK ({response.status})")
                    else:
                        print(f"⚠️ {endpoint} - Status {response.status}")
            except Exception as e:
                print(f"❌ {endpoint} - Error: {e}")


async def main():
    """Main test function"""
    print("🧪 Claude MPM Dashboard Connection Test")
    print("=" * 50)
    
    print("\n📡 Testing HTTP endpoints...")
    await test_http_endpoints()
    
    print("\n🔌 Testing Socket.IO connection...")
    success = await test_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Dashboard connection is working.")
        sys.exit(0)
    else:
        print("💥 Connection test failed! Check server status.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())