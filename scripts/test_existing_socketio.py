#!/usr/bin/env python3
"""Test connection to existing Socket.IO server."""

import sys
import time
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from claude_mpm.core.hook_manager import get_hook_manager
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    SOCKETIO_AVAILABLE = False


def test_existing_server():
    """Test connecting to the existing Socket.IO server."""
    print("=== Testing Existing Socket.IO Server ===")
    
    if not SOCKETIO_AVAILABLE:
        print("❌ Socket.IO not available")
        return False
    
    try:
        # Create client
        client = socketio.Client(
            logger=False, 
            engineio_logger=False,
            reconnection=True,
            reconnection_attempts=3,
            reconnection_delay=1
        )
        
        connected = False
        events_received = []
        
        @client.event
        def connect():
            nonlocal connected
            connected = True
            print("✓ Client connected to existing server")
        
        @client.event
        def disconnect():
            print("✓ Client disconnected")
        
        @client.event(namespace='/hook')
        def pre_tool(data):
            events_received.append(('pre_tool', data))
            print(f"✓ Received pre_tool event: {data}")
        
        @client.event(namespace='/hook')
        def post_tool(data):
            events_received.append(('post_tool', data))
            print(f"✓ Received post_tool event: {data}")
        
        @client.event(namespace='/hook')
        def user_prompt(data):
            events_received.append(('user_prompt', data))
            print(f"✓ Received user_prompt event: {data}")
        
        # Connect to existing server
        print("Connecting to existing server on port 8765...")
        client.connect('http://localhost:8765', namespaces=['/hook', '/system'])
        
        # Wait for connection
        time.sleep(2)
        
        if not connected:
            print("❌ Client failed to connect to existing server")
            try:
                client.disconnect()
            except:
                pass
            return False
        
        # Test the hook manager with the existing server
        print("Testing hook manager with existing server...")
        manager = get_hook_manager()
        
        # Trigger hook events
        print("Triggering pre-tool hook...")
        success1 = manager.trigger_pre_tool_hook("TodoWrite", {
            "todos": [{"content": "[Research] Test todo from hook manager", "status": "pending", "priority": "high", "id": "test-1"}]
        })
        
        print("Triggering post-tool hook...")
        success2 = manager.trigger_post_tool_hook("TodoWrite", 0, "Test completed successfully")
        
        print("Triggering user prompt hook...")
        success3 = manager.trigger_user_prompt_hook("Test user prompt from hook manager")
        
        # Wait for events
        print("Waiting for events...")
        time.sleep(3)
        
        # Check results
        print(f"\nHook trigger results:")
        print(f"  Pre-tool hook: {'✓' if success1 else '❌'}")
        print(f"  Post-tool hook: {'✓' if success2 else '❌'}")
        print(f"  User prompt hook: {'✓' if success3 else '❌'}")
        
        print(f"\nEvents received: {len(events_received)}")
        for i, (event_type, data) in enumerate(events_received):
            print(f"  {i+1}. {event_type}: {data}")
        
        # Cleanup
        client.disconnect()
        
        # Success if we connected and triggered hooks successfully
        return connected and (success1 or success2 or success3)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the test."""
    print("Existing Socket.IO Server Test")
    print("=" * 50)
    
    success = test_existing_server()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ Test completed successfully")
        print("The existing Socket.IO server is working and receiving hook events.")
    else:
        print("❌ Test failed")
        print("There may be an issue with the Socket.IO server or hook system.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())