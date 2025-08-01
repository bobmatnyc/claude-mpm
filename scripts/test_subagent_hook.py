#!/usr/bin/env python3
"""Test SubagentStop hook event"""

import json
import subprocess
import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

print("=== Testing SubagentStop Hook ===")

# Create a SubagentStop event
hook_event = {
    "hook_event_name": "SubagentStop",
    "agent_type": "research",
    "agent_id": "research-test-123",
    "reason": "completed",
    "session_id": "test-subagent-stop",
    "cwd": os.getcwd(),
    "results": {"task": "completed successfully"},
    "output": "Test output from subagent"
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

# Wait a moment for event to be processed
print("\nWaiting for event processing...")
time.sleep(1)

# Check server event history
print("\nChecking for SubagentStop event...")
import socketio

sio = socketio.Client()
found_subagent_stop = False

@sio.event
def connect():
    print("Connected to check history")
    sio.emit('get_history', {'limit': 20})

@sio.event
def history(data):
    global found_subagent_stop
    events = data.get('events', [])
    print(f"\nFound {len(events)} events in history")
    for event in events:
        event_type = event.get('type', 'unknown')
        if 'subagent_stop' in event_type:
            found_subagent_stop = True
            print(f"  ✓ Found SubagentStop event: {event_type}")
            event_data = event.get('data', {})
            print(f"    Agent: {event_data.get('agent_type')} ({event_data.get('agent_id')})")
            print(f"    Reason: {event_data.get('reason')}")
    sio.disconnect()

try:
    sio.connect('http://localhost:8765')
    time.sleep(0.5)
except Exception as e:
    print(f"Failed to check history: {e}")

if found_subagent_stop:
    print("\n✓ SubagentStop hook is working correctly!")
else:
    print("\n✗ SubagentStop event not found in history")
    print("  Check if Claude is actually sending SubagentStop events")