#!/usr/bin/env python3
"""
Test script to send events via Socket.IO client to test git diff feature
"""

import json
import time
from datetime import datetime

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False

def send_file_write_event():
    """Send a test file write event via socket.io"""
    if not SOCKETIO_AVAILABLE:
        print("ERROR: python-socketio package not available. Install with: pip install python-socketio")
        return
        
    sio = socketio.SimpleClient()
    
    try:
        # Connect to the socket.io server
        sio.connect('http://localhost:8080')
        print("Connected to Socket.IO server")
        
        # Create a test write event
        test_event = {
            "type": "hook",
            "subtype": "post_tool",
            "timestamp": datetime.now().isoformat(),
            "id": "test_write_002",
            "data": {
                "tool_name": "Write",
                "session_id": "test_session_002", 
                "tool_parameters": {
                    "file_path": "/Users/masa/Projects/claude-mpm/test_file.py"
                },
                "working_directory": "/Users/masa/Projects/claude-mpm",
                "duration_ms": 120,
                "success": True,
                "exit_code": 0,
                "event_type": "post_tool"
            }
        }
        
        # Send the event
        sio.emit('hook_event', test_event)
        print(f"Sent test write event: {test_event['data']['tool_name']} - {test_event['data']['tool_parameters']['file_path']}")
        
        # Also send an Edit event to be sure
        edit_event = {
            "type": "hook", 
            "subtype": "pre_tool",
            "timestamp": datetime.now().isoformat(),
            "id": "test_edit_001",
            "data": {
                "tool_name": "Edit",
                "session_id": "test_session_003",
                "tool_parameters": {
                    "file_path": "/Users/masa/Projects/claude-mpm/src/claude_mpm/web/static/js/dashboard.js"
                },
                "working_directory": "/Users/masa/Projects/claude-mpm",
                "event_type": "pre_tool"
            }
        }
        
        sio.emit('hook_event', edit_event)
        print(f"Sent test edit event: {edit_event['data']['tool_name']} - {edit_event['data']['tool_parameters']['file_path']}")
        
        print("\nTest events sent successfully!")
        print("Now check the dashboard:")
        print("1. The dashboard should be open in your browser")
        print("2. Go to the Files tab")
        print("3. Look for the write operations and click on them")
        print("4. You should see 'View Git Diff' buttons for Write/Edit operations")
        
        # Wait a moment then disconnect
        time.sleep(2)
        sio.disconnect()
        
    except Exception as e:
        print(f"Error: {e}")
        try:
            sio.disconnect()
        except:
            pass

if __name__ == "__main__":
    send_file_write_event()