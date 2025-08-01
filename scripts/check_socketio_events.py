#!/usr/bin/env python3
"""Check Socket.IO server event history"""

import socketio
import time

sio = socketio.Client()
events_received = []

@sio.event
def connect():
    print("Connected to Socket.IO server")
    # Request event history
    sio.emit('get_history', {'limit': 50})

@sio.event
def history(data):
    print(f"\nReceived event history: {len(data.get('events', []))} events")
    for event in data.get('events', []):
        print(f"  - {event.get('type', 'unknown')}: {event.get('timestamp', 'no timestamp')}")
        if 'data' in event:
            print(f"    Data: {str(event['data'])[:100]}...")

@sio.event
def claude_event(data):
    print(f"\nReal-time event received: {data}")
    events_received.append(data)

@sio.on('*')
def catch_all(event, data):
    print(f"\nCaught event '{event}': {data}")

print("Connecting to Socket.IO server at localhost:8765...")
try:
    sio.connect('http://localhost:8765')
    
    # Wait for events
    print("Listening for events for 5 seconds...")
    time.sleep(5)
    
    print(f"\nTotal real-time events received: {len(events_received)}")
    
    sio.disconnect()
except Exception as e:
    print(f"Error: {e}")