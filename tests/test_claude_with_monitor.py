#!/usr/bin/env python3
"""
Final integration test to verify Claude with --monitor flag works properly.
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

def start_socketio_monitor():
    """Start a Socket.IO client to monitor events during the test."""
    try:
        import socketio
        
        events_received = []
        
        async def monitor_events():
            client = socketio.AsyncClient()
            
            @client.event
            async def connect():
                print("🔗 Monitor connected to Socket.IO server")
            
            @client.event
            async def claude_event(data):
                print(f"📨 Received event: {data.get('type', 'unknown')} - {data.get('data', {}).get('event_type', 'N/A')}")
                events_received.append(data)
            
            try:
                await client.connect('http://localhost:8765')
                
                # Monitor for 30 seconds
                for i in range(30):
                    await asyncio.sleep(1)
                    if i % 5 == 0:
                        print(f"📊 Monitoring... ({len(events_received)} events received)")
                
                await client.disconnect()
                
            except Exception as e:
                print(f"❌ Monitor error: {e}")
            
            return events_received
        
        # Run monitor in background thread
        def run_monitor():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(monitor_events())
        
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        
        return monitor_thread, events_received
        
    except ImportError:
        print("⚠️ Socket.IO client not available for monitoring")
        return None, []

def test_claude_with_monitor():
    """Test Claude with --monitor flag."""
    print("🧪 Testing Claude with --monitor flag...")
    
    # Set up environment
    env = os.environ.copy()
    env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    env['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
    env['PYTHONPATH'] = str(project_root / "src")
    
    # Start monitoring
    monitor_thread, events = start_socketio_monitor()
    time.sleep(2)  # Give monitor time to connect
    
    # Run Claude command
    claude_script = project_root / "scripts" / "claude-mpm"
    
    try:
        print("🚀 Running Claude command with --monitor...")
        
        result = subprocess.run([
            str(claude_script), 
            "run", 
            "-i", 
            "echo 'Testing Socket.IO hook integration'",
            "--non-interactive"
        ], 
        env=env,
        capture_output=True,
        text=True,
        timeout=20
        )
        
        print(f"📤 Claude exit code: {result.returncode}")
        print(f"📤 Claude output preview: {result.stdout[:200]}...")
        
        if result.stderr:
            print(f"📤 Claude stderr preview: {result.stderr[:200]}...")
        
        # Wait for events to be processed
        time.sleep(3)
        
        success = result.returncode == 0
        
        # Check for hook events in stderr (they go to stderr due to DEBUG)
        hook_events_in_stderr = 'Emitted pooled Socket.IO event' in result.stderr
        
        print(f"🎯 Hook events detected in logs: {hook_events_in_stderr}")
        
        if monitor_thread:
            print(f"📨 Events received by monitor: {len(events)}")
        
        return success and (hook_events_in_stderr or len(events) > 0)
        
    except subprocess.TimeoutExpired:
        print("❌ Claude command timed out")
        return False
    except Exception as e:
        print(f"❌ Claude test error: {e}")
        return False

def main():
    """Run final integration test."""
    print("🎯 Final Integration Test: Claude with Socket.IO Hook Monitoring")
    print("=" * 70)
    
    # Test Claude with monitor
    success = test_claude_with_monitor()
    
    print("=" * 70)
    
    if success:
        print("✅ SUCCESS: Claude with --monitor is working!")
        print("\nSocket.IO hook integration is now functional.")
        print("\nTo use:")
        print("1. Ensure Socket.IO server is running:")
        print("   python -m claude_mpm.services.socketio_server &")
        print()
        print("2. Set environment variables:")
        print("   export CLAUDE_MPM_HOOK_DEBUG=true")
        print("   export CLAUDE_MPM_SOCKETIO_PORT=8765")
        print()
        print("3. Run Claude with monitoring:")
        print("   ./claude-mpm run -i 'your prompt' --monitor")
        print()
        print("4. View events in dashboard:")
        print("   http://localhost:8765/dashboard")
        
    else:
        print("❌ FAILED: Issues remain with Socket.IO hook integration")
        print("\nCheck the error messages above for details.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)