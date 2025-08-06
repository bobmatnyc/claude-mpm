#!/usr/bin/env python3
"""
Test script to verify agent onclick fix by triggering some agent events
and checking if the dashboard can handle clicks correctly.
"""

import asyncio
import json
import time
import websockets
from datetime import datetime

async def send_test_events():
    """Send test agent events to the websocket server"""
    uri = "ws://localhost:8080"
    
    # Test agent events
    test_events = [
        {
            "type": "hook",
            "subtype": "pre_tool",
            "tool_name": "Task",
            "tool_parameters": {
                "subagent_type": "Research",
                "prompt": "Test research task"
            },
            "timestamp": datetime.now().isoformat(),
            "session_id": "test_session_001",
            "agent_type": "Research"
        },
        {
            "type": "agent",
            "subtype": "task_delegation", 
            "agent_type": "PM",
            "subagent_type": "Engineer",
            "timestamp": datetime.now().isoformat(),
            "description": "Test engineer delegation",
            "session_id": "test_session_002"
        },
        {
            "type": "hook",
            "subtype": "post_tool",
            "tool_name": "Edit",
            "agent_type": "Engineer",
            "timestamp": datetime.now().isoformat(),
            "session_id": "test_session_003",
            "file_path": "/test/file.py"
        }
    ]
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to websocket server")
            
            for i, event in enumerate(test_events, 1):
                message = json.dumps(event)
                await websocket.send(message)
                print(f"Sent test event {i}: {event['type']} - {event.get('subtype', 'N/A')}")
                await asyncio.sleep(0.5)
            
            print("\nTest events sent successfully!")
            print("Now you can:")
            print("1. Open dashboard at http://localhost:8080")
            print("2. Go to Agents tab")
            print("3. Click on agent cards to test if they respond correctly")
            print("4. Compare with Tools and Files tabs to ensure consistent behavior")
            
    except ConnectionRefusedError:
        print("Could not connect to websocket server on port 8080")
        print("Make sure the server is running with: python -m claude_mpm.services.websocket_server --port 8080")
    except Exception as e:
        print(f"Error sending test events: {e}")

if __name__ == "__main__":
    asyncio.run(send_test_events())