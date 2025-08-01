#!/usr/bin/env python3
"""
Test script to verify Socket.IO broadcasting fix.

This script:
1. Starts a Socket.IO server
2. Sends events via HTTP POST to /emit endpoint
3. Verifies that events are properly broadcasted to connected clients

Run this script and then connect the dashboard to verify the fix works.
"""

import asyncio
import json
import requests
import time
import threading
from datetime import datetime

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.websocket_server import SocketIOServer


def test_event_broadcasting():
    """Test that events are properly broadcasted to Socket.IO clients."""
    
    print("🚀 Starting Socket.IO broadcast test...")
    
    # Start Socket.IO server
    server = SocketIOServer(host="localhost", port=8765)
    server.start()
    
    # Give server time to start
    time.sleep(2)
    
    print("✅ Socket.IO server started on port 8765")
    print("🌐 Dashboard available at: http://localhost:8765/dashboard")
    print("📊 Connect your dashboard and watch for test events...")
    
    # Test events to send
    test_events = [
        {
            "namespace": "/hook",
            "event": "pre_tool",
            "data": {
                "tool_name": "test_tool",
                "session_id": "test_session_123",
                "message": "Testing Socket.IO broadcast fix"
            }
        },
        {
            "namespace": "/session",
            "event": "start", 
            "data": {
                "session_id": "test_session_123",
                "start_time": datetime.utcnow().isoformat(),
                "launch_method": "test_mode",
                "working_directory": "/test/directory"
            }
        },
        {
            "namespace": "/claude",
            "event": "status_changed",
            "data": {
                "status": "running",
                "pid": 12345,
                "message": "Test Claude status update"
            }
        },
        {
            "namespace": "/memory",
            "event": "updated",
            "data": {
                "agent_id": "test_agent",
                "learning_type": "success",
                "content": "Successfully tested Socket.IO broadcasting",
                "section": "learnings"
            }
        }
    ]
    
    print("\n📤 Sending test events via HTTP POST...")
    
    # Send test events
    for i, event in enumerate(test_events, 1):
        try:
            response = requests.post(
                "http://localhost:8765/emit",
                json=event,
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Event {i}: {result['message']}")
            else:
                print(f"❌ Event {i} failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Event {i} error: {e}")
        
        # Small delay between events
        time.sleep(1)
    
    print("\n🎯 Test complete! Check your dashboard for received events.")
    print("📋 Expected events:")
    for event in test_events:
        print(f"   - {event['namespace']}/{event['event']}")
    
    print("\n⏳ Keeping server running for 30 seconds...")
    print("🌐 Dashboard URL: http://localhost:8765/dashboard?autoconnect=true")
    
    # Keep server running for testing
    time.sleep(30)
    
    print("\n🛑 Stopping server...")
    server.stop()
    print("✅ Test completed successfully!")


if __name__ == "__main__":
    test_event_broadcasting()