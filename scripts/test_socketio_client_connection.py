#!/usr/bin/env python3
"""Test Socket.IO client connection to see what's happening"""

import socketio
import time
import asyncio

# Create a Socket.IO client
sio = socketio.Client()

events_received = []

@sio.event
def connect():
    print("✓ Connected to main namespace")

@sio.event
def disconnect():
    print("✗ Disconnected from main namespace")

# Set up handlers for all namespaces
namespaces = ['/system', '/session', '/claude', '/agent', '/hook', '/todo', '/memory', '/log']

for ns in namespaces:
    def make_handlers(namespace):
        @sio.on('connect', namespace=namespace)
        def on_connect():
            print(f"✓ Connected to {namespace}")
        
        @sio.on('disconnect', namespace=namespace)
        def on_disconnect():
            print(f"✗ Disconnected from {namespace}")
        
        @sio.on('*', namespace=namespace)
        def catch_all(event, *args):
            print(f"📨 Event on {namespace}: {event} - {args}")
            events_received.append((namespace, event, args))
    
    make_handlers(ns)

# Try to connect
try:
    print("Attempting to connect to Socket.IO server at http://localhost:8765...")
    sio.connect('http://localhost:8765', 
                auth={'token': 'dev-token'},
                namespaces=['/', '/system', '/session', '/claude', '/agent', '/hook', '/todo', '/memory', '/log'])
    
    print("\nWaiting for events (10 seconds)...")
    print("Try running this in another terminal:")
    print('curl -X POST http://localhost:8765/emit -H "Content-Type: application/json" -d \'{"namespace": "hook", "event": "test", "data": {"msg": "hello"}}\'')
    
    # Wait for events
    time.sleep(10)
    
    print(f"\nReceived {len(events_received)} events")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        sio.disconnect()
    except:
        pass

print("\nDone!")