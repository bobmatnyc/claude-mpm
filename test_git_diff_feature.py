#!/usr/bin/env python3
"""
Test script to verify git diff feature by creating a simple write operation
and checking if the git diff button appears in the dashboard.
"""

import asyncio
import json
import time
import websockets
from datetime import datetime
import os

async def send_file_write_event():
    """Send a test file write event to the websocket server"""
    uri = "ws://localhost:8080"
    
    # Create a test event that should trigger the git diff button
    test_event = {
        "type": "hook",
        "subtype": "post_tool", 
        "timestamp": datetime.now().isoformat(),
        "id": "test_write_001",
        "data": {
            "tool_name": "Write",
            "session_id": "test_session_001",
            "tool_parameters": {
                "file_path": "/Users/masa/Projects/claude-mpm/test_file.py"
            },
            "working_directory": "/Users/masa/Projects/claude-mpm",
            "duration_ms": 150,
            "success": True,
            "exit_code": 0,
            "event_type": "post_tool"
        }
    }
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to websocket server")
            
            message = json.dumps(test_event)
            await websocket.send(message)
            print(f"Sent test write event: {test_event['data']['tool_name']} - {test_event['data']['tool_parameters']['file_path']}")
            
            print("\nTest event sent successfully!")
            print("Now you can:")
            print("1. Open dashboard at http://localhost:8080")
            print("2. Go to Files tab") 
            print("3. Click on the file operation to see if 'View Git Diff' button appears")
            print("4. Try clicking the git diff button if it shows up")
            
    except ConnectionRefusedError:
        print("Could not connect to websocket server on port 8080")
        print("Make sure the server is running with: python -m claude_mpm.services.socketio_server --port 8080")
    except Exception as e:
        print(f"Error sending test event: {e}")

# Also create a test file to ensure we have something in git
def create_test_file():
    """Create a test file and commit it to git for testing"""
    test_file_path = "/Users/masa/Projects/claude-mpm/test_file.py"
    
    # Create test file
    with open(test_file_path, 'w') as f:
        f.write("""# Test file for git diff feature
print("Hello, world!")
""")
    
    # Add to git if in a git repo
    try:
        os.system(f"cd /Users/masa/Projects/claude-mpm && git add {test_file_path}")
        os.system(f"cd /Users/masa/Projects/claude-mpm && git commit -m 'Add test file for git diff feature'")
        print(f"Created and committed test file: {test_file_path}")
    except:
        print(f"Created test file: {test_file_path} (but could not commit to git)")

if __name__ == "__main__":
    print("Creating test file...")
    create_test_file()
    
    print("Sending test event...")
    asyncio.run(send_file_write_event())