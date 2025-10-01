#!/usr/bin/env python3
"""
Test script for implied PM detection functionality.

Tests the orphan agent detection and implied PM grouping logic.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def create_test_events():
    """Create test events with various scenarios for implied PM detection."""
    base_time = datetime.now(timezone.utc)
    events = []

    # Scenario 1: Normal PM delegation (should NOT create implied PM)
    events.append(
        {
            "timestamp": (base_time).isoformat(),
            "session_id": "main_session_1",
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "tool_parameters": {
                "subagent_type": "engineer",
                "task": "Implement feature X",
            },
        }
    )

    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=1)).isoformat(),
            "session_id": "subagent_session_1",
            "hook_event_name": "SubagentStart",
            "agent_type": "engineer",
            "data": {"agent_type": "engineer"},
        }
    )

    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=5)).isoformat(),
            "session_id": "subagent_session_1",
            "hook_event_name": "SubagentStop",
            "agent_type": "engineer",
        }
    )

    # Scenario 2: Orphan agent - SubagentStart without PM Task (should create implied PM)
    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=10)).isoformat(),
            "session_id": "orphan_session_1",
            "hook_event_name": "SubagentStart",
            "agent_type": "research",
            "data": {"agent_type": "research"},
        }
    )

    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=12)).isoformat(),
            "session_id": "orphan_session_1",
            "hook_event_name": "ToolUse",
            "tool_name": "WebSearch",
            "agent_type": "research",
        }
    )

    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=15)).isoformat(),
            "session_id": "orphan_session_1",
            "hook_event_name": "SubagentStop",
            "agent_type": "research",
        }
    )

    # Scenario 3: Multiple orphan agents close in time (should group in same implied PM)
    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=20)).isoformat(),
            "session_id": "orphan_session_2",
            "hook_event_name": "SubagentStart",
            "agent_type": "qa",
            "data": {"agent_type": "qa"},
        }
    )

    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=21)).isoformat(),
            "session_id": "orphan_session_2",
            "hook_event_name": "ToolUse",
            "tool_name": "Test",
            "agent_type": "qa",
        }
    )

    # Another orphan within 5 seconds (should be grouped)
    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=23)).isoformat(),
            "session_id": "orphan_session_3",
            "hook_event_name": "SubagentStart",
            "agent_type": "documentation",
            "data": {"agent_type": "documentation"},
        }
    )

    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=24)).isoformat(),
            "session_id": "orphan_session_3",
            "hook_event_name": "ToolUse",
            "tool_name": "Write",
            "agent_type": "documentation",
        }
    )

    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=25)).isoformat(),
            "session_id": "orphan_session_2",
            "hook_event_name": "SubagentStop",
            "agent_type": "qa",
        }
    )

    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=27)).isoformat(),
            "session_id": "orphan_session_3",
            "hook_event_name": "SubagentStop",
            "agent_type": "documentation",
        }
    )

    # Scenario 4: Orphan agent far apart in time (should create separate implied PM)
    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=40)).isoformat(),
            "session_id": "orphan_session_4",
            "hook_event_name": "SubagentStart",
            "agent_type": "security",
            "data": {"agent_type": "security"},
        }
    )

    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=42)).isoformat(),
            "session_id": "orphan_session_4",
            "hook_event_name": "SubagentStop",
            "agent_type": "security",
        }
    )

    # Scenario 5: Legacy events without clear agent marking
    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=50)).isoformat(),
            "session_id": "legacy_session",
            "type": "hook.subagent_start",
            "data": {"agent_id": "ops"},
        }
    )

    events.append(
        {
            "timestamp": (base_time + timedelta(seconds=52)).isoformat(),
            "session_id": "legacy_session",
            "type": "hook.subagent_stop",
            "data": {"agent_id": "ops"},
        }
    )

    return events


def analyze_results(events):
    """Analyze the test events to show expected results."""
    print("\n" + "=" * 60)
    print("EXPECTED IMPLIED PM DETECTION RESULTS")
    print("=" * 60)

    print("\n✅ Normal PM Delegation (NO implied PM):")
    print("   - Engineer Agent: Delegated by PM Task tool")

    print("\n🔍 Implied PM #1 (Single orphan):")
    print("   - Research Agent: Started without PM Task delegation")
    print("   - Time window: seconds 10-15")

    print("\n🔍 Implied PM #2 (Grouped orphans):")
    print("   - QA Agent: Started at second 20")
    print("   - Documentation Agent: Started at second 23 (within 5s)")
    print("   - Should be grouped together in same implied PM")

    print("\n🔍 Implied PM #3 (Separate orphan):")
    print("   - Security Agent: Started at second 40")
    print("   - Too far from previous orphans (>5s gap)")

    print("\n🔍 Implied PM #4 (Legacy format):")
    print("   - Ops Agent: Legacy event format")
    print("   - Should be detected as orphan")


def save_test_events(events, output_file="test_implied_pm_events.json"):
    """Save test events to a JSON file."""
    output_path = Path(__file__).parent / output_file
    with output_path.open("w") as f:
        json.dump(events, f, indent=2)
    print(f"\n✅ Test events saved to: {output_path}")
    print(f"   Total events: {len(events)}")
    return output_path


def print_instructions():
    """Print instructions for testing the feature."""
    print("\n" + "=" * 60)
    print("TESTING INSTRUCTIONS")
    print("=" * 60)
    print("\n1. Start the dashboard server:")
    print("   claude-mpm dashboard")
    print("\n2. Open the dashboard in your browser:")
    print("   http://localhost:8765")
    print("\n3. Load the test events:")
    print("   - Click 'Load File' button")
    print("   - Select: scripts/test_implied_pm_events.json")
    print("\n4. Navigate to the 'Agents' tab")
    print("\n5. Verify the hierarchy shows:")
    print("   - PM (Main Session) with Engineer Agent")
    print("   - PM (Implied #1) with Research Agent")
    print("   - PM (Implied #2) with QA and Documentation Agents")
    print("   - PM (Implied #3) with Security Agent")
    print("   - PM (Implied #4) with Ops Agent")
    print("\n6. Visual verification:")
    print("   - Implied PMs should have dashed borders")
    print("   - Implied PMs should use 🔍 icon instead of 👔")
    print("   - Status should show 'inferred' in purple")
    print("   - Hover over implied nodes to see tooltips")


def main():
    """Main test function."""
    print("🚀 Implied PM Detection Test Script")
    print("=" * 60)

    # Create test events
    events = create_test_events()

    # Save to file
    save_test_events(events)

    # Analyze expected results
    analyze_results(events)

    # Print testing instructions
    print_instructions()

    print("\n✨ Test data generation complete!")
    print("   Follow the instructions above to test the feature.")


if __name__ == "__main__":
    main()
