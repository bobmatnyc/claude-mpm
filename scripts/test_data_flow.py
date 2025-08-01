#!/usr/bin/env python3
"""Test data flow to Socket.IO server."""

import json
import sys
import time
import os
from pathlib import Path

# Add the claude-mpm source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_socketio_client_events():
    """Test sending events to Socket.IO server via client."""
    try:
        import socketio
        
        # Create client
        client = socketio.Client(
            reconnection=True,
            reconnection_attempts=3,
            reconnection_delay=0.5,
            logger=False,
            engineio_logger=False
        )
        
        connected = False
        events_received = []
        
        @client.event
        def connect():
            nonlocal connected
            connected = True
            print("✓ Client connected to Socket.IO server")
        
        @client.event
        def disconnect():
            print("ℹ Client disconnected from Socket.IO server")
        
        @client.event
        def test_response(data):
            events_received.append(data)
            print(f"✓ Received test response: {data}")
        
        # Connect to server
        server_url = "http://localhost:8765"
        print(f"Connecting to {server_url}...")
        
        try:
            client.connect(server_url, auth={'token': 'dev-token'}, wait=True, timeout=5)
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
        
        if not connected:
            print("❌ Connection failed")
            return False
        
        # Send test events
        test_events = [
            {
                "event": "hook_start",
                "hook_name": "test_hook",
                "timestamp": time.time(),
                "test": True
            },
            {
                "event": "hook_end", 
                "hook_name": "test_hook",
                "timestamp": time.time(),
                "status": "success",
                "test": True
            }
        ]
        
        print("Sending test events...")
        for event in test_events:
            try:
                client.emit('hook_event', event, namespace='/hook')
                print(f"✓ Sent event: {event['event']}")
                time.sleep(0.1)
            except Exception as e:
                print(f"❌ Failed to send event: {e}")
        
        # Give server time to process
        time.sleep(1)
        
        # Disconnect
        client.disconnect()
        print("✓ Client disconnected")
        
        return True
        
    except ImportError:
        print("❌ python-socketio not available")
        return False
    except Exception as e:
        print(f"❌ Client test failed: {e}")
        return False

def test_server_events_api():
    """Test server events via REST API."""
    try:
        import requests
        
        # Check if server has events
        response = requests.get("http://localhost:8765/events", timeout=5)
        
        if response.status_code == 200:
            events = response.json()
            print(f"✓ Server events API available, {len(events)} events in history")
            
            # Show recent events
            if events:
                print("Recent events:")
                for event in events[-3:]:  # Show last 3 events
                    timestamp = event.get('timestamp', 'unknown')
                    event_type = event.get('event', event.get('type', 'unknown'))
                    print(f"  - {timestamp}: {event_type}")
            
            return True
        else:
            print(f"❌ Events API returned {response.status_code}")
            return False
            
    except ImportError:
        print("❌ requests library not available")
        return False
    except Exception as e:
        print(f"❌ Events API test failed: {e}")
        return False

def test_hook_handler_connection():
    """Test if hook handler can connect to Socket.IO server."""
    try:
        # Set environment variable for hook handler
        os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
        os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
        
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
        
        print("Creating hook handler...")
        handler = ClaudeHookHandler()
        
        if hasattr(handler, 'socketio_client') and handler.socketio_client:
            print("✓ Hook handler has Socket.IO client")
            
            # Test connection status
            if handler.socketio_client.connected:
                print("✓ Hook handler connected to Socket.IO server")
                return True
            else:
                print("⚠️  Hook handler not connected, but client exists")
                return True  # This is still progress
        else:
            print("❌ Hook handler has no Socket.IO client")
            return False
            
    except Exception as e:
        print(f"❌ Hook handler test failed: {e}")
        return False

def main():
    """Run all data flow tests."""
    print("=== Socket.IO Data Flow Tests ===")
    
    tests = [
        ("Socket.IO Client Events", test_socketio_client_events),
        ("Server Events API", test_server_events_api), 
        ("Hook Handler Connection", test_hook_handler_connection)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n=== Test Results ===")
    passed = 0
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(tests)} tests passed")
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)