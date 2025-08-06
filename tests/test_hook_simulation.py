#!/usr/bin/env python3
"""Simulate a hook event end-to-end"""

import json
import subprocess
import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

print("=== Testing Hook to Socket.IO Flow ===")

# 1. First verify Socket.IO server is running
print("\n1. Checking Socket.IO server health...")
result = subprocess.run(['curl', '-s', 'http://localhost:8765/health'], capture_output=True, text=True)
if result.returncode == 0:
    health = json.loads(result.stdout)
    print(f"✓ Server healthy: {health['server']} on port {health['port']}")
else:
    print("✗ Server not responding")
    sys.exit(1)

# 2. Simulate a hook event by calling the hook handler directly
print("\n2. Simulating hook event...")

# Create a fake hook event
hook_event = {
    "hook_event_name": "UserPromptSubmit",
    "prompt": "Test prompt from simulation script",
    "session_id": "test-simulation-123",
    "cwd": os.getcwd()
}

# Set environment variables
env = os.environ.copy()
env['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
env['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), '..', 'src')

# Call the hook handler
hook_handler_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'claude_mpm', 'hooks', 'claude_hooks', 'hook_handler.py')
proc = subprocess.Popen(
    [sys.executable, hook_handler_path],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env,
    text=True
)

stdout, stderr = proc.communicate(input=json.dumps(hook_event))

print(f"Hook handler stdout: {stdout}")
if stderr:
    print(f"Hook handler stderr: {stderr}")

# 3. Wait a moment for event to be processed
print("\n3. Waiting for event processing...")
time.sleep(1)

# 4. Check server event history
print("\n4. Checking server event history...")
from claude_mpm.core.socketio_pool import stop_connection_pool

# Import and use the check script logic
import socketio

sio = socketio.Client()
events_found = []

@sio.event
def connect():
    print("Connected to check history")
    sio.emit('get_history', {'limit': 10})

@sio.event
def history(data):
    events = data.get('events', [])
    print(f"\nFound {len(events)} events in history:")
    for event in events:
        event_type = event.get('type', 'unknown')
        if 'hook' in event_type:
            events_found.append(event)
            print(f"  ✓ {event_type} at {event.get('timestamp', 'no timestamp')}")
            if event.get('data', {}).get('prompt_text'):
                print(f"    Prompt: {event['data']['prompt_text'][:50]}...")
        else:
            print(f"  - {event_type}")
    sio.disconnect()

try:
    sio.connect('http://localhost:8765')
    time.sleep(0.5)
except Exception as e:
    print(f"Failed to check history: {e}")

# 5. Summary
print("\n=== Summary ===")
if events_found:
    print(f"✓ Successfully found {len(events_found)} hook events in Socket.IO server")
    print("✓ Hook to Socket.IO integration is working!")
else:
    print("✗ No hook events found in server history")
    print("✗ Check hook handler stderr output above for errors")

# Cleanup
stop_connection_pool()