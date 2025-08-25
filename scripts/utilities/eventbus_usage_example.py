#!/usr/bin/env python3
"""Example usage of the EventBus architecture in claude-mpm.

This script demonstrates various ways to use the EventBus for
decoupled event handling in your application.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.event_bus import EventBus


def example_1_basic_publishing():
    """Example 1: Basic event publishing from synchronous code."""
    print("\n📘 Example 1: Basic Event Publishing")
    print("-" * 40)

    # Get the EventBus singleton
    event_bus = EventBus.get_instance()

    # Publish a simple event
    event_bus.publish(
        "app.user_action",
        {
            "action": "clicked_button",
            "button_id": "submit",
            "timestamp": datetime.now().isoformat(),
        },
    )

    # Publish a hook event (will be picked up by Socket.IO relay)
    event_bus.publish(
        "hook.pre_tool",
        {
            "tool_name": "Read",
            "file_path": "/example/file.py",
            "sessionId": "example-123",
        },
    )

    print("✅ Events published to EventBus")


def example_2_event_consumers():
    """Example 2: Registering event consumers."""
    print("\n📘 Example 2: Event Consumers")
    print("-" * 40)

    event_bus = EventBus.get_instance()

    # Define event handlers
    def log_user_action(data):
        print(f"  LOG: User performed action: {data.get('action')}")

    def track_analytics(data):
        print(f"  ANALYTICS: Tracking {data.get('action')} event")

    def send_notification(data):
        if data.get("action") == "important_action":
            print("  NOTIFICATION: Alerting user about important action")

    # Register multiple consumers for the same event
    event_bus.on("app.user_action", log_user_action)
    event_bus.on("app.user_action", track_analytics)
    event_bus.on("app.user_action", send_notification)

    # Publish events
    event_bus.publish("app.user_action", {"action": "login", "user": "alice"})
    event_bus.publish("app.user_action", {"action": "important_action", "user": "bob"})

    print("✅ Multiple consumers processed events")


async def example_3_async_handlers():
    """Example 3: Async event handlers."""
    print("\n📘 Example 3: Async Event Handlers")
    print("-" * 40)

    event_bus = EventBus.get_instance()

    # Define async handler
    async def async_processor(data):
        print("  ASYNC: Starting processing...")
        await asyncio.sleep(0.5)  # Simulate async work
        print(f"  ASYNC: Processed {data.get('item_count')} items")

    # Register async handler
    event_bus.on("app.process_batch", async_processor)

    # Publish event (works from sync context)
    event_bus.publish("app.process_batch", {"item_count": 100})

    # Wait for async processing
    await asyncio.sleep(1)

    print("✅ Async handler processed event")


def example_4_event_filtering():
    """Example 4: Event filtering with patterns."""
    print("\n📘 Example 4: Event Filtering")
    print("-" * 40)

    event_bus = EventBus.get_instance()

    # Clear any existing filters
    event_bus.clear_filters()

    # Only allow hook events and critical system events
    event_bus.add_filter("hook.*")
    event_bus.add_filter("system.critical.*")

    # These will be processed
    success1 = event_bus.publish("hook.pre_tool", {"tool": "Read"})
    success2 = event_bus.publish("system.critical.error", {"error": "Database down"})

    # These will be filtered out
    success3 = event_bus.publish("app.user_action", {"action": "click"})
    success4 = event_bus.publish("system.info", {"message": "All good"})

    print(f"  hook.pre_tool: {'✅ Allowed' if success1 else '❌ Filtered'}")
    print(f"  system.critical.error: {'✅ Allowed' if success2 else '❌ Filtered'}")
    print(f"  app.user_action: {'✅ Allowed' if success3 else '❌ Filtered'}")
    print(f"  system.info: {'✅ Allowed' if success4 else '❌ Filtered'}")

    # Clear filters for other examples
    event_bus.clear_filters()

    print("✅ Event filtering demonstrated")


def example_5_wildcard_subscriptions():
    """Example 5: Wildcard event subscriptions."""
    print("\n📘 Example 5: Wildcard Subscriptions")
    print("-" * 40)

    event_bus = EventBus.get_instance()

    # Handler for all hook events
    def hook_monitor(event_type, data):
        print(f"  HOOK MONITOR: Received {event_type}")

    # Handler for all system events
    def system_monitor(event_type, data):
        print(f"  SYSTEM MONITOR: Received {event_type}")

    # Subscribe to patterns
    event_bus.on("hook.*", hook_monitor)
    event_bus.on("system.*", system_monitor)

    # Publish various events
    event_bus.publish("hook.pre_tool", {"tool": "Read"})
    event_bus.publish("hook.post_tool", {"tool": "Write"})
    event_bus.publish("system.startup", {"time": "now"})
    event_bus.publish("system.shutdown", {"reason": "maintenance"})
    event_bus.publish("app.other", {"data": "ignored"})  # Won't match

    print("✅ Wildcard subscriptions working")


def example_6_one_time_handlers():
    """Example 6: One-time event handlers."""
    print("\n📘 Example 6: One-Time Handlers")
    print("-" * 40)

    event_bus = EventBus.get_instance()

    # Handler that only runs once
    def initialization_handler(data):
        print(f"  INIT: System initialized with config: {data.get('config')}")

    # Register one-time handler
    event_bus.once("app.initialized", initialization_handler)

    # First event - handler will run
    event_bus.publish("app.initialized", {"config": "production"})

    # Second event - handler won't run (already removed)
    event_bus.publish("app.initialized", {"config": "development"})

    print("✅ One-time handler executed only once")


def example_7_event_stats():
    """Example 7: Monitoring EventBus statistics."""
    print("\n📘 Example 7: EventBus Statistics")
    print("-" * 40)

    event_bus = EventBus.get_instance()

    # Reset stats for clean example
    event_bus.reset_stats()

    # Generate some events
    for i in range(10):
        event_bus.publish("test.event", {"index": i})

    # Add filter and try more events
    event_bus.add_filter("allowed.*")
    event_bus.publish("allowed.event", {"data": "yes"})
    event_bus.publish("blocked.event", {"data": "no"})

    # Get statistics
    stats = event_bus.get_stats()

    print(f"  Events published: {stats['events_published']}")
    print(f"  Events filtered: {stats['events_filtered']}")
    print(f"  Events failed: {stats['events_failed']}")
    print(f"  Filters active: {stats['filters_active']}")

    # Get recent event history
    recent = event_bus.get_recent_events(3)
    print(f"\n  Recent events ({len(recent)}):")
    for event in recent:
        print(f"    - {event['type']} at {event['timestamp']}")

    # Clear filters
    event_bus.clear_filters()

    print("✅ Statistics and history available")


def example_8_error_handling():
    """Example 8: Error handling in consumers."""
    print("\n📘 Example 8: Error Handling")
    print("-" * 40)

    event_bus = EventBus.get_instance()

    results = {"good": 0, "bad": 0}

    def good_handler(data):
        results["good"] += 1
        print(f"  GOOD: Processing event #{data.get('id')}")

    def bad_handler(data):
        results["bad"] += 1
        print(f"  BAD: Attempting to process event #{data.get('id')}")
        if data.get("id") == 2:
            raise ValueError("Simulated error on event #2")

    # Register both handlers
    event_bus.on("app.test_error", good_handler)
    event_bus.on("app.test_error", bad_handler)

    # Publish events
    for i in range(1, 4):
        event_bus.publish("app.test_error", {"id": i})

    print(f"\n  Good handler processed: {results['good']} events")
    print(f"  Bad handler processed: {results['bad']} events (1 with error)")
    print("✅ Errors in one consumer don't affect others")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("EventBus Usage Examples")
    print("=" * 60)

    # Run synchronous examples
    example_1_basic_publishing()
    example_2_event_consumers()

    # Run async example
    await example_3_async_handlers()

    # Continue with sync examples
    example_4_event_filtering()
    example_5_wildcard_subscriptions()
    example_6_one_time_handlers()
    example_7_event_stats()
    example_8_error_handling()

    print("\n" + "=" * 60)
    print("🎉 All examples completed successfully!")
    print("\nKey takeaways:")
    print("  • EventBus provides decoupled event handling")
    print("  • Supports both sync and async handlers")
    print("  • Multiple consumers can handle the same event")
    print("  • Failures in one consumer don't affect others")
    print("  • Built-in filtering, statistics, and monitoring")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
