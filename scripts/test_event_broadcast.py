#!/usr/bin/env python3
"""
Test to verify event broadcasting between hook handler and dashboard client.
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


async def test_event_broadcast():
    """Test event broadcasting specifically."""
    print("🔍 Testing event broadcasting...")
    
    # Start server
    print("\n1. Starting server...")
    server = get_socketio_server()
    server.start()
    await asyncio.sleep(3)
    
    # Create dashboard client
    print("\n2. Creating dashboard client...")
    client = socketio.AsyncClient(logger=False, engineio_logger=False)
    
    # Track all events received
    all_events = []
    
    # Set up handlers for ALL possible events in /hook namespace
    @client.event(namespace='/hook')
    async def user_prompt(data):
        print(f"📥 Dashboard: user_prompt -> {data}")
        all_events.append(('user_prompt', data))
    
    @client.event(namespace='/hook')
    async def pre_tool(data):
        print(f"📥 Dashboard: pre_tool -> {data}")
        all_events.append(('pre_tool', data))
    
    @client.event(namespace='/hook')
    async def post_tool(data):
        print(f"📥 Dashboard: post_tool -> {data}")
        all_events.append(('post_tool', data))
    
    # Catch-all handler to see ALL events
    @client.event(namespace='/hook')
    async def catch_all(*args, **kwargs):
        print(f"📥 Dashboard: catch_all -> args={args}, kwargs={kwargs}")
        all_events.append(('catch_all', args, kwargs))
    
    # Connect to server
    await client.connect(
        'http://localhost:8765',
        auth={'token': 'dev-token'},
        namespaces=['/hook'],
        wait=True
    )
    
    print("✅ Dashboard client connected")
    await asyncio.sleep(1)
    
    # Step 1: Test direct server broadcast to verify client receives events
    print("\n3. Testing direct server broadcast...")
    
    # Use async emit with await
    await server.sio.emit('user_prompt', {'test': 'direct server emit'}, namespace='/hook')
    await asyncio.sleep(1)
    
    print(f"   Events after direct emit: {len(all_events)}")
    
    # Step 2: Test hook handler events
    print("\n4. Testing hook handler events...")
    
    # Set environment
    os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
    os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    
    # Test multiple event types
    test_events = [
        {
            'hook_event_name': 'UserPromptSubmit',
            'prompt': 'Test user prompt from test',
            'session_id': 'broadcast-test',
            'timestamp': time.time()
        },
        {
            'hook_event_name': 'PreToolUse',
            'tool_name': 'TestTool',
            'session_id': 'broadcast-test',
            'timestamp': time.time()
        },
        {
            'hook_event_name': 'PostToolUse',
            'tool_name': 'TestTool',
            'exit_code': 0,
            'session_id': 'broadcast-test',
            'timestamp': time.time()
        }
    ]
    
    hook_script = project_root / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
    
    for i, test_event in enumerate(test_events):
        print(f"\n   4.{i+1}. Testing {test_event['hook_event_name']}...")
        
        # Run hook handler
        process = subprocess.Popen(
            [sys.executable, str(hook_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ}
        )
        
        stdout, stderr = process.communicate(input=json.dumps(test_event), timeout=10)
        
        print(f"      stdout: {stdout.strip()}")
        print(f"      stderr: {stderr.strip() if stderr.strip() else '(no stderr)'}")
        
        # Wait for events to propagate
        await asyncio.sleep(1)
        
        print(f"      Events after hook {i+1}: {len(all_events)}")
    
    # Final check
    print(f"\n📊 Final Results:")
    print(f"   Total events received: {len(all_events)}")
    for i, event in enumerate(all_events):
        print(f"   {i+1}. {event}")
    
    # Cleanup
    await client.disconnect()
    server.stop()
    
    # Analysis
    if len(all_events) >= 3:  # Direct emit + hook events
        print("\n✅ SUCCESS: Events are being broadcast correctly!")
    elif len(all_events) >= 1:
        print("\n⚠️  PARTIAL: Some events received, but not from hooks")
    else:
        print("\n❌ FAILURE: No events received at all")
        

if __name__ == "__main__":
    asyncio.run(test_event_broadcast())