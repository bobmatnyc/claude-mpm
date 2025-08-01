#!/usr/bin/env python3
"""Test using synchronous Socket.IO client for hooks"""

import socketio
from datetime import datetime

# Create a synchronous client
sio = socketio.Client()

# Connect
print("Connecting to Socket.IO server...")
sio.connect('http://localhost:8765')

# Emit test event
event_data = {
    'type': 'hook.user_prompt',
    'timestamp': datetime.now().isoformat(),
    'data': {
        'event_type': 'user_prompt',
        'prompt_text': 'Test from sync client',
        'session_id': 'sync-test-123'
    }
}

print("Emitting test event...")
sio.emit('claude_event', event_data)

# Give server time to process
import time
time.sleep(0.5)

# Disconnect
sio.disconnect()
print("Done!")