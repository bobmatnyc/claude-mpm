#!/usr/bin/env python3
"""
Direct test of hook handler -> Socket.IO server flow without Claude.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_direct_hook_to_socketio():
    """Test direct hook handler to Socket.IO server communication."""
    print("🧪 Testing direct hook handler -> Socket.IO server communication")
    
    # Start Socket.IO client to monitor events
    events_received = []
    
    try:
        import socketio
        
        async def monitor_events():
            client = socketio.AsyncClient()
            
            @client.event
            async def connect():
                print("✅ Monitor client connected to Socket.IO server")
            
            @client.event
            async def claude_event(data):
                print(f"📨 Received Socket.IO event: {json.dumps(data, indent=2)}")
                events_received.append(data)
            
            @client.event
            async def disconnect():
                print("🔌 Monitor client disconnected")
            
            try:
                await client.connect('http://localhost:8765')
                print("🔗 Monitor connected, waiting for events...")
                
                # Wait 10 seconds for events
                await asyncio.sleep(10)
                
                await client.disconnect()
                
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                
            return events_received
        
        # Start monitoring in background
        def run_monitor():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(monitor_events())
        
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        
        # Give monitor time to connect
        time.sleep(2)
        
    except ImportError:
        print("⚠️ Socket.IO not available - will test without monitoring")
        monitor_thread = None
    
    # Test hook handler with various events
    test_events = [
        {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Test prompt for Socket.IO integration",
            "session_id": "direct_test_001",
            "cwd": str(Path.cwd()),
            "timestamp": datetime.now().isoformat()
        },
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo 'test command'"},
            "session_id": "direct_test_002",
            "cwd": str(Path.cwd()),
            "timestamp": datetime.now().isoformat()
        },
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "exit_code": 0,
            "output": "test output",
            "session_id": "direct_test_003",
            "cwd": str(Path.cwd()),
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    hook_handler_path = project_root / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
    
    # Set up environment
    env = os.environ.copy()
    env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    env['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
    env['PYTHONPATH'] = str(project_root / "src")
    
    successful_hooks = 0
    
    for i, event in enumerate(test_events, 1):
        print(f"\n🧪 Testing hook event {i}/{len(test_events)}: {event['hook_event_name']}")
        
        hook_json = json.dumps(event)
        
        try:
            result = subprocess.run(
                [sys.executable, str(hook_handler_path)],
                input=hook_json,
                text=True,
                capture_output=True,
                env=env,
                timeout=5
            )
            
            if result.returncode == 0:
                print(f"✅ Hook {i} executed successfully")
                successful_hooks += 1
                
                # Check for Socket.IO emission in stderr
                if 'Emitted pooled Socket.IO event' in result.stderr:
                    print(f"✅ Socket.IO event emission detected in logs")
                elif result.stderr:
                    print(f"📋 Hook stderr: {result.stderr[:200]}...")
            else:
                print(f"❌ Hook {i} failed with code {result.returncode}")
                if result.stderr:
                    print(f"❌ Error: {result.stderr}")
            
            # Small delay between hooks
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Hook {i} error: {e}")
    
    # Wait for any remaining events to be processed
    time.sleep(3)
    
    if monitor_thread:
        monitor_thread.join(timeout=2)
    
    print(f"\n📊 Results:")
    print(f"  Hooks executed successfully: {successful_hooks}/{len(test_events)}")
    print(f"  Socket.IO events received: {len(events_received)}")
    
    if events_received:
        print(f"📨 Event types received:")
        for event in events_received:
            event_type = event.get('data', {}).get('event_type', 'unknown')
            print(f"  - {event_type}")
    
    return successful_hooks == len(test_events) and len(events_received) > 0

def main():
    """Run direct hook to Socket.IO test."""
    print("🎯 Direct Hook Handler -> Socket.IO Server Test")
    print("=" * 60)
    
    success = test_direct_hook_to_socketio()
    
    print("=" * 60)
    
    if success:
        print("✅ SUCCESS: Hook handler -> Socket.IO server communication works!")
        print("\n🎉 Socket.IO hook integration is functioning correctly.")
        print("\nThe issue with Claude --monitor is likely in Claude's hook invocation,")
        print("not in our Socket.IO integration.")
    else:
        print("❌ Hook handler -> Socket.IO communication has issues")
        print("\nCheck the logs above for specific error details.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)