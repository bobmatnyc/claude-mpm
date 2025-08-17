#!/usr/bin/env python3
"""Test what events are being generated for file operations."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.event_storage import EventStorage


def test_file_events():
    """Check what file operation events are stored."""
    print("Testing File Operation Events")
    print("=" * 60)

    storage = EventStorage()

    # Get recent events
    events = storage.get_recent_events(limit=100)

    print(f"\nFound {len(events)} recent events")

    # Filter for file-related tools
    file_tools = [
        "read",
        "write",
        "edit",
        "multiedit",
        "grep",
        "Read",
        "Write",
        "Edit",
        "MultiEdit",
        "Grep",
    ]
    file_events = []

    for event in events:
        tool_name = event.get("tool_name", "")
        if tool_name:
            print(
                f"  Event tool_name: '{tool_name}' (type: {event.get('type')}, subtype: {event.get('subtype')})"
            )

        if any(tool.lower() == tool_name.lower() for tool in file_tools):
            file_events.append(event)

    print(f"\nFound {len(file_events)} file operation events")

    if file_events:
        print("\nSample file events:")
        for i, event in enumerate(file_events[:5]):
            print(f"\n{i+1}. Event details:")
            print(f"   Type: {event.get('type')}")
            print(f"   Subtype: {event.get('subtype')}")
            print(f"   Tool name: {event.get('tool_name')}")
            print(f"   Tool parameters: {event.get('tool_parameters', {})}")
            if "file_path" in str(event.get("tool_parameters", {})):
                params = event.get("tool_parameters", {})
                print(
                    f"   File path: {params.get('file_path', params.get('path', 'N/A'))}"
                )

    # Check case sensitivity issue
    print("\n" + "=" * 60)
    print("Tool name case analysis:")
    tool_name_cases = {}
    for event in events:
        tool_name = event.get("tool_name", "")
        if tool_name:
            if tool_name not in tool_name_cases:
                tool_name_cases[tool_name] = 0
            tool_name_cases[tool_name] += 1

    print("\nUnique tool names found (with counts):")
    for name, count in sorted(tool_name_cases.items()):
        print(f"  '{name}': {count} events")

    return len(file_events) > 0


if __name__ == "__main__":
    success = test_file_events()
    sys.exit(0 if success else 1)
