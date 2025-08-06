#\!/usr/bin/env python3
import socketio
import time

def test_connection():
    print("Testing Socket.IO connection to localhost:8765...")
    
    sio = socketio.Client()
    
    @sio.event
    def connect():
        print("✅ Connected successfully\!")
        
    @sio.event
    def disconnect():
        print("❌ Disconnected")
        
    @sio.on('*')
    def catch_all(event, data):
        print(f"📨 Received event '{event}': {data}")
    
    try:
        sio.connect('http://localhost:8765')
        print("Waiting for events...")
        time.sleep(2)
        
        # Test sending a message
        sio.emit('test_message', {'data': 'Hello from test client'})
        time.sleep(1)
        
        sio.disconnect()
        print("Test completed\!")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
