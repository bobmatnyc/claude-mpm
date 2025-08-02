#!/usr/bin/env python3
"""
Quick Socket.IO connection test for debugging dashboard issue
"""

import socketio
import time
import json

def test_connection():
    print("Testing Socket.IO connection to localhost:8765...")
    
    # Create a Socket.IO client
    sio = socketio.Client()
    
    @sio.event
    def connect():
        print("✅ Successfully connected to Socket.IO server!")
        print(f"Socket ID: {sio.sid}")
        
        # Request status
        print("Requesting server status...")
        sio.emit('get_status')
        
        # Send a test event
        test_event = {
            'type': 'test.debug',
            'timestamp': time.time(),
            'data': {
                'message': 'Debug test event from manual connection test',
                'source': 'debug_script'
            }
        }
        print(f"Sending test event: {json.dumps(test_event, indent=2)}")
        sio.emit('claude_event', test_event)
    
    @sio.event
    def disconnect():
        print("❌ Disconnected from Socket.IO server")
    
    @sio.event
    def connect_error(data):
        print(f"❌ Connection error: {data}")
    
    @sio.event
    def status(data):
        print(f"📊 Server status: {json.dumps(data, indent=2)}")
    
    @sio.event
    def claude_event(data):
        print(f"📨 Received claude_event: {json.dumps(data, indent=2)}")
    
    try:
        # Connect to the server
        sio.connect('http://localhost:8765')
        
        # Keep connection alive for a few seconds
        time.sleep(2)
        
        # Request history
        print("Requesting event history...")
        sio.emit('get_history', {'limit': 5, 'event_types': []})
        
        # Wait a bit more
        time.sleep(1)
        
        # Disconnect
        sio.disconnect()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_connection()
    if success:
        print("\n✅ Socket.IO connection test completed successfully")
    else:
        print("\n❌ Socket.IO connection test failed")