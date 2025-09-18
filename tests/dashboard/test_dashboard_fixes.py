#!/usr/bin/env python3
"""
Test script to verify dashboard fixes:
1. Activity tab text displays horizontally
2. File operations are tracked from events
3. File Tree tab uses same data as Files tab

Run this test after starting the dashboard server.
"""

import json
import random
import time
from pathlib import Path

import socketio

# Connect to the Claude MPM dashboard
sio = socketio.Client()


def emit_test_event(event_type, subtype, tool_name=None, file_path=None):
    """Emit a test event to the dashboard"""
    event = {
        "type": event_type,
        "subtype": subtype,
        "timestamp": time.time() * 1000,  # milliseconds
        "session_id": "test-session-001",
        "data": {"session_id": "test-session-001"},
    }

    if tool_name:
        event["tool_name"] = tool_name
        event["data"]["tool_name"] = tool_name

    if file_path:
        event["tool_parameters"] = {"file_path": file_path}
        event["data"]["tool_parameters"] = {"file_path": file_path}

    print(f"Emitting event: {event_type}.{subtype} - {tool_name} - {file_path}")
    sio.emit("claude_event", event)
    return event


def test_file_operations():
    """Test file operation tracking"""
    print("\n=== Testing File Operations ===")

    test_files = [
        "/Users/masa/Projects/claude-mpm/README.md",
        "/Users/masa/Projects/claude-mpm/src/main.py",
        "/Users/masa/Projects/claude-mpm/tests/test_dashboard.py",
    ]

    file_tools = ["Read", "Write", "Edit", "Grep", "MultiEdit"]

    for i, file_path in enumerate(test_files):
        tool = random.choice(file_tools)

        # Emit pre_tool event
        emit_test_event("hook", "pre_tool", tool, file_path)
        time.sleep(0.1)

        # Emit post_tool event
        post_event = emit_test_event("hook", "post_tool", tool, file_path)
        post_event["duration_ms"] = random.randint(50, 500)
        post_event["success"] = True
        sio.emit("claude_event", post_event)
        time.sleep(0.2)

    print(f"Emitted {len(test_files) * 2} file operation events")


def test_tool_operations():
    """Test general tool operations"""
    print("\n=== Testing Tool Operations ===")

    tools = ["Bash", "WebSearch", "TodoWrite", "WebFetch"]

    for tool in tools:
        params = {}
        if tool == "Bash":
            params = {"command": "ls -la"}
        elif tool == "WebSearch":
            params = {"query": "test search"}
        elif tool == "TodoWrite":
            params = {"todos": [{"content": "Test todo", "status": "pending"}]}
        elif tool == "WebFetch":
            params = {"url": "https://example.com"}

        # Emit pre_tool event
        event = emit_test_event("hook", "pre_tool", tool, None)
        event["tool_parameters"] = params
        sio.emit("claude_event", event)
        time.sleep(0.1)

        # Emit post_tool event
        post_event = emit_test_event("hook", "post_tool", tool, None)
        post_event["tool_parameters"] = params
        post_event["duration_ms"] = random.randint(100, 1000)
        post_event["success"] = True
        sio.emit("claude_event", post_event)
        time.sleep(0.2)

    print(f"Emitted {len(tools) * 2} tool operation events")


def test_agent_events():
    """Test agent tracking events"""
    print("\n=== Testing Agent Events ===")

    agents = ["PM", "Engineer", "QA", "Architect"]

    for agent in agents:
        event = {
            "type": "agent",
            "subtype": "activated",
            "timestamp": time.time() * 1000,
            "session_id": "test-session-001",
            "agent_type": agent,
            "data": {
                "agent_type": agent,
                "session_id": "test-session-001",
                "task": f"Test task for {agent}",
            },
        }

        print(f"Emitting agent event: {agent}")
        sio.emit("claude_event", event)
        time.sleep(0.1)

    print(f"Emitted {len(agents)} agent events")


@sio.event
def connect():
    print("Connected to dashboard!")
    time.sleep(1)

    # Run tests
    test_file_operations()
    test_tool_operations()
    test_agent_events()

    print("\n=== Test Complete ===")
    print("Check the dashboard to verify:")
    print("1. Activity tab text displays horizontally (not vertically)")
    print("2. Files tab shows the file operations")
    print("3. Tools tab shows the tool operations")
    print("4. Agents tab shows the agent activations")
    print("5. File Tree tab shows the same files as Files tab")

    time.sleep(2)
    sio.disconnect()


@sio.event
def connect_error(data):
    print(f"Connection error: {data}")
    print("\nMake sure the Claude MPM dashboard is running!")
    print("Start it with: claude-mpm monitor")


@sio.event
def disconnect():
    print("Disconnected from dashboard")


if __name__ == "__main__":
    print("Claude MPM Dashboard Test Script")
    print("=================================")
    print("Connecting to dashboard on localhost:5173...")

    try:
        sio.connect("http://localhost:5173")
        sio.wait()
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure the dashboard is running:")
        print("  claude-mpm monitor")
