#!/usr/bin/env python3
"""Debug Socket.IO namespace connections."""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False


def test_namespace_connections():
    """Test connecting to different namespaces."""
    print("=== Testing Socket.IO Namespace Connections ===")
    
    if not SOCKETIO_AVAILABLE:
        print("❌ python-socketio not available")
        return False
    
    try:
        # Test each namespace individually
        namespaces_to_test = ['/system', '/hook', '/todo', '/log', '/session', '/claude', '/agent', '/memory']
        results = {}
        
        for namespace in namespaces_to_test:
            print(f"\nTesting namespace: {namespace}")
            
            # Create client for this namespace
            sio = socketio.Client(
                logger=False,
                engineio_logger=False,
                reconnection=False  # Disable for testing
            )
            
            connected = False
            error_msg = None
            
            @sio.event
            def connect():
                nonlocal connected
                connected = True
                print(f"  ✓ Connected to {namespace}")
            
            @sio.event
            def connect_error(data):
                nonlocal error_msg
                error_msg = str(data)
                print(f"  ❌ Connection error: {data}")
            
            @sio.event
            def disconnect():
                print(f"  ℹ️  Disconnected from {namespace}")
            
            try:
                # Connect to specific namespace
                sio.connect(
                    'http://localhost:8765',
                    namespaces=[namespace],
                    wait=True
                )
                
                # Wait a moment
                time.sleep(1)
                
                # Check connection status
                if connected and sio.connected:
                    print(f"  ✅ {namespace}: SUCCESS")
                    results[namespace] = True
                else:
                    print(f"  ❌ {namespace}: FAILED - not connected")
                    results[namespace] = False
                
                # Disconnect
                sio.disconnect()
                
            except Exception as e:
                print(f"  ❌ {namespace}: FAILED - {e}")
                results[namespace] = False
                try:
                    sio.disconnect()
                except:
                    pass
        
        # Summary
        print(f"\n{'='*50}")
        print("Namespace Connection Results:")
        for namespace, success in results.items():
            status = "✅ CONNECTED" if success else "❌ FAILED"
            print(f"  {namespace}: {status}")
        
        successful_namespaces = sum(1 for success in results.values() if success)
        total_namespaces = len(results)
        
        print(f"\nSummary: {successful_namespaces}/{total_namespaces} namespaces connected successfully")
        
        return successful_namespaces > 0
        
    except Exception as e:
        print(f"❌ Namespace testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_emission():
    """Test emitting events to working namespaces."""
    print("\n=== Testing Event Emission ===")
    
    if not SOCKETIO_AVAILABLE:
        print("❌ python-socketio not available")
        return False
    
    try:
        # Create a client that connects to multiple namespaces
        sio = socketio.Client(logger=False, engineio_logger=False)
        
        connected_namespaces = []
        events_received = []
        
        @sio.event
        def connect():
            print("✓ Main connection established")
        
        # Try to connect to all namespaces
        namespaces = ['/system', '/hook', '/todo']
        
        for namespace in namespaces:
            try:
                # Add event handlers for each namespace
                @sio.event(namespace=namespace)
                def test_event(data):
                    events_received.append((namespace, 'test_event', data))
                    print(f"  📨 Received test_event from {namespace}: {data}")
                
                connected_namespaces.append(namespace)
            except Exception as e:
                print(f"  ⚠️  Could not set up handler for {namespace}: {e}")
        
        print(f"Connecting to namespaces: {connected_namespaces}")
        
        # Connect
        sio.connect('http://localhost:8765', namespaces=connected_namespaces)
        
        # Wait for connection
        time.sleep(2)
        
        # Emit test events from server side
        print("Now triggering server-side events...")
        
        # Import server and emit events
        from claude_mpm.services.websocket_server import get_server_instance
        server = get_server_instance()
        
        # Emit test events
        server.emit_event('/system', 'test_event', {'message': 'test from system', 'source': 'debug'})
        server.emit_event('/hook', 'test_event', {'message': 'test from hook', 'source': 'debug'})
        server.emit_event('/todo', 'test_event', {'message': 'test from todo', 'source': 'debug'})
        
        print("Events emitted, waiting for responses...")
        time.sleep(3)
        
        # Check results
        print(f"\nEvents received: {len(events_received)}")
        for namespace, event_type, data in events_received:
            print(f"  - {namespace}/{event_type}: {data}")
        
        # Cleanup
        sio.disconnect()
        
        return len(events_received) > 0
        
    except Exception as e:
        print(f"❌ Event emission test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run debug tests."""
    print("Socket.IO Namespace Debug")
    print("=" * 50)
    
    # Test 1: Namespace connections
    ns_success = test_namespace_connections()
    
    # Test 2: Event emission
    event_success = test_event_emission()
    
    # Summary
    print("\n" + "=" * 50)
    print("Debug Results:")
    print(f"1. Namespace Connections: {'✓ PASS' if ns_success else '❌ FAIL'}")
    print(f"2. Event Emission: {'✓ PASS' if event_success else '❌ FAIL'}")
    
    if ns_success and event_success:
        print("\n✅ Socket.IO namespaces are working correctly")
    elif ns_success:
        print("\n⚠️  Namespaces connect but events may not be flowing properly")
    else:
        print("\n❌ Namespace connection issues detected")
    
    return 0 if ns_success else 1


if __name__ == "__main__":
    sys.exit(main())