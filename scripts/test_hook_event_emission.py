#!/usr/bin/env python3
"""
Test script to emit a hook event to an existing Socket.IO server.

This simulates what the hook handler does when it emits events.
"""

import requests
import json
from datetime import datetime

def emit_hook_event():
    """Emit a test hook event to the Socket.IO server."""
    
    # Test hook event (similar to what the hook handler sends)
    event_data = {
        "namespace": "/hook",
        "event": "pre_tool",
        "data": {
            "tool_name": "Bash",
            "session_id": "test_session_" + str(int(datetime.now().timestamp())),
            "timestamp": datetime.now().isoformat(),
            "message": "Testing hook event emission after broadcast fix"
        }
    }
    
    try:
        print("📤 Sending hook event to Socket.IO server...")
        print(f"🎯 Event: {event_data['namespace']}/{event_data['event']}")
        print(f"📊 Data: {json.dumps(event_data['data'], indent=2)}")
        
        response = requests.post(
            "http://localhost:8765/emit",
            json=event_data,
            timeout=5.0
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result['message']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is the Socket.IO server running on port 8765?")
        print("💡 Start the server with: python -m claude_mpm.services.websocket_server")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    emit_hook_event()