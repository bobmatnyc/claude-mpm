#!/usr/bin/env python3
"""Final test of dashboard code analysis functionality."""

import sys
sys.path.insert(0, 'src')

import time
import threading
from claude_mpm.services.socketio.server.main import SocketIOServer

def start_server():
    """Start the dashboard server."""
    print("Starting dashboard server on port 8765...")
    server = SocketIOServer(host='localhost', port=8765)
    try:
        server.start_sync()
    except Exception as e:
        print(f"Server error: {e}")

# Start server in background
server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

# Wait for server to be ready
print("Waiting for server to initialize...")
time.sleep(5)

# Now test with client
import socketio

sio = socketio.Client()
events_received = []

@sio.on('code:directory:discovered')
def on_dir(data):
    path = data.get('path', 'unknown')
    print(f"✅ Directory discovered: {path[:60]}...")
    events_received.append(('dir', data))

@sio.on('code:file:discovered')
def on_file(data):
    path = data.get('path', 'unknown')
    print(f"✅ File discovered: {path[:60]}...")
    events_received.append(('file', data))

@sio.on('code:file:analyzed')
def on_analyzed(data):
    path = data.get('path', 'unknown')
    print(f"✅ File analyzed: {path[:60]}...")
    events_received.append(('analyzed', data))

@sio.on('code:analysis:error')
def on_error(data):
    print(f"❌ Error: {data}")
    events_received.append(('error', data))

try:
    print("\n🔌 Connecting to dashboard...")
    sio.connect('http://localhost:8765')
    print("✅ Connected!")
    
    time.sleep(1)
    
    print("\n📤 Test 1: Discover top-level directories...")
    sio.emit('code:discover:top_level', {
        'path': '/Users/masa/Projects/claude-mpm/src',
        'request_id': 'test-1'
    })
    time.sleep(5)  # Give more time for events
    
    print("\n📤 Test 2: Analyze a Python file...")
    sio.emit('code:analyze:file', {
        'path': '/Users/masa/Projects/claude-mpm/src/claude_mpm/__init__.py',
        'request_id': 'test-2'
    })
    time.sleep(5)  # Give more time for events
    
    # Results
    print("\n" + "="*60)
    print("📊 RESULTS")
    print("="*60)
    print(f"Total events received: {len(events_received)}")
    
    if events_received:
        print("\n✅ CODE ANALYSIS IS WORKING!")
        print("\nBreakdown:")
        dirs = sum(1 for t, _ in events_received if t == 'dir')
        files = sum(1 for t, _ in events_received if t == 'file')
        analyzed = sum(1 for t, _ in events_received if t == 'analyzed')
        errors = sum(1 for t, _ in events_received if t == 'error')
        
        print(f"  📁 Directories discovered: {dirs}")
        print(f"  📄 Files discovered: {files}")
        print(f"  🔍 Files analyzed: {analyzed}")
        print(f"  ❌ Errors: {errors}")
        
        print("\n🎉 The Analyze button in the Code tab should now work!")
    else:
        print("\n❌ No events received - there may still be issues")
        print("Check that:")
        print("  1. Event handlers are registered")
        print("  2. CodeTreeAnalyzer is working")
        print("  3. Events are using correct names (colons)")
    
except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
finally:
    if sio.connected:
        sio.disconnect()
        print("\n🔌 Disconnected")

print("\n✅ Test complete!")