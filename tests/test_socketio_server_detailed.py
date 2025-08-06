#!/usr/bin/env python3
"""Detailed test to verify Socket.IO server compatibility."""

import sys
import os
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_socketio_endpoint(port):
    """Test if a Socket.IO server is running on the given port."""
    print(f"\n🔍 Testing Socket.IO server on port {port}...")
    
    try:
        import urllib.request
        import json
        
        # Test Socket.IO endpoint
        socketio_url = f'http://localhost:{port}/socket.io/'
        print(f"  Checking Socket.IO endpoint: {socketio_url}")
        
        try:
            # Make a request to the Socket.IO endpoint
            request = urllib.request.Request(
                socketio_url + "?EIO=4&transport=polling",
                headers={'Content-Type': 'application/json'}
            )
            
            response = urllib.request.urlopen(request, timeout=5)
            content = response.read().decode('utf-8')
            
            print(f"  ✓ Socket.IO endpoint responded (status: {response.getcode()})")
            print(f"  Response preview: {content[:100]}...")
            
            # Check if this looks like Engine.IO/Socket.IO response
            if content.startswith('0'):  # Engine.IO open packet
                print("  ✓ Looks like a valid Socket.IO server")
                return True
            else:
                print("  ⚠️  Response doesn't look like Socket.IO format")
                return False
                
        except urllib.error.HTTPError as e:
            if e.code == 400:
                print("  ✓ Got 400 response (normal for Socket.IO without proper handshake)")
                return True
            else:
                print(f"  ❌ HTTP error {e.code}: {e.reason}")
                return False
                
    except Exception as e:
        print(f"  ❌ Error testing endpoint: {e}")
        return False

def test_manual_socketio_connection(port):
    """Test manual Socket.IO client connection."""
    print(f"\n🔗 Testing manual Socket.IO client connection to port {port}...")
    
    try:
        import socketio
        
        # Create client with debug
        sio = socketio.Client(
            reconnection=False,
            logger=True,
            engineio_logger=True
        )
        
        @sio.event
        def connect():
            print("  ✅ Connected to Socket.IO server!")
            
        @sio.event
        def connect_error(data):
            print(f"  ❌ Connection error: {data}")
            
        @sio.event 
        def disconnect():
            print("  🔌 Disconnected from Socket.IO server")
            
        # Try to connect
        server_url = f"http://localhost:{port}"
        print(f"  Attempting connection to: {server_url}")
        
        try:
            # Test connection with auth
            auth_data = {'token': 'dev-token'}
            sio.connect(server_url, auth=auth_data, namespaces=['/system'], wait_timeout=3)
            
            if sio.connected:
                print("  ✅ Successfully connected with authentication")
                
                # Test emitting an event
                sio.emit('test_event', {'message': 'test'}, namespace='/system')
                print("  ✅ Test event emitted")
                
                # Wait a moment then disconnect
                time.sleep(1)
                sio.disconnect()
                return True
            else:
                print("  ❌ Connection failed")
                return False
                
        except Exception as conn_error:
            print(f"  ❌ Connection failed: {conn_error}")
            return False
            
    except ImportError:
        print("  ❌ python-socketio not available")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    """Run detailed Socket.IO server tests."""
    print("🔍 Detailed Socket.IO Server Testing")
    print("=" * 50)
    
    # Set debug mode
    os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    
    # Find running servers
    import socket
    ports_to_check = [8765, 8080, 8081, 8082, 8083, 8084, 8085]
    running_servers = []
    
    print("🔍 Scanning for running servers...")
    for port in ports_to_check:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    running_servers.append(port)
                    print(f"  ✓ Server detected on port {port}")
        except:
            continue
    
    if not running_servers:
        print("❌ No servers detected. Start a server with: claude-mpm run --monitor")
        return
    
    # Test each running server
    socketio_servers = []
    for port in running_servers:
        if test_socketio_endpoint(port):
            socketio_servers.append(port)
            
    print(f"\n📊 Summary:")
    print(f"  Servers detected: {len(running_servers)} on ports {running_servers}")
    print(f"  Socket.IO compatible: {len(socketio_servers)} on ports {socketio_servers}")
    
    # Test manual connection to Socket.IO servers
    if socketio_servers:
        print(f"\n🔗 Testing manual connections...")
        for port in socketio_servers:
            test_manual_socketio_connection(port)
    else:
        print("\n❌ No Socket.IO compatible servers found")
        print("💡 To start a proper Claude MPM Socket.IO server:")
        print("   claude-mpm run --monitor --websocket-port 8765")

if __name__ == "__main__":
    main()