#!/usr/bin/env python3
"""Test Socket.IO connection and event reception."""

import socketio
import time
import asyncio

# Test client connecting to all namespaces
namespaces = ['/system', '/session', '/claude', '/agent', '/hook', '/todo', '/memory', '/log']

async def test_connection():
    """Test connection to all namespaces."""
    print("🔄 Starting Socket.IO connection test")
    
    # First, test basic connection
    sio = socketio.AsyncClient()
    
    @sio.event
    async def connect():
        print(f"✅ Connected to /system namespace")
        
    @sio.event
    async def disconnect():
        print(f"❌ Disconnected from /system namespace")
        
    @sio.event
    async def connect_error(data):
        print(f"🔥 Connection error for /system: {data}")
    
    @sio.on('status')
    async def on_status(data):
        print(f"📨 Received status event: {data}")
    
    print("🔌 Attempting to connect to /system namespace...")
    try:
        # Set a connection timeout
        await asyncio.wait_for(
            sio.connect('http://localhost:8765/system'),
            timeout=5.0
        )
        print("✅ Connection successful!")
        
        # Send a status request
        print("📤 Requesting status...")
        await sio.emit('get_status')
        
        # Wait for response
        await asyncio.sleep(2)
        
    except asyncio.TimeoutError:
        print("⏰ Connection timed out")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        if sio.connected:
            await sio.disconnect()
            print("📤 Disconnected")

if __name__ == "__main__":
    asyncio.run(test_connection())