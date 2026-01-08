#!/usr/bin/env python3
"""Demo script showing delegation detector hook integration.

This script simulates an AssistantResponse event and shows how
the delegation detector automatically creates autotodos.
"""

# Add src to path
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.hooks.claude_hooks.event_handlers import EventHandlers
from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
from claude_mpm.services.event_log import get_event_log


def demo_delegation_detection():
    """Demonstrate delegation pattern detection in hook handler."""
    print("=" * 60)
    print("Delegation Detector Hook Integration Demo")
    print("=" * 60)
    print()

    # Create hook handler and event handlers
    print("1. Initializing hook handler...")
    hook_handler = ClaudeHookHandler()
    event_handlers = EventHandlers(hook_handler)
    print("   ✅ Hook handler initialized")
    print()

    # Create sample assistant response with delegation anti-patterns
    print("2. Creating sample PM response with delegation anti-patterns...")
    response_text = """
I've analyzed the project structure. Here's what you need to do:

1. Make sure to add .env.local to your .gitignore file to prevent secrets from being committed.
2. You'll need to run npm install to install the dependencies.
3. Please run the tests manually with npm test to verify everything works.
4. Remember to update the README with the new setup instructions.

Let me know if you need any help!
"""

    event = {
        "response": response_text,
        "session_id": "demo-session-123",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    print(f"   Response preview: {response_text[:100]}...")
    print("   ✅ Sample response created")
    print()

    # Get event log before scanning
    event_log = get_event_log()
    initial_count = len(event_log.list_events(event_type="autotodo.delegation"))
    print(f"3. Current delegation autotodos: {initial_count}")
    print()

    # Trigger delegation scanning
    print("4. Scanning for delegation patterns...")
    event_handlers._scan_for_delegation_patterns(event)
    print("   ✅ Scanning complete")
    print()

    # Check autotodos created
    print("5. Checking autotodos created...")
    autotodos = event_log.list_events(event_type="autotodo.delegation")
    new_count = len(autotodos) - initial_count

    print(f"   Found {new_count} new delegation autotodos:")
    print()

    # Display each autotodo
    for i, todo in enumerate(autotodos[-new_count:], 1):
        payload = todo.get("payload", {})
        print(f"   Autotodo #{i}:")
        print(f"      Content: {payload.get('content', 'N/A')}")
        print(f"      Original: {payload.get('original_text', 'N/A')}")
        print(f"      Status: {todo.get('status', 'N/A')}")
        print()

    # Show event log location
    print("6. Event log location:")
    print(f"   {event_log.log_file}")
    print()

    # Show summary
    print("=" * 60)
    print("Summary:")
    print(f"  - Detected {new_count} delegation anti-patterns")
    print(f"  - Created {new_count} autotodos in event log")
    print("  - Status: pending (ready for PM to delegate)")
    print("=" * 60)
    print()

    # Cleanup demo autotodos
    print("Cleanup: Marking demo autotodos as resolved...")
    for todo in autotodos[-new_count:]:
        event_log.mark_resolved(todo["id"])
    print("✅ Demo complete!")


if __name__ == "__main__":
    demo_delegation_detection()
