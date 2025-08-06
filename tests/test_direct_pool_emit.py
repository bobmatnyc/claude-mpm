#!/usr/bin/env python3
"""Test connection pool emission directly with verbose logging"""

import sys
import os
import time
import logging
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Enable all logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set environment
os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'

from claude_mpm.core.socketio_pool import get_connection_pool

print("=== Testing Direct Connection Pool Emission ===")

# Get connection pool
pool = get_connection_pool()
print(f"\nInitial pool stats: {pool.get_stats()}")

# Test 1: Simple event
print("\n1. Testing simple event emission...")
event_data = {
    'type': 'hook.test',
    'timestamp': datetime.now().isoformat(),
    'data': {
        'message': 'Direct pool test',
        'test_id': 'pool-test-1'
    }
}

pool.emit_event('', 'claude_event', event_data)
print("Event queued for emission")

# Wait for batch processing
time.sleep(1)

print(f"\nPool stats after emission: {pool.get_stats()}")

# Test 2: Multiple events
print("\n2. Testing multiple events...")
for i in range(3):
    event_data = {
        'type': f'hook.test_{i}',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'message': f'Test event {i}',
            'test_id': f'pool-test-{i}'
        }
    }
    pool.emit_event('', 'claude_event', event_data)
    print(f"Queued event {i}")

time.sleep(1)

print(f"\nFinal pool stats: {pool.get_stats()}")

# Check if events made it to the server
import socketio
sio = socketio.Client()
found_events = []

@sio.event
def connect():
    print("\n3. Checking server for our events...")
    sio.emit('get_history', {'limit': 20})

@sio.event
def history(data):
    events = data.get('events', [])
    print(f"Server has {len(events)} total events")
    for event in events:
        if event.get('data', {}).get('test_id', '').startswith('pool-test'):
            found_events.append(event)
            print(f"  ✓ Found our test event: {event['data']['test_id']}")

try:
    sio.connect('http://localhost:8765')
    time.sleep(0.5)
    sio.disconnect()
except Exception as e:
    print(f"Failed to connect for history check: {e}")

print(f"\n=== Results ===")
print(f"Events sent: 4")
print(f"Events found in server: {len(found_events)}")
if len(found_events) == 4:
    print("✓ All events successfully delivered!")
else:
    print("✗ Some events were not delivered")

# Cleanup
pool.stop()