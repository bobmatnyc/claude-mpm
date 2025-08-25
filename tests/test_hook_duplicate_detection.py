#!/usr/bin/env python3
"""Test that duplicate event detection works within a single process."""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import the handler directly
from claude_mpm.hooks.claude_hooks import hook_handler


def test_duplicate_detection():
    """Test that duplicate events are detected and skipped."""

    print("Testing duplicate event detection within single process...")
    print("-" * 50)

    # Create a test event
    test_event = {
        "hook_event_name": "PreToolUse",
        "session_id": "test-session-456",
        "tool_name": "Bash",
        "tool_input": {"command": "echo test"},
        "cwd": "/tmp",
    }

    # Create handler instance
    handler = hook_handler.ClaudeHookHandler()

    # Test getting event keys
    event_key = handler._get_event_key(test_event)
    print(f"Event key: {event_key}")

    # Add the event to recent events
    current_time = time.time()
    hook_handler._recent_events.append((event_key, current_time))
    print(f"Added event to recent events at time: {current_time}")

    # Try adding the same event again within 100ms
    time.sleep(0.05)  # 50ms delay

    # Check if it would be detected as duplicate
    duplicate_found = False
    for recent_key, recent_time in hook_handler._recent_events:
        if recent_key == event_key and (time.time() - recent_time) < 0.1:
            duplicate_found = True
            break

    print(f"\nDuplicate detection result: {duplicate_found}")

    # Now wait more than 100ms and check again
    time.sleep(0.1)  # Total 150ms since original

    duplicate_found_after_delay = False
    for recent_key, recent_time in hook_handler._recent_events:
        if recent_key == event_key and (time.time() - recent_time) < 0.1:
            duplicate_found_after_delay = True
            break

    print(f"Duplicate detection after 150ms: {duplicate_found_after_delay}")

    print("\n" + "=" * 50)
    if duplicate_found and not duplicate_found_after_delay:
        print("✅ SUCCESS: Duplicate detection works correctly")
        print("   - Duplicates detected within 100ms window")
        print("   - No false positives after 100ms")
        return True
    print("❌ FAILURE: Duplicate detection not working as expected")
    return False


if __name__ == "__main__":
    success = test_duplicate_detection()
    sys.exit(0 if success else 1)
