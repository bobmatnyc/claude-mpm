#!/usr/bin/env python3
"""
Debug script to test hook emission specifically.

This focuses on the specific issue: hooks run but don't emit events to Socket.IO.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("❌ Socket.IO not available")
    sys.exit(1)

from claude_mpm.services.websocket_server import get_socketio_server


async def main():
    """Debug hook event emission."""
    print("🔍 Debugging hook event emission...")
    
    # Start server
    print("\n1. Starting Socket.IO server...")
    server = get_socketio_server()
    server.start()
    time.sleep(2)  # Let server start
    
    # Set environment
    os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
    os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    
    # Create client to receive events
    print("\n2. Creating dashboard client...")
    client = socketio.AsyncClient(logger=True, engineio_logger=True)
    received_events = []
    
    @client.event
    async def connect():
        print("✅ Client connected")
    
    @client.event(namespace='/hook')
    async def user_prompt(data):
        print(f"📥 Received user_prompt: {data}")
        received_events.append(('user_prompt', data))
    
    @client.event(namespace='/hook')
    async def pre_tool(data):
        print(f"📥 Received pre_tool: {data}")
        received_events.append(('pre_tool', data))
    
    @client.event(namespace='/hook')
    async def post_tool(data):
        print(f"📥 Received post_tool: {data}")
        received_events.append(('post_tool', data))
    
    # Connect client
    await client.connect('http://localhost:8765', namespaces=['/hook'])
    
    # Test direct emission from server to verify connection
    print("\n3. Testing direct server emission...")
    server.broadcast_event('test_event', {'message': 'direct test'})
    await asyncio.sleep(1)
    
    # Now test hook handler
    print("\n4. Testing hook handler emission...")
    
    test_event = {
        'hook_event_name': 'UserPromptSubmit',
        'prompt': 'Test prompt for debugging',
        'session_id': 'debug-session',
        'timestamp': time.time()
    }
    
    # Run hook handler
    hook_script = project_root / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
    
    print(f"🔧 Running hook handler: {hook_script}")
    
    process = subprocess.Popen(
        [sys.executable, str(hook_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ}
    )
    
    stdout, stderr = process.communicate(input=json.dumps(test_event), timeout=10)
    
    print(f"📤 Hook handler stdout: {stdout}")
    print(f"📤 Hook handler stderr: {stderr}")
    print(f"📤 Hook handler return code: {process.returncode}")
    
    # Wait for events
    print("\n5. Waiting for events...")
    await asyncio.sleep(5)
    
    print(f"\n📊 Received {len(received_events)} events:")
    for event_type, data in received_events:
        print(f"  📝 {event_type}: {data}")
    
    # Cleanup
    await client.disconnect()
    server.stop()
    
    if received_events:
        print("\n✅ SUCCESS: Events were received!")
    else:
        print("\n❌ PROBLEM: No events received")
        
        # Additional debugging
        print("\n🔍 Debugging info:")
        print(f"  - Server port: {server.port}")
        print(f"  - Server running: {server.running}")
        print(f"  - Environment CLAUDE_MPM_SOCKETIO_PORT: {os.environ.get('CLAUDE_MPM_SOCKETIO_PORT')}")
        
        # Try to import hook handler and check its connection
        print("\n🔍 Testing hook handler connection directly...")
        try:
            sys.path.insert(0, str(project_root / "src"))
            from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
            
            handler = ClaudeHookHandler()
            print(f"  - Handler server_port: {handler.server_port}")
            print(f"  - Handler server_url: {handler.server_url}")
            print(f"  - Handler socketio_client: {handler.socketio_client}")
            if handler.socketio_client:
                print(f"  - Handler connected: {handler.socketio_client.connected}")
            
        except Exception as e:
            print(f"  - Handler test error: {e}")


if __name__ == "__main__":
    asyncio.run(main())