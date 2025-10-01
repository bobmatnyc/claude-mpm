#!/usr/bin/env python3
"""
Event Generator for Testing Socket.IO Event Flow
===============================================

This script generates test events to verify the event flow and test for duplicates.
It can generate events via both EventBus and HTTP POST to test different pathways.

Usage:
    python scripts/test_event_generator.py [--method eventbus|http|both] [--count N]
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests


def generate_test_event(event_id: int, method: str) -> dict:
    """Generate a test event with unique data."""
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "type": "hook",
        "subtype": "test_event",
        "timestamp": timestamp,
        "session_id": f"test_session_{event_id // 5}",  # Group events by session
        "source": "test_generator",
        "method": method,
        "data": {
            "event_id": event_id,
            "test_data": f"Test event {event_id} via {method}",
            "generated_at": timestamp,
        },
        "metadata": {"generator": "test_event_generator.py", "method": method},
    }


def send_via_http(event: dict, host: str = "localhost", port: int = 8765) -> bool:
    """Send event via HTTP POST to the monitor daemon."""
    try:
        url = f"http://{host}:{port}/api/events"

        # Format for HTTP API
        payload = {"namespace": "hook", "event": "test_event", "data": event}

        response = requests.post(
            url, json=payload, headers={"Content-Type": "application/json"}, timeout=5
        )

        if response.status_code == 200:
            print(f"✅ HTTP: Sent event {event['data']['event_id']}")
            return True
        print(
            f"❌ HTTP: Failed to send event {event['data']['event_id']} - Status: {response.status_code}"
        )
        return False

    except Exception as e:
        print(f"❌ HTTP: Error sending event {event['data']['event_id']}: {e}")
        return False


def send_via_eventbus(event: dict) -> bool:
    """Send event via EventBus."""
    try:
        from claude_mpm.services.event_bus import EventBus

        event_bus = EventBus.get_instance()

        # Publish to EventBus
        success = event_bus.publish("hook.test_event", event)

        if success:
            print(f"✅ EventBus: Sent event {event['data']['event_id']}")
            return True
        print(f"❌ EventBus: Failed to send event {event['data']['event_id']}")
        return False

    except ImportError:
        print("❌ EventBus: EventBus not available")
        return False
    except Exception as e:
        print(f"❌ EventBus: Error sending event {event['data']['event_id']}: {e}")
        return False


async def main():
    """Main generator function."""
    parser = argparse.ArgumentParser(description="Event Generator for Testing")
    parser.add_argument(
        "--method",
        choices=["eventbus", "http", "both"],
        default="both",
        help="Method to send events",
    )
    parser.add_argument(
        "--count", type=int, default=10, help="Number of events to generate"
    )
    parser.add_argument(
        "--interval", type=float, default=1.0, help="Interval between events in seconds"
    )
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    args = parser.parse_args()

    print(f"🚀 Generating {args.count} test events via {args.method}")
    print(f"📡 Target: {args.host}:{args.port}")
    print(f"⏱️  Interval: {args.interval}s")
    print()

    success_count = 0

    for i in range(args.count):
        event_id = i + 1

        if args.method in ["eventbus", "both"]:
            event = generate_test_event(event_id, "eventbus")
            if send_via_eventbus(event):
                success_count += 1

        if args.method in ["http", "both"]:
            event = generate_test_event(event_id, "http")
            if send_via_http(event, args.host, args.port):
                success_count += 1

        # Wait between events
        if i < args.count - 1:  # Don't wait after last event
            await asyncio.sleep(args.interval)

    print()
    print(f"✅ Generation complete: {success_count} events sent successfully")

    # If using both methods, warn about potential duplicates
    if args.method == "both":
        print("⚠️  Note: Using 'both' methods may create duplicate events for testing")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Event generation stopped")
        sys.exit(0)
