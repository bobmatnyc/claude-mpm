#!/usr/bin/env python3
"""
Verify code event consistency across the system.

This script checks that event names are consistent between:
1. Event emitter definitions
2. Handler emissions
3. Frontend listeners
"""

import re
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).parent.parent

    # Expected event names
    expected_events = {
        "code:directory:discovered",
        "code:file:discovered",
        "code:file:analyzed",
        "code:analysis:error",
    }

    print("=== Code Event Consistency Check ===\n")

    # 1. Check event definitions in code_tree_events.py
    print("1. Checking event definitions...")
    events_file = project_root / "src/claude_mpm/tools/code_tree_events.py"
    with open(events_file) as f:
        content = f.read()

    defined_events = set()
    for line in content.split("\n"):
        if "EVENT_" in line and "=" in line and '"code:' in line:
            match = re.search(r'"(code:[^"]+)"', line)
            if match:
                defined_events.add(match.group(1))

    print(f"   Found {len(defined_events)} defined events:")
    for event in sorted(defined_events):
        print(f"     - {event}")

    # 2. Check handler emissions in code_analysis.py
    print("\n2. Checking handler emissions...")
    handler_file = (
        project_root / "src/claude_mpm/services/socketio/handlers/code_analysis.py"
    )
    with open(handler_file) as f:
        content = f.read()

    emitted_events = set()
    # Look for self.server.core.sio.emit calls
    pattern = r'self\.server\.core\.sio\.emit\(\s*"([^"]+)"'
    for match in re.finditer(pattern, content):
        event_name = match.group(1)
        if event_name.startswith("code:"):
            emitted_events.add(event_name)

    # Also look for await self.server.sio.emit calls (older pattern)
    pattern2 = r'await self\.server\.sio\.emit\(\s*"([^"]+)"'
    for match in re.finditer(pattern2, content):
        event_name = match.group(1)
        if event_name.startswith("code:"):
            emitted_events.add(event_name)

    print(f"   Found {len(emitted_events)} emitted event types:")
    for event in sorted(emitted_events):
        print(f"     - {event}")

    # 3. Check frontend listeners in code-tree.js
    print("\n3. Checking frontend listeners...")
    frontend_file = (
        project_root / "src/claude_mpm/dashboard/static/js/components/code-tree.js"
    )
    with open(frontend_file) as f:
        content = f.read()

    listened_events = set()
    # Look for socket.on calls
    pattern = r"socket\.on\('([^']+)'|socket\.on\(\"([^\"]+)\""
    for match in re.finditer(pattern, content):
        event_name = match.group(1) or match.group(2)
        if event_name and event_name.startswith("code:"):
            listened_events.add(event_name)

    print(f"   Found {len(listened_events)} listened events:")
    for event in sorted(listened_events):
        print(f"     - {event}")

    # 4. Check for inconsistencies
    print("\n=== Consistency Analysis ===\n")

    # Check for 'code:discovery:error' (incorrect)
    print("Checking for incorrect 'code:discovery:error' usage...")
    incorrect_found = False

    for file_path in [events_file, handler_file, frontend_file]:
        with open(file_path) as f:
            if "code:discovery:error" in f.read():
                print(f"   ❌ Found 'code:discovery:error' in {file_path.name}")
                incorrect_found = True

    if not incorrect_found:
        print("   ✅ No incorrect 'code:discovery:error' found")

    # Check that all expected events are present
    print("\nChecking expected events are used correctly...")
    all_events = defined_events | emitted_events | listened_events

    for event in expected_events:
        if event in all_events:
            print(f"   ✅ {event}")
        else:
            print(f"   ❌ {event} - MISSING")

    # Check for any unexpected code: events
    print("\nChecking for unexpected code: events...")
    unexpected = all_events - expected_events
    # Filter out non-error events
    unexpected = {
        e
        for e in unexpected
        if not any(
            x in e
            for x in [
                "analysis:queued",
                "analysis:accepted",
                "analysis:cancelled",
                "analysis:start",
                "analysis:complete",
                "analysis:progress",
                "analysis:status",
                "node:found",
                "analyze:",
                "discover:",
            ]
        )
    }

    if unexpected:
        print("   Found unexpected events:")
        for event in sorted(unexpected):
            print(f"     - {event}")
    else:
        print("   ✅ No unexpected error events found")

    # Final summary
    print("\n=== Summary ===")
    if not incorrect_found and "code:analysis:error" in all_events:
        print("✅ Event consistency check PASSED")
        print("   All error events correctly use 'code:analysis:error'")
        return 0
    print("❌ Event consistency check FAILED")
    if incorrect_found:
        print("   Found usage of incorrect 'code:discovery:error'")
    if "code:analysis:error" not in all_events:
        print("   'code:analysis:error' not properly configured")
    return 1


if __name__ == "__main__":
    sys.exit(main())
