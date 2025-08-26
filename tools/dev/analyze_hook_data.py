#!/usr/bin/env python3
"""Analyze hook data to see what Claude is sending"""

import json
import time

import socketio

sio = socketio.Client()
all_events = []


@sio.event
def connect():
    print("Connected to Socket.IO server")
    # Request full history
    sio.emit("get_history", {"limit": 100})


@sio.event
def history(data):
    global all_events
    events = data.get("events", [])
    all_events = events
    print(f"\nReceived {len(events)} events from history")

    # Analyze different event types
    event_types = {}
    for event in events:
        event_type = event.get("type", "unknown")
        if event_type not in event_types:
            event_types[event_type] = []
        event_types[event_type].append(event)

    print("\nEvent type summary:")
    for event_type, type_events in sorted(event_types.items()):
        print(f"  {event_type}: {len(type_events)} events")

    # Analyze hook events in detail
    print("\n" + "=" * 60)
    print("DETAILED HOOK EVENT ANALYSIS")
    print("=" * 60)

    # User prompts
    print("\n1. USER PROMPTS:")
    user_prompts = event_types.get("hook.user_prompt", [])
    for i, event in enumerate(user_prompts[-3:]):  # Last 3
        data = event.get("data", {})
        print(f"\n  Prompt #{i+1}:")
        print(f"    Text: {data.get('prompt_text', 'N/A')[:100]}...")
        print(f"    Session: {data.get('session_id', 'N/A')}")
        print(f"    Is command: {data.get('is_command', 'N/A')}")
        print(f"    Contains code: {data.get('contains_code', 'N/A')}")

    # Pre-tool events
    print("\n2. PRE-TOOL EVENTS:")
    pre_tools = event_types.get("hook.pre_tool", [])
    tool_usage = {}
    for event in pre_tools:
        data = event.get("data", {})
        tool_name = data.get("tool_name", "unknown")
        tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

    print("  Tool usage count:")
    for tool, count in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True):
        print(f"    {tool}: {count}")

    # Look for Task tool usage (agent delegations)
    print("\n3. AGENT DELEGATIONS (Task tool):")
    task_events = [e for e in pre_tools if e.get("data", {}).get("tool_name") == "Task"]
    for i, event in enumerate(task_events[-3:]):  # Last 3
        data = event.get("data", {})
        params = data.get("tool_parameters", {})
        print(f"\n  Delegation #{i+1}:")
        print(f"    Parameters: {json.dumps(params, indent=6)[:200]}...")

    # SubagentStop events
    print("\n4. SUBAGENT STOP EVENTS:")
    subagent_stops = event_types.get("hook.subagent_stop", [])
    for i, event in enumerate(subagent_stops[-3:]):  # Last 3
        data = event.get("data", {})
        print(f"\n  SubagentStop #{i+1}:")
        print(f"    Agent type: {data.get('agent_type', 'N/A')}")
        print(f"    Agent ID: {data.get('agent_id', 'N/A')}")
        print(f"    Reason: {data.get('reason', 'N/A')}")
        print(f"    Has results: {data.get('has_results', 'N/A')}")

    # Look for prompts to agents
    print("\n5. PROMPTS TO AGENTS/PM:")
    print("  Searching for delegated prompts in Task tool parameters...")
    for event in task_events:
        data = event.get("data", {})
        params = data.get("tool_parameters", {})
        param_keys = params.get("param_keys", [])

        # Look for prompt-like fields
        for key in ["prompt", "task", "description", "message", "input"]:
            if key in param_keys:
                print(f"\n  Found '{key}' parameter in Task delegation")
                # The actual value would be in the raw_input or other fields

    sio.disconnect()


try:
    sio.connect("http://localhost:8765")
    time.sleep(1)  # Wait for data
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("RECOMMENDATIONS:")
print("=" * 60)
print("1. Task tool parameters don't seem to include the actual prompt text")
print("2. SubagentStop events lack agent identification data")
print("3. Consider adding prompt capture when Task tool is invoked")
print("4. May need to enhance hook data extraction for delegations")
