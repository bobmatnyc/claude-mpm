#!/usr/bin/env python3
"""Test the code discovery handlers directly."""

import sys

sys.path.insert(0, 'src')

import threading
import time

from claude_mpm.services.socketio.server.main import SocketIOServer

# Start server
server = SocketIOServer(host='localhost', port=8766)  # Different port to avoid conflict

def start_server():
    """Start server in thread."""
    server.start_sync()

# Start in background
thread = threading.Thread(target=start_server, daemon=True)
thread.start()

# Wait for server to initialize
print("Waiting for server to start...")
time.sleep(3)

# Now test with client
import socketio

sio = socketio.Client()
results = []

@sio.on('code.directory_discovered')
def on_dir(data):
    print(f"✅ Got directory discovered: {data.get('path', 'unknown')}")
    results.append(('dir', data))

@sio.on('code.file_analyzed')
def on_file(data):
    print(f"✅ Got file analyzed: {data.get('path', 'unknown')}")
    results.append(('file', data))

@sio.on('code.discovery_error')
def on_error(data):
    print(f"❌ Got error: {data}")
    results.append(('error', data))

# Connect
print("\nConnecting to test server...")
sio.connect('http://localhost:8766')
time.sleep(1)

# Test discovery
print("\nTesting code:discover:top_level...")
sio.emit('code:discover:top_level', {
    'path': '/Users/masa/Projects/claude-mpm',
    'request_id': 'test-123'
})
time.sleep(2)

# Test file analysis
print("\nTesting code:analyze:file...")
sio.emit('code:analyze:file', {
    'path': '/Users/masa/Projects/claude-mpm/src/claude_mpm/__init__.py',
    'request_id': 'test-456'
})
time.sleep(2)

# Results
print(f"\n📊 Results: {len(results)} events received")
for event_type, data in results:
    if event_type == 'dir':
        children = data.get('children', [])
        print(f"  - Directory with {len(children)} children")
    elif event_type == 'file':
        nodes = data.get('nodes', [])
        print(f"  - File with {len(nodes)} nodes")

sio.disconnect()
print("\n✅ Test complete!")

# Cleanup
server.stop()
