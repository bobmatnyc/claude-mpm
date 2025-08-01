#!/usr/bin/env python3
"""
Test to specifically verify namespace connection issues.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import socketio
from claude_mpm.services.websocket_server import get_socketio_server


async def test_namespace_connection():
    """Test namespace connections specifically."""
    print("🔍 Testing namespace connections...")
    
    # Start server
    print("\n1. Starting server...")
    server = get_socketio_server()
    server.start()
    
    # Wait longer for server to fully start
    print("⏳ Waiting for server to fully start...")
    await asyncio.sleep(3)
    
    # Create client
    print("\n2. Creating client with detailed logging...")
    client = socketio.AsyncClient(
        logger=True, 
        engineio_logger=True,
        reconnection=True,
        reconnection_attempts=3,
        reconnection_delay=1
    )
    
    # Track events
    events_received = []
    connection_events = []
    
    # Connection handlers
    @client.event
    async def connect():
        print("✅ Main client connected")
        connection_events.append('main_connected')
    
    @client.event
    async def disconnect():
        print("❌ Main client disconnected")
        connection_events.append('main_disconnected')
    
    # Hook namespace handlers
    @client.event(namespace='/hook')
    async def connect():
        print("✅ /hook namespace connected")
        connection_events.append('hook_connected')
    
    @client.event(namespace='/hook')
    async def disconnect():
        print("❌ /hook namespace disconnected")
        connection_events.append('hook_disconnected')
    
    @client.event(namespace='/hook')
    async def user_prompt(data):
        print(f"📥 Received user_prompt in /hook: {data}")
        events_received.append(('hook', 'user_prompt', data))
    
    @client.event(namespace='/hook')
    async def pre_tool(data):
        print(f"📥 Received pre_tool in /hook: {data}")
        events_received.append(('hook', 'pre_tool', data))
    
    # System namespace handlers
    @client.event(namespace='/system')
    async def connect():
        print("✅ /system namespace connected")
        connection_events.append('system_connected')
    
    @client.event(namespace='/system')
    async def disconnect():
        print("❌ /system namespace disconnected")
        connection_events.append('system_disconnected')
    
    # Connect to server with auth
    print("\n3. Connecting to server with auth...")
    try:
        await client.connect(
            'http://localhost:8765',
            auth={'token': 'dev-token'},
            namespaces=['/hook', '/system'],
            wait=True,
            wait_timeout=10
        )
        print("✅ Client connected successfully")
    except Exception as e:
        print(f"❌ Client connection failed: {e}")
        return
    
    # Wait for namespace connections
    print("\n4. Waiting for namespace connections...")
    await asyncio.sleep(2)
    
    print(f"📊 Connection events so far: {connection_events}")
    
    # Test direct emission to namespaces
    print("\n5. Testing direct server emission...")
    
    # Emit to hook namespace
    server.sio.emit('test_hook_event', {'message': 'test hook'}, namespace='/hook')
    
    # Emit to system namespace  
    server.sio.emit('test_system_event', {'message': 'test system'}, namespace='/system')
    
    await asyncio.sleep(2)
    
    # Now test hook handler connection
    print("\n6. Testing hook handler...")
    
    # Set environment
    os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
    os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    
    # Create test event
    test_event = {
        'hook_event_name': 'UserPromptSubmit',
        'prompt': 'Test namespace connectivity',
        'session_id': 'test-session',
        'timestamp': time.time()
    }
    
    # Run hook handler
    hook_script = project_root / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
    
    print(f"🔧 Running hook handler...")
    process = subprocess.Popen(
        [sys.executable, str(hook_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ}
    )
    
    stdout, stderr = process.communicate(input=json.dumps(test_event), timeout=15)
    
    print(f"📤 Hook stdout: {stdout}")
    print(f"📤 Hook stderr: {stderr}")
    
    # Wait for events
    print("\n7. Final event check...")
    await asyncio.sleep(3)
    
    print(f"\n📊 Final Results:")
    print(f"  Connection events: {connection_events}")
    print(f"  Events received: {events_received}")
    
    # Cleanup
    await client.disconnect()
    server.stop()
    
    # Analysis
    success = len(events_received) > 0 and 'hook_connected' in connection_events
    if success:
        print("\n✅ SUCCESS: Namespace connection working!")
    else:
        print("\n❌ ISSUE: Namespace connection problems")
        if 'hook_connected' not in connection_events:
            print("  - /hook namespace never connected")
        if len(events_received) == 0:
            print("  - No events received")


if __name__ == "__main__":
    asyncio.run(test_namespace_connection())