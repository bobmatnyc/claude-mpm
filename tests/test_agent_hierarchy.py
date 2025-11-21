#!/usr/bin/env python3
"""
Test script to verify agent hierarchy display in the dashboard.

This script simulates PM and subagent events to test the hierarchical
visualization in the monitor dashboard.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def create_test_events():
    """Create test events that simulate PM delegating to subagents."""
    events = []
    base_time = datetime.now(timezone.utc).isoformat()

    # PM starts
    events.append(
        {
            "type": "hook.start",
            "hook_event_name": "Start",
            "session_id": "main_session",
            "timestamp": base_time,
            "data": {"agent_type": "pm", "hook_event_name": "Start"},
        }
    )

    # PM delegates to research agent
    events.append(
        {
            "type": "hook.pre_tool",
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "session_id": "main_session",
            "timestamp": base_time,
            "data": {
                "tool_name": "Task",
                "tool_parameters": {
                    "subagent_type": "research",
                    "task": "Analyze the codebase structure and identify key components",
                },
            },
        }
    )

    # Research agent events
    for i in range(5):
        events.append(
            {
                "type": "hook.subagent_event",
                "hook_event_name": "SubagentEvent",
                "session_id": "research_session",
                "timestamp": base_time,
                "data": {
                    "agent_type": "research",
                    "event_index": i,
                    "message": f"Research event {i + 1}",
                },
            }
        )

    # Research agent completes
    events.append(
        {
            "type": "hook.subagent_stop",
            "hook_event_name": "SubagentStop",
            "session_id": "research_session",
            "timestamp": base_time,
            "data": {"agent_type": "research", "subagent_type": "research"},
        }
    )

    # PM delegates to engineer agent
    events.append(
        {
            "type": "hook.pre_tool",
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "session_id": "main_session",
            "timestamp": base_time,
            "data": {
                "tool_name": "Task",
                "tool_parameters": {
                    "subagent_type": "engineer",
                    "task": "Implement the user authentication feature",
                },
            },
        }
    )

    # Engineer agent events
    for i in range(10):
        events.append(
            {
                "type": "hook.subagent_event",
                "hook_event_name": "SubagentEvent",
                "session_id": "engineer_session",
                "timestamp": base_time,
                "data": {
                    "agent_type": "engineer",
                    "event_index": i,
                    "message": f"Engineer event {i + 1}",
                },
            }
        )

    # Engineer still active (no stop event)

    # Some orphan security agent events (no explicit PM delegation)
    for i in range(3):
        events.append(
            {
                "type": "hook.subagent_event",
                "hook_event_name": "SubagentEvent",
                "session_id": "security_session",
                "timestamp": base_time,
                "data": {
                    "agent_type": "security",
                    "subagent_type": "security",
                    "event_index": i,
                    "message": f"Security audit event {i + 1}",
                },
            }
        )

    # Security agent completes
    events.append(
        {
            "type": "hook.subagent_stop",
            "hook_event_name": "SubagentStop",
            "session_id": "security_session",
            "timestamp": base_time,
            "data": {"agent_type": "security", "subagent_type": "security"},
        }
    )

    # PM delegates to QA agent
    events.append(
        {
            "type": "hook.pre_tool",
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "session_id": "main_session",
            "timestamp": base_time,
            "data": {
                "tool_name": "Task",
                "tool_parameters": {
                    "subagent_type": "qa",
                    "task": "Test the authentication implementation",
                },
            },
        }
    )

    # QA is pending (no events yet)

    return events


def save_test_events():
    """Save test events to a file for manual testing."""
    events = create_test_events()

    output_file = Path("/tmp/test_agent_hierarchy_events.json")
    with output_file.open("w") as f:
        json.dump(events, f, indent=2)

    print(f"Test events saved to: {output_file}")
    print(f"Total events: {len(events)}")
    print("\nEvent summary:")
    print("- PM: Main session with delegations")
    print("- Research Agent: 5 events (completed)")
    print("- Engineer Agent: 10 events (active)")
    print("- Security Agent: 3 events (implied PM, completed)")
    print("- QA Agent: 0 events (pending)")
    print("\nTo test in the dashboard:")
    print("1. Start the dashboard: claude-mpm monitor")
    print("2. Open the dashboard in your browser")
    print("3. Go to the Agents tab")
    print("4. You should see a hierarchical tree structure")


if __name__ == "__main__":
    save_test_events()
