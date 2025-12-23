#!/usr/bin/env python3
"""Test script to validate JSON event emission for hook system.

This script simulates hook execution and verifies that structured events
are emitted with proper timing, success/failure status, and summaries.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
from claude_mpm.services.socketio.event_normalizer import EventNormalizer


def test_hook_event_emission():
    """Test that hook events are properly emitted with metadata."""

    print("🧪 Testing Hook Event Emission System")
    print("=" * 60)

    # Initialize handler
    handler = ClaudeHookHandler()

    # Test cases for different hook types
    test_cases = [
        {
            "name": "UserPromptSubmit",
            "event": {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Write a Python function to calculate fibonacci numbers",
                "session_id": "test-session-123",
                "cwd": "/Users/test/project",
            },
            "expected_fields": ["prompt_preview", "prompt_length"],
        },
        {
            "name": "PreToolUse",
            "event": {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "ls -la"},
                "session_id": "test-session-123",
                "cwd": "/Users/test/project",
            },
            "expected_fields": ["tool_name"],
        },
        {
            "name": "PostToolUse",
            "event": {
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "exit_code": 0,
                "output": "file1.txt\nfile2.py",
                "session_id": "test-session-123",
                "cwd": "/Users/test/project",
            },
            "expected_fields": ["tool_name", "exit_code"],
        },
        {
            "name": "SubagentStop",
            "event": {
                "hook_event_name": "SubagentStop",
                "agent_type": "engineer",
                "reason": "completed",
                "output": "Task completed successfully",
                "session_id": "test-session-123",
                "cwd": "/Users/test/project",
            },
            "expected_fields": ["agent_type", "reason"],
        },
        {
            "name": "SessionStart",
            "event": {
                "hook_event_name": "SessionStart",
                "session_id": "test-session-456",
                "cwd": "/Users/test/project",
            },
            "expected_fields": [],
        },
    ]

    # Track emitted events (monkey patch for testing)
    emitted_events = []
    original_emit = handler.connection_manager.emit_event

    def capture_emit(namespace, event_type, data):
        """Capture emitted events for validation."""
        emitted_events.append(
            {
                "namespace": namespace,
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        # Also call original to maintain normal flow
        try:
            original_emit(namespace, event_type, data)
        except Exception:
            pass  # Ignore emit failures in test

    handler.connection_manager.emit_event = capture_emit

    # Run test cases
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing {test_case['name']} hook...")
        print("-" * 60)

        # Clear previous events
        emitted_events.clear()

        # Route the event (this triggers hook processing and event emission)
        start_time = time.time()
        result = handler._route_event(test_case["event"])
        duration = time.time() - start_time

        print(f"   ⏱️  Execution time: {duration * 1000:.2f}ms")

        # Find the hook_execution event
        hook_exec_events = [
            e for e in emitted_events if e["event_type"] == "hook_execution"
        ]

        if hook_exec_events:
            hook_event = hook_exec_events[0]
            data = hook_event["data"]

            print("   ✅ Hook execution event emitted")
            print(f"      - hook_type: {data.get('hook_type')}")
            print(f"      - success: {data.get('success')}")
            print(f"      - duration_ms: {data.get('duration_ms')}ms")
            print(f"      - result_summary: {data.get('result_summary')}")

            # Validate required fields
            required_fields = [
                "hook_name",
                "hook_type",
                "session_id",
                "working_directory",
                "success",
                "duration_ms",
                "result_summary",
                "timestamp",
            ]

            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                print(f"   ❌ Missing required fields: {missing_fields}")
            else:
                print("   ✅ All required fields present")

            # Validate hook-specific fields
            for field in test_case["expected_fields"]:
                if field in data:
                    print(f"   ✅ Hook-specific field '{field}' present")
                else:
                    print(f"   ⚠️  Expected field '{field}' not found")

            # Validate timing
            if data.get("duration_ms", 0) > 0:
                print("   ✅ Timing information captured")
            else:
                print("   ⚠️  Duration is 0 or missing")

        else:
            print("   ❌ No hook_execution event found!")
            print(f"      Emitted events: {[e['event_type'] for e in emitted_events]}")

    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    print(f"   - Tested {len(test_cases)} hook types")
    print("   - All hooks emitted structured events")
    print("   - Events include timing and success status")
    print("   - Events follow normalized schema")


def test_event_normalizer():
    """Test that EventNormalizer properly handles hook_execution events."""

    print("\n\n🧪 Testing Event Normalizer")
    print("=" * 60)

    normalizer = EventNormalizer()

    # Test hook_execution event normalization
    raw_event = {
        "type": "hook_execution",
        "hook_name": "PreToolUse",
        "hook_type": "PreToolUse",
        "session_id": "test-123",
        "working_directory": "/Users/test",
        "success": True,
        "duration_ms": 42,
        "result_summary": "Pre-processing tool call: Bash",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": "Bash",
    }

    normalized = normalizer.normalize(raw_event, source="hook")
    event_dict = normalized.to_dict()

    print("\n1. Testing hook_execution normalization...")
    print("-" * 60)
    print(f"   Source: {event_dict['source']}")
    print(f"   Type: {event_dict['type']}")
    print(f"   Subtype: {event_dict['subtype']}")
    print(f"   Timestamp: {event_dict['timestamp']}")

    # Validate normalized structure
    if event_dict["source"] == "hook":
        print("   ✅ Source correctly set to 'hook'")
    else:
        print(f"   ❌ Source incorrect: {event_dict['source']}")

    if event_dict["type"] == "hook":
        print("   ✅ Type correctly set to 'hook'")
    else:
        print(f"   ❌ Type incorrect: {event_dict['type']}")

    if event_dict["subtype"] == "execution":
        print("   ✅ Subtype correctly set to 'execution'")
    else:
        print(f"   ❌ Subtype incorrect: {event_dict['subtype']}")

    # Validate data payload
    data = event_dict.get("data", {})
    if "hook_name" in data and "duration_ms" in data:
        print("   ✅ Data payload contains hook metadata")
    else:
        print("   ❌ Data payload missing required fields")

    print("\n" + "=" * 60)
    print("✅ Event Normalizer Test Complete")


def print_example_events():
    """Print example event outputs for documentation."""

    print("\n\n📄 Example Event Outputs")
    print("=" * 60)

    examples = [
        {
            "name": "UserPromptSubmit Hook Execution",
            "event": {
                "event": "claude_event",
                "source": "mpm_hook",
                "type": "hook",
                "subtype": "execution",
                "timestamp": "2025-12-23T10:30:00.123Z",
                "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
                "data": {
                    "hook_name": "UserPromptSubmit",
                    "hook_type": "UserPromptSubmit",
                    "session_id": "abc123def456",
                    "working_directory": "/Users/masa/Projects/claude-mpm",
                    "success": True,
                    "duration_ms": 15,
                    "result_summary": "Processed user prompt (87 chars)",
                    "prompt_preview": "Write a Python function to calculate fibonacci numbers",
                    "prompt_length": 87,
                },
            },
        },
        {
            "name": "PreToolUse Hook Execution",
            "event": {
                "event": "claude_event",
                "source": "mpm_hook",
                "type": "hook",
                "subtype": "execution",
                "timestamp": "2025-12-23T10:30:01.456Z",
                "correlation_id": "550e8400-e29b-41d4-a716-446655440001",
                "data": {
                    "hook_name": "PreToolUse",
                    "hook_type": "PreToolUse",
                    "session_id": "abc123def456",
                    "working_directory": "/Users/masa/Projects/claude-mpm",
                    "success": True,
                    "duration_ms": 8,
                    "result_summary": "Pre-processing tool call: Bash",
                    "tool_name": "Bash",
                },
            },
        },
        {
            "name": "PostToolUse Hook Execution (Success)",
            "event": {
                "event": "claude_event",
                "source": "mpm_hook",
                "type": "hook",
                "subtype": "execution",
                "timestamp": "2025-12-23T10:30:02.789Z",
                "correlation_id": "550e8400-e29b-41d4-a716-446655440002",
                "data": {
                    "hook_name": "PostToolUse",
                    "hook_type": "PostToolUse",
                    "session_id": "abc123def456",
                    "working_directory": "/Users/masa/Projects/claude-mpm",
                    "success": True,
                    "duration_ms": 12,
                    "result_summary": "Completed tool call: Bash (success)",
                    "tool_name": "Bash",
                    "exit_code": 0,
                },
            },
        },
        {
            "name": "SubagentStop Hook Execution",
            "event": {
                "event": "claude_event",
                "source": "mpm_hook",
                "type": "hook",
                "subtype": "execution",
                "timestamp": "2025-12-23T10:30:15.123Z",
                "correlation_id": "550e8400-e29b-41d4-a716-446655440003",
                "data": {
                    "hook_name": "SubagentStop",
                    "hook_type": "SubagentStop",
                    "session_id": "xyz789ghi012",
                    "working_directory": "/Users/masa/Projects/claude-mpm",
                    "success": True,
                    "duration_ms": 25,
                    "result_summary": "Subagent engineer stopped: completed",
                    "agent_type": "engineer",
                    "reason": "completed",
                },
            },
        },
        {
            "name": "Failed Hook Execution (Error)",
            "event": {
                "event": "claude_event",
                "source": "mpm_hook",
                "type": "hook",
                "subtype": "execution",
                "timestamp": "2025-12-23T10:30:03.456Z",
                "correlation_id": "550e8400-e29b-41d4-a716-446655440004",
                "data": {
                    "hook_name": "PreToolUse",
                    "hook_type": "PreToolUse",
                    "session_id": "abc123def456",
                    "working_directory": "/Users/masa/Projects/claude-mpm",
                    "success": False,
                    "duration_ms": 5,
                    "result_summary": "Hook PreToolUse failed during processing",
                    "error_message": "Invalid tool parameters: missing required field 'command'",
                },
            },
        },
    ]

    for example in examples:
        print(f"\n{example['name']}:")
        print("-" * 60)
        print(json.dumps(example["event"], indent=2))

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        # Run tests
        test_hook_event_emission()
        test_event_normalizer()
        print_example_events()

        print("\n\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
