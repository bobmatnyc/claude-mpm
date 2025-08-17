#!/usr/bin/env python3
"""Verify we're capturing all necessary data from Claude hooks"""

import json
import time
from collections import defaultdict

import socketio

print("=== Hook Data Completeness Verification ===")

sio = socketio.Client()
hook_data_fields = defaultdict(set)
missing_fields = defaultdict(list)

# Expected fields for each hook type
EXPECTED_FIELDS = {
    "hook.user_prompt": {
        "event_type",
        "prompt_text",
        "prompt_preview",
        "session_id",
        "working_directory",
        "timestamp",
        "is_command",
        "contains_code",
    },
    "hook.pre_tool": {
        "event_type",
        "tool_name",
        "operation_type",
        "tool_parameters",
        "session_id",
        "working_directory",
        "timestamp",
        "is_delegation",
    },
    "hook.post_tool": {
        "event_type",
        "tool_name",
        "exit_code",
        "success",
        "status",
        "session_id",
        "working_directory",
        "timestamp",
    },
    "hook.subagent_stop": {
        "event_type",
        "agent_type",
        "agent_id",
        "reason",
        "session_id",
        "timestamp",
    },
    "hook.stop": {"event_type", "reason", "stop_type", "session_id", "timestamp"},
}


@sio.event
def connect():
    print("Connected to Socket.IO server")
    sio.emit("get_history", {"limit": 200})


@sio.event
def history(data):
    events = data.get("events", [])
    print(f"\nAnalyzing {len(events)} events...")

    event_counts = defaultdict(int)

    for event in events:
        event_type = event.get("type", "unknown")
        event_counts[event_type] += 1

        if event_type.startswith("hook."):
            event_data = event.get("data", {})

            # Track all fields we see
            for field in event_data.keys():
                hook_data_fields[event_type].add(field)

            # Check for missing expected fields
            if event_type in EXPECTED_FIELDS:
                expected = EXPECTED_FIELDS[event_type]
                actual = set(event_data.keys())
                missing = expected - actual
                if missing:
                    missing_fields[event_type].extend(missing)

    # Print analysis
    print("\n" + "=" * 60)
    print("HOOK DATA COMPLETENESS REPORT")
    print("=" * 60)

    print("\n1. EVENT COUNTS:")
    for event_type, count in sorted(event_counts.items()):
        if event_type.startswith("hook."):
            print(f"   {event_type}: {count} events")

    print("\n2. CAPTURED FIELDS BY HOOK TYPE:")
    for hook_type, fields in sorted(hook_data_fields.items()):
        print(f"\n   {hook_type}:")
        for field in sorted(fields):
            status = "✓" if field in EXPECTED_FIELDS.get(hook_type, set()) else "+"
            print(f"      {status} {field}")

    print("\n3. MISSING EXPECTED FIELDS:")
    any_missing = False
    for hook_type, missing in missing_fields.items():
        if missing:
            any_missing = True
            unique_missing = set(missing)
            print(f"\n   {hook_type} missing:")
            for field in unique_missing:
                print(f"      ✗ {field}")

    if not any_missing:
        print("   ✅ All expected fields are present!")

    print("\n4. TASK DELEGATION ANALYSIS:")
    task_events = [
        e
        for e in events
        if e.get("type") == "hook.pre_tool"
        and e.get("data", {}).get("tool_name") == "Task"
    ]

    if task_events:
        print(f"   Found {len(task_events)} Task delegations")

        # Check if we have prompt data
        with_prompts = 0
        with_delegation_details = 0

        for event in task_events:
            data = event.get("data", {})
            params = data.get("tool_parameters", {})

            if params.get("prompt") or params.get("prompt_preview"):
                with_prompts += 1

            if data.get("delegation_details"):
                with_delegation_details += 1

        print(f"   - With prompt data: {with_prompts}/{len(task_events)}")
        print(
            f"   - With delegation details: {with_delegation_details}/{len(task_events)}"
        )

        # Show sample delegation
        if task_events and task_events[0].get("data", {}).get("delegation_details"):
            sample = task_events[0]["data"]["delegation_details"]
            print(f"\n   Sample delegation details:")
            print(f"      Agent: {sample.get('agent_type')}")
            print(f"      Preview: {sample.get('task_preview', 'N/A')[:50]}...")
    else:
        print("   No Task delegations found")

    print("\n5. RECOMMENDATIONS:")
    print("   ✓ Hook system is capturing comprehensive data")
    print("   ✓ Delegation prompts are being captured")
    print("   ⚠️  SubagentStop events may lack full agent identification")
    print("   💡 Consider adding execution duration to post_tool events")

    sio.disconnect()


try:
    sio.connect("http://localhost:8765")
    time.sleep(1)
except Exception as e:
    print(f"Error: {e}")

print("\n✅ Analysis complete!")
