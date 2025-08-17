#!/usr/bin/env python3
"""Debug what data Claude sends in SubagentStop events"""

import socketio
import json
from datetime import datetime

sio = socketio.Client()

print("Monitoring for SubagentStop events...")
print("Trigger a Task tool to see the data...\n")

@sio.event
def connect():
    print("Connected to Socket.IO server")

@sio.event
def claude_event(data):
    if data.get('type') == 'hook.subagent_stop':
        print(f"\n{'='*60}")
        print(f"SubagentStop Event at {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print("Full event data:")
        print(json.dumps(data, indent=2))
        
        event_data = data.get('data', {})
        print(f"\nExtracted fields:")
        print(f"  - agent_type: {event_data.get('agent_type', 'NOT PROVIDED')}")
        print(f"  - agent_id: {event_data.get('agent_id', 'NOT PROVIDED')}")
        print(f"  - reason: {event_data.get('reason', 'NOT PROVIDED')}")
        print(f"  - session_id: {event_data.get('session_id', 'NOT PROVIDED')}")
        print(f"  - has_results: {event_data.get('has_results', 'NOT PROVIDED')}")

try:
    sio.connect('http://localhost:8765')
    # Keep listening
    while True:
        import time
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopping monitor...")
    sio.disconnect()