#!/usr/bin/env python3
"""
Comprehensive Duplicate Event Test
=================================

Tests for duplicate events by:
1. Monitoring all Socket.IO events with timestamps
2. Generating events via multiple pathways
3. Analyzing for duplicates with detailed reporting
"""

import asyncio
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set

import requests
import socketio


class DuplicateEventTester:
    """Comprehensive duplicate event testing."""

    def __init__(self):
        self.events_received = []
        self.event_signatures = defaultdict(list)
        self.duplicates_found = []
        self.start_time = time.time()

    def add_event(self, event_name: str, data: dict, timestamp: float):
        """Add an event and check for duplicates."""
        # Create unique signature for the event
        signature = self._create_signature(event_name, data)

        event_record = {
            "timestamp": timestamp,
            "event_name": event_name,
            "signature": signature,
            "data": data,
            "relative_time": timestamp - self.start_time,
        }

        self.events_received.append(event_record)

        # Check for duplicates (same signature within 5 seconds)
        recent_events = [
            e
            for e in self.event_signatures[signature]
            if timestamp - e["timestamp"] < 5.0
        ]

        if recent_events:
            duplicate_info = {
                "signature": signature,
                "current_event": event_record,
                "previous_events": recent_events,
                "duplicate_count": len(recent_events) + 1,
            }
            self.duplicates_found.append(duplicate_info)
            print(f"🔴 DUPLICATE DETECTED: {signature}")
            print(f"   Count: {len(recent_events) + 1}")
            print(f"   Time gap: {timestamp - recent_events[-1]['timestamp']:.3f}s")

        self.event_signatures[signature].append(event_record)

        # Log the event
        print(f"📡 [{event_record['relative_time']:.3f}s] {event_name}")
        if data:
            key_fields = ["type", "subtype", "session_id", "event_id", "test_id"]
            summary = {
                k: v for k, v in data.items() if k in key_fields and v is not None
            }
            if summary:
                print(f"   {json.dumps(summary)}")

    def _create_signature(self, event_name: str, data: dict) -> str:
        """Create a unique signature for duplicate detection."""
        # Key fields that make an event unique
        key_fields = [
            "type",
            "subtype",
            "session_id",
            "event_id",
            "test_id",
            "tool_name",
            "hook_event_name",
        ]

        signature_parts = [event_name]
        for field in key_fields:
            if field in data and data[field] is not None:
                signature_parts.append(f"{field}:{data[field]}")

        return "|".join(signature_parts)

    def generate_report(self):
        """Generate comprehensive duplicate analysis report."""
        runtime = time.time() - self.start_time

        print("\n" + "=" * 70)
        print("COMPREHENSIVE DUPLICATE EVENT ANALYSIS")
        print("=" * 70)
        print(f"Test runtime: {runtime:.1f} seconds")
        print(f"Total events received: {len(self.events_received)}")
        print(f"Unique signatures: {len(self.event_signatures)}")
        print(f"Duplicates detected: {len(self.duplicates_found)}")

        if self.duplicates_found:
            print("\n🔴 DUPLICATE EVENTS FOUND:")
            for i, dup in enumerate(self.duplicates_found, 1):
                print(f"\n  Duplicate #{i}:")
                print(f"    Signature: {dup['signature']}")
                print(f"    Count: {dup['duplicate_count']}")
                times = [
                    f"{e['relative_time']:.3f}s"
                    for e in dup["previous_events"] + [dup["current_event"]]
                ]
                print(f"    Times: {times}")
        else:
            print("\n✅ NO DUPLICATE EVENTS DETECTED")

        # Event timeline
        if self.events_received:
            print("\n📊 EVENT TIMELINE:")
            for event in self.events_received[-10]:  # Show last 10 events
                print(
                    f"  {event['relative_time']:6.3f}s - {event['event_name']} - {event['signature'][:50]}..."
                )

        return len(self.duplicates_found) == 0


async def run_comprehensive_test():
    """Run comprehensive duplicate event test."""
    tester = DuplicateEventTester()

    print("🧪 Starting Comprehensive Duplicate Event Test")
    print("=" * 50)

    # Create Socket.IO client
    sio = socketio.AsyncClient(logger=False, engineio_logger=False)

    @sio.event
    async def connect():
        print("✅ Connected to Socket.IO server")

    @sio.event
    async def disconnect():
        print("❌ Disconnected from Socket.IO server")

    # Catch all events
    @sio.event
    async def catch_all(event_name, *args):
        timestamp = time.time()
        data = args[0] if args else {}
        if not isinstance(data, dict):
            data = {"raw_data": data}
        tester.add_event(event_name, data, timestamp)

    sio.on("*", catch_all)

    try:
        # Connect to server
        print("🔌 Connecting to Socket.IO server...")
        await sio.connect("http://localhost:8765")

        # Wait a moment for connection to stabilize
        await asyncio.sleep(1)

        # Generate test events via multiple pathways
        print("\n🚀 Generating test events...")

        # Test 1: EventBus events
        print("📡 Testing EventBus pathway...")
        for i in range(3):
            import subprocess

            result = subprocess.run(
                [
                    "python",
                    "scripts/test_event_generator.py",
                    "--method",
                    "eventbus",
                    "--count",
                    "1",
                ],
                capture_output=True,
                text=True,
                cwd=".",
                check=False,
            )
            await asyncio.sleep(0.5)  # Small delay between events

        # Test 2: HTTP events
        print("📡 Testing HTTP pathway...")
        for i in range(2):
            test_event = {
                "type": "hook",
                "subtype": "test_http_duplicate",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "test_id": f"http_duplicate_test_{i+1}",
                    "message": f"HTTP duplicate test event {i+1}",
                },
                "source": "duplicate_tester",
            }

            try:
                response = requests.post(
                    "http://localhost:8765/api/events", json=test_event, timeout=2
                )
                print(f"   HTTP event {i+1}: Status {response.status_code}")
            except Exception as e:
                print(f"   HTTP event {i+1}: Error {e}")

            await asyncio.sleep(0.5)

        # Wait for all events to be processed
        print("\n⏳ Waiting for events to be processed...")
        await asyncio.sleep(5)

        # Generate final report
        success = tester.generate_report()

        return success

    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
    finally:
        if sio.connected:
            await sio.disconnect()


if __name__ == "__main__":
    try:
        success = asyncio.run(run_comprehensive_test())
        if success:
            print("\n✅ DUPLICATE TEST PASSED - No duplicates detected")
            sys.exit(0)
        else:
            print("\n❌ DUPLICATE TEST FAILED - Duplicates detected")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        sys.exit(1)
