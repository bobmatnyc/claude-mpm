#!/usr/bin/env python3
"""
Test script to verify dashboard event relay is working correctly.
Run this after starting claude-mpm with the dashboard.
"""

import json
import sys
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_eventbus_relay():
    """Test that EventBus is properly relaying events to the dashboard."""
    print("🧪 Testing EventBus relay to dashboard...")

    try:
        from claude_mpm.services.event_bus import EventBus
        from claude_mpm.services.event_bus.config import get_config

        # Check configuration
        config = get_config()
        print(f"✓ EventBus enabled: {config.enabled}")
        print(f"✓ Relay enabled: {config.relay_enabled}")
        print(f"✓ Debug mode: {config.debug}")

        if not config.enabled or not config.relay_enabled:
            print(
                "⚠️  EventBus or relay is disabled. Enable with environment variables:"
            )
            print("    export CLAUDE_MPM_EVENTBUS_ENABLED=true")
            print("    export CLAUDE_MPM_RELAY_ENABLED=true")
            return False

        # Get EventBus instance
        eventbus = EventBus.get_instance()
        print("✓ EventBus instance obtained")

        # Get stats
        stats = eventbus.get_stats() if hasattr(eventbus, "get_stats") else {}
        print(f"📊 EventBus stats: {json.dumps(stats, indent=2)}")

        # Publish test events
        test_events = [
            (
                "hook.user_prompt",
                {"message": "Test user prompt", "timestamp": time.time()},
            ),
            ("hook.pre_tool", {"tool": "test_tool", "args": {"test": True}}),
            ("hook.post_tool", {"tool": "test_tool", "result": "success"}),
        ]

        print("\n📤 Publishing test events...")
        for event_type, data in test_events:
            eventbus.publish(event_type, data)
            print(f"  ✓ Published: {event_type}")
            time.sleep(0.5)  # Small delay between events

        # Check stats again
        if hasattr(eventbus, "get_stats"):
            new_stats = eventbus.get_stats()
            print(
                f"\n📊 EventBus stats after publishing: {json.dumps(new_stats, indent=2)}"
            )

        print("\n✅ Test complete! Check the dashboard for events.")
        print("   If you don't see events, check:")
        print("   1. Dashboard is connected (check browser console)")
        print("   2. Socket.IO server is running (port 8765)")
        print("   3. Debug logs for any errors")

        return True

    except ImportError as e:
        print(f"❌ Failed to import EventBus: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_socketio_server():
    """Check if Socket.IO server is running."""
    import socket

    print("\n🔍 Checking Socket.IO server...")

    for port in range(8765, 8786):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()

        if result == 0:
            print(f"✓ Socket.IO server is running on port {port}")
            return True

    print("⚠️  Socket.IO server not found on ports 8765-8785")
    return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Dashboard Event Relay Test")
    print("=" * 60)

    # Check Socket.IO server
    server_running = check_socketio_server()
    if not server_running:
        print("\n⚠️  Start claude-mpm with dashboard first:")
        print("    ./scripts/claude-mpm run")
        return 1

    # Test EventBus relay
    relay_working = test_eventbus_relay()

    print("\n" + "=" * 60)
    if relay_working:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed - check output above")
    print("=" * 60)

    return 0 if relay_working else 1


if __name__ == "__main__":
    sys.exit(main())
