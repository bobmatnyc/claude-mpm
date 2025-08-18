#!/usr/bin/env python3
"""Test script to verify dashboard error fixes."""

import sys
import os
import time
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.socketio.server.core import SocketIOServer
from claude_mpm.services.socketio.server.broadcaster import EventBroadcaster

def test_dashboard_errors():
    """Test that dashboard handles problematic events without errors."""
    
    print("Testing dashboard error fixes...")
    
    # Initialize the server
    server = SocketIOServer(port=8080)
    broadcaster = EventBroadcaster(server)
    
    # Start server in background
    server.start()
    time.sleep(2)
    
    print(f"SocketIO server started on port 8080")
    print(f"Dashboard URL: http://localhost:8080/dashboard")
    
    # Test problematic events that caused errors
    test_events = [
        {
            "type": "hook",
            "subtype": None,  # This was causing the error in file-tool-tracker.js
            "data": {"tool_name": "Read"},
            "timestamp": time.time() * 1000
        },
        {
            "type": "hook", 
            "subtype": "",  # Empty string should also be handled
            "data": {"tool_name": "Write"},
            "timestamp": time.time() * 1000
        },
        {
            "type": "hook",
            "hook_event_name": 123,  # Non-string value that was causing error in event-viewer.js
            "data": {"tool_name": "Edit"},
            "timestamp": time.time() * 1000
        },
        {
            "type": "hook",
            "hook_event_name": None,  # Null value
            "data": {"tool_name": "Bash"},
            "timestamp": time.time() * 1000
        },
        {
            "type": "hook",
            "subtype": "pre_tool",  # Normal event for comparison
            "data": {"tool_name": "TodoWrite"},
            "timestamp": time.time() * 1000
        }
    ]
    
    print("\nBroadcasting test events...")
    for i, event in enumerate(test_events, 1):
        broadcaster.emit_event(event)
        print(f"  Sent event {i}: {event.get('type')}.{event.get('subtype', 'null')} with hook_event_name={event.get('hook_event_name', 'undefined')}")
        time.sleep(0.5)
    
    print("\n✅ All test events sent successfully!")
    print("\nPlease open the dashboard in your browser and check:")
    print("1. No errors in browser console")
    print("2. All events appear in the Events tab")
    print("3. File operations are tracked correctly in the Files tab")
    print("\nPress Ctrl+C to stop the server...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.stop()
        print("Server stopped.")

if __name__ == "__main__":
    test_dashboard_errors()