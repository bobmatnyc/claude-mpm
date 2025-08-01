#!/usr/bin/env python3
"""Simple Socket.IO connection test without namespaces."""

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


def test_basic_connection():
    """Test basic Socket.IO connection without namespaces."""
    print("=== Testing Basic Socket.IO Connection ===")
    
    if not SOCKETIO_AVAILABLE:
        print("❌ python-socketio not available")
        return False
    
    try:
        # Create simple client
        sio = socketio.Client(
            logger=True,  # Enable logging to see what's happening
            engineio_logger=True
        )
        
        connected = False
        
        @sio.event
        def connect():
            nonlocal connected
            connected = True
            print("✓ Connected to Socket.IO server")
        
        @sio.event
        def disconnect():
            print("ℹ️  Disconnected from Socket.IO server")
        
        @sio.event
        def connect_error(data):
            print(f"❌ Connection error: {data}")
        
        # Connect to main namespace (no specific namespace)
        print("Connecting to http://localhost:8765...")
        sio.connect('http://localhost:8765', wait=True)
        
        # Wait to see if connection works
        time.sleep(2)
        
        if connected:
            print("✅ Basic connection successful")
            
            # Try to emit a test event
            print("Emitting test event...")
            sio.emit('test', {'message': 'hello from client'})
            
            # Wait for any responses
            time.sleep(1)
            
            result = True
        else:
            print("❌ Connection failed")
            result = False
        
        # Cleanup
        sio.disconnect()
        return result
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_namespace_connection_with_auth():
    """Test namespace connection with authentication.""" 
    print("\n=== Testing Namespace Connection with Auth ===")
    
    if not SOCKETIO_AVAILABLE:
        print("❌ python-socketio not available")
        return False
    
    try:
        # Create client with auth
        sio = socketio.Client(logger=True, engineio_logger=True)
        
        connected_namespaces = []
        
        @sio.event
        def connect():
            print("✓ Connected to main namespace")
        
        @sio.event
        def connect_error(data):
            print(f"❌ Main connection error: {data}")
        
        # Set up namespace-specific handlers
        @sio.event(namespace='/system')
        def connect():
            connected_namespaces.append('/system')
            print("✓ Connected to /system namespace")
        
        @sio.event(namespace='/system')
        def connect_error(data):
            print(f"❌ /system connection error: {data}")
        
        @sio.event(namespace='/hook')
        def connect():
            connected_namespaces.append('/hook')
            print("✓ Connected to /hook namespace")
        
        @sio.event(namespace='/hook')
        def connect_error(data):
            print(f"❌ /hook connection error: {data}")
        
        # Connect with auth token
        auth_data = {'token': 'dev-token'}  # Default dev token from server
        
        print("Connecting with authentication...")
        sio.connect(
            'http://localhost:8765',
            auth=auth_data,
            namespaces=['/system', '/hook'],
            wait=True
        )
        
        # Wait for connections
        time.sleep(3)
        
        print(f"Connected namespaces: {connected_namespaces}")
        
        success = len(connected_namespaces) > 0
        
        # Cleanup  
        sio.disconnect()
        
        return success
        
    except Exception as e:
        print(f"❌ Namespace connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run connection tests."""
    print("Simple Socket.IO Connection Test")
    print("=" * 50)
    
    # Test 1: Basic connection
    basic_success = test_basic_connection()
    
    # Test 2: Namespace connection with auth
    ns_success = test_namespace_connection_with_auth()
    
    # Summary
    print("\n" + "=" * 50)
    print("Connection Test Results:")
    print(f"1. Basic Connection: {'✓ PASS' if basic_success else '❌ FAIL'}")
    print(f"2. Namespace + Auth: {'✓ PASS' if ns_success else '❌ FAIL'}")
    
    if basic_success and ns_success:
        print("\n✅ Socket.IO connections are working")
    elif basic_success:
        print("\n⚠️  Basic connection works, but namespace issues remain")
    else:
        print("\n❌ Socket.IO connection issues detected")
    
    return 0 if basic_success else 1


if __name__ == "__main__":
    sys.exit(main())