#!/usr/bin/env python3
"""Test script for the Activity Dashboard."""

import json
import os
import sys
import threading
import time
from pathlib import Path

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_mpm.services.monitor.server import UnifiedMonitorServer


def start_server():
    """Start the monitor server in a thread."""
    server = UnifiedMonitorServer(port=5001)
    server.start()


def send_test_events():
    """Send test events to the server."""
    time.sleep(2)  # Wait for server to start

    base_url = "http://localhost:5001"

    # Check if server is running
    try:
        response = requests.get(f"{base_url}/api/status")
        print(f"Server status: {response.json()}")
    except Exception as e:
        print(f"Error checking server status: {e}")
        return

    # Send some test events
    events = [
        {
            "type": "start",
            "session_id": "test-session-1",
            "timestamp": time.time(),
            "data": {"working_directory": "/test/project", "git_branch": "main"},
        },
        {
            "type": "user_prompt",
            "session_id": "test-session-1",
            "timestamp": time.time(),
            "prompt_text": "Build a simple web application with user authentication",
        },
        {
            "type": "subagent",
            "subtype": "started",
            "session_id": "test-session-1",
            "agent_name": "PM",
            "timestamp": time.time(),
        },
        {
            "type": "hook",
            "subtype": "pre_tool",
            "session_id": "test-session-1",
            "tool_name": "TodoWrite",
            "timestamp": time.time(),
            "tool_parameters": {
                "todos": [
                    {
                        "content": "Design database schema",
                        "status": "pending",
                        "activeForm": "Designing database schema",
                    },
                    {
                        "content": "Implement user model",
                        "status": "pending",
                        "activeForm": "Implementing user model",
                    },
                    {
                        "content": "Create authentication endpoints",
                        "status": "pending",
                        "activeForm": "Creating authentication endpoints",
                    },
                ]
            },
        },
        {
            "type": "subagent",
            "subtype": "started",
            "session_id": "test-session-1",
            "agent_name": "Engineer",
            "parent_agent": "PM",
            "timestamp": time.time(),
        },
        {
            "type": "hook",
            "subtype": "pre_tool",
            "session_id": "test-session-1",
            "tool_name": "Read",
            "timestamp": time.time(),
            "tool_parameters": {"file_path": "/test/project/requirements.txt"},
        },
        {
            "type": "hook",
            "subtype": "pre_tool",
            "session_id": "test-session-1",
            "tool_name": "Write",
            "timestamp": time.time(),
            "tool_parameters": {"file_path": "/test/project/models/user.py"},
        },
        {
            "type": "hook",
            "subtype": "pre_tool",
            "session_id": "test-session-1",
            "tool_name": "Bash",
            "timestamp": time.time(),
            "tool_parameters": {"command": "python manage.py migrate"},
        },
    ]

    # Send events via API
    for event in events:
        try:
            response = requests.post(
                f"{base_url}/api/event",
                json=event,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                print(f"✓ Sent event: {event['type']} - {event.get('subtype', '')}")
            else:
                print(f"✗ Failed to send event: {response.status_code}")
        except Exception as e:
            print(f"✗ Error sending event: {e}")
        time.sleep(0.5)  # Small delay between events


def main():
    """Main function to run the test."""
    print("Starting Activity Dashboard Test")
    print("=" * 50)

    # Start server in a thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print("Server starting on http://localhost:5001")
    print("Activity Dashboard: http://localhost:5001/static/activity.html")
    print("=" * 50)

    # Send test events
    send_test_events()

    print("\n✨ Test events sent successfully!")
    print("Open http://localhost:5001/static/activity.html in your browser")
    print("You should see a hierarchical tree with:")
    print("  - PM Session")
    print("    - User instruction")
    print("    - TodoWrite with 3 tasks")
    print("    - PM agent")
    print("    - Engineer agent with tools (Read, Write, Bash)")
    print("\nPress Ctrl+C to stop the server")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
