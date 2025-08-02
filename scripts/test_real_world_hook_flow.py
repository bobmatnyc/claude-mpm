#!/usr/bin/env python3
"""
Real-world test of the complete hook → Socket.IO → dashboard flow.

This simulates the actual production scenario:
1. Start Socket.IO server (like ClaudeRunner does)
2. Connect dashboard client 
3. Run actual hook events through the hook handler
4. Verify dashboard receives them
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


async def main():
    """Test the real-world hook flow."""
    print("🚀 Testing real-world hook → Socket.IO → dashboard flow")
    print("=" * 60)
    
    # Step 1: Start server (like ClaudeRunner does)
    print("\n📡 Starting Socket.IO server...")
    server = get_socketio_server()
    server.start()
    
    # Wait for server to start
    await asyncio.sleep(2)
    print("✅ Server started")
    
    # Step 2: Set environment (like ClaudeRunner does)
    os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
    print("✅ Environment configured")
    
    # Step 3: Connect dashboard client
    print("\n🖥️  Connecting dashboard client...")
    client = socketio.AsyncClient()
    events_received = []
    
    @client.event(namespace='/hook')
    async def user_prompt(data):
        print(f"📥 Dashboard received: user_prompt -> {data}")
        events_received.append(('user_prompt', data))
    
    @client.event(namespace='/hook')
    async def pre_tool(data):
        print(f"📥 Dashboard received: pre_tool -> {data}")
        events_received.append(('pre_tool', data))
    
    @client.event(namespace='/hook')
    async def post_tool(data):
        print(f"📥 Dashboard received: post_tool -> {data}")
        events_received.append(('post_tool', data))
    
    await client.connect('http://localhost:8765', 
                        auth={'token': 'dev-token'}, 
                        namespaces=['/hook'])
    print("✅ Dashboard connected")
    
    # Step 4: Simulate real hook events
    print("\n🎯 Simulating real hook events...")
    
    real_events = [
        {
            'hook_event_name': 'UserPromptSubmit',
            'prompt': 'Show me the current directory contents',
            'session_id': 'production-session-456',
            'timestamp': time.time()
        },
        {
            'hook_event_name': 'PreToolUse', 
            'tool_name': 'Bash',
            'session_id': 'production-session-456',
            'timestamp': time.time()
        },
        {
            'hook_event_name': 'PostToolUse',
            'tool_name': 'Bash',
            'exit_code': 0,
            'session_id': 'production-session-456', 
            'timestamp': time.time()
        }
    ]
    
    hook_script = project_root / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
    
    for i, event in enumerate(real_events, 1):
        print(f"\n   {i}. Sending {event['hook_event_name']}...")
        
        # Run hook handler exactly like Claude would
        process = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            env=os.environ
        )
        
        if process.returncode == 0:
            print(f"      ✅ Hook handler completed successfully")
        else:
            print(f"      ❌ Hook handler failed: {process.stderr}")
        
        # Wait for event to propagate
        await asyncio.sleep(0.5)
    
    # Step 5: Final verification
    print(f"\n📊 Results:")
    print(f"   Events sent: {len(real_events)}")
    print(f"   Events received: {len(events_received)}")
    
    for event_type, data in events_received:
        print(f"   📝 {event_type}: session={data.get('session_id', 'N/A')}")
    
    # Cleanup
    await client.disconnect()
    server.stop()
    
    # Final status
    if len(events_received) == len(real_events):
        print(f"\n🎉 SUCCESS! All {len(real_events)} events received by dashboard!")
        print("   The complete hook → Socket.IO → dashboard flow is working! 🚀")
    else:
        print(f"\n⚠️  Partial success: {len(events_received)}/{len(real_events)} events received")
    
    print(f"\n💡 You can now use the dashboard with Socket.IO events!")
    print(f"   - Start claude-mpm with --monitor flag")
    print(f"   - Open the dashboard in your browser")
    print(f"   - Watch real-time events as Claude runs!")


if __name__ == "__main__":
    asyncio.run(main())