#!/usr/bin/env python3
"""
Final comprehensive test to verify dashboard is receiving and displaying events.
"""

import asyncio
import json
import time
from datetime import datetime
import socketio
import webbrowser

# ANSI color codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

async def main():
    print(f"\n{BOLD}Dashboard Event Display Final Test{RESET}\n")
    print(f"{YELLOW}This test will:{RESET}")
    print(f"1. Connect to the SocketIO server")
    print(f"2. Send various test events")
    print(f"3. Open the dashboard in your browser")
    print(f"4. You should see the events appearing in real-time\n")
    
    # Create a SocketIO client
    sio = socketio.AsyncClient()
    
    @sio.event
    async def connect():
        print(f"{GREEN}✓ Connected to server{RESET}")
    
    @sio.event
    async def disconnect():
        print(f"{YELLOW}⚠ Disconnected from server{RESET}")
    
    try:
        # Connect to the server
        print(f"{YELLOW}Connecting to http://localhost:8765...{RESET}")
        await sio.connect('http://localhost:8765')
        await asyncio.sleep(1)
        
        # Open dashboard
        print(f"\n{BLUE}Opening dashboard in browser...{RESET}")
        webbrowser.open('http://localhost:8765')
        await asyncio.sleep(2)
        
        print(f"\n{YELLOW}Sending test events...{RESET}")
        print(f"{BLUE}Watch the dashboard - events should appear in real-time!{RESET}\n")
        
        # Send various types of events
        test_events = [
            {
                "event": "Start",
                "message": "🚀 Dashboard test session started",
                "timestamp": datetime.now().isoformat(),
                "session_id": "test_" + str(int(time.time()))
            },
            {
                "event": "SubagentStart",
                "agent": "Engineer",
                "task": "Implementing new feature",
                "priority": "high",
                "timestamp": datetime.now().isoformat()
            },
            {
                "event": "ToolCall",
                "tool": "Read",
                "args": {"file": "/src/main.py"},
                "timestamp": datetime.now().isoformat()
            },
            {
                "event": "ToolResult",
                "tool": "Read",
                "result": "File read successfully (500 lines)",
                "timestamp": datetime.now().isoformat()
            },
            {
                "event": "SubagentMessage",
                "agent": "Engineer",
                "message": "Found the issue - fixing now...",
                "timestamp": datetime.now().isoformat()
            },
            {
                "event": "ToolCall",
                "tool": "Edit",
                "args": {"file": "/src/main.py", "changes": "Applied fix"},
                "timestamp": datetime.now().isoformat()
            },
            {
                "event": "SubagentStop",
                "agent": "Engineer",
                "result": "✅ Feature implemented successfully",
                "duration": 1234,
                "timestamp": datetime.now().isoformat()
            },
            {
                "event": "SubagentStart",
                "agent": "QA",
                "task": "Running test suite",
                "timestamp": datetime.now().isoformat()
            },
            {
                "event": "TestResult",
                "status": "passed",
                "tests_run": 42,
                "tests_passed": 42,
                "timestamp": datetime.now().isoformat()
            },
            {
                "event": "SubagentStop",
                "agent": "QA",
                "result": "✅ All tests passed",
                "timestamp": datetime.now().isoformat()
            },
            {
                "event": "Stop",
                "message": "🎉 Session completed successfully",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        for i, event in enumerate(test_events, 1):
            print(f"  [{i}/{len(test_events)}] Sending: {event['event']} - {event.get('message', event.get('agent', ''))}")
            await sio.emit('claude_event', event)
            await asyncio.sleep(1)  # Delay between events for visibility
        
        print(f"\n{GREEN}✅ All test events sent!{RESET}")
        print(f"\n{BOLD}Check the dashboard:{RESET}")
        print(f"  • You should see {len(test_events)} events in the event list")
        print(f"  • Events should have different colors based on type")
        print(f"  • Timestamps should be visible")
        print(f"  • Agent names should be highlighted")
        
        print(f"\n{YELLOW}Keeping connection open for 10 seconds...{RESET}")
        print(f"Feel free to interact with the dashboard during this time.")
        await asyncio.sleep(10)
        
        await sio.disconnect()
        print(f"\n{GREEN}✅ Test completed successfully!{RESET}")
        
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())