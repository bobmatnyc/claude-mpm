#!/usr/bin/env python3
"""Test emitting events in the correct format for the dashboard"""

import requests
import json

# The dashboard expects specific event names on each namespace
test_events = [
    # Hook namespace expects: user_prompt, pre_tool, post_tool
    {"namespace": "hook", "event": "user_prompt", "data": {"prompt": "Test prompt from script"}},
    {"namespace": "hook", "event": "pre_tool", "data": {"tool": "Bash", "args": {"command": "ls"}}},
    {"namespace": "hook", "event": "post_tool", "data": {"tool": "Bash", "result": "success"}},
    
    # System namespace expects: status
    {"namespace": "system", "event": "status", "data": {"message": "Test status update"}},
    
    # Session namespace expects: start, end
    {"namespace": "session", "event": "start", "data": {"session_id": "test-session-123"}},
    
    # Claude namespace expects: status_changed, output
    {"namespace": "claude", "event": "output", "data": {"type": "stdout", "content": "Test output"}},
]

print("Emitting test events to Socket.IO server...")

for event in test_events:
    try:
        response = requests.post(
            'http://localhost:8765/emit',
            json=event,
            headers={'Content-Type': 'application/json'}
        )
        print(f"✓ Sent {event['namespace']}/{event['event']}: {response.json()}")
    except Exception as e:
        print(f"❌ Failed to send {event['namespace']}/{event['event']}: {e}")

print("\nCheck your dashboard - these events should appear!")