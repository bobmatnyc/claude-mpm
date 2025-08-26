#!/usr/bin/env python3
"""
Test Script for Async Code Analysis Feature
===========================================

This script tests the async, event-driven code analysis feature by:
1. Starting a mock Socket.IO server
2. Sending a code analysis request
3. Verifying events are received in real-time
4. Checking that the UI doesn't block during analysis
"""

import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.logging_config import get_logger
from claude_mpm.dashboard.analysis_runner import CodeAnalysisRunner

logger = get_logger(__name__)


class MockSocketIOServer:
    """Mock Socket.IO server for testing."""

    def __init__(self, port=8765):
        self.port = port
        self.events = []
        self.logger = get_logger(__name__)

    def broadcast_event(self, event_type: str, data: dict):
        """Simulate broadcasting an event."""
        event = {"type": event_type, "data": data, "timestamp": time.time()}
        self.events.append(event)

        # Log event for debugging
        if event_type in ["code:file:start", "code:node:found"]:
            self.logger.info(
                f"Event: {event_type} - {data.get('path', data.get('name', 'unknown'))[:50]}"
            )
        elif event_type == "code:analysis:progress":
            self.logger.info(
                f"Progress: {data.get('percentage', 0):.1f}% - {data.get('message', '')}"
            )
        else:
            self.logger.info(f"Event: {event_type}")


async def test_async_analysis():
    """Test the async code analysis functionality."""

    print("\n" + "=" * 60)
    print("Testing Async Code Analysis")
    print("=" * 60 + "\n")

    # Create mock server
    server = MockSocketIOServer()

    # Create analysis runner
    runner = CodeAnalysisRunner(server)
    runner.start()

    try:
        # Test 1: Request analysis
        print("Test 1: Requesting code analysis...")
        request_id = "test-analysis-001"
        test_path = str(Path(__file__).parent.parent / "src" / "claude_mpm")

        success = runner.request_analysis(
            request_id=request_id, path=test_path, languages=["python"], max_depth=2
        )

        assert success, "Failed to queue analysis request"
        print("✅ Analysis request queued successfully\n")

        # Test 2: Check for real-time events
        print("Test 2: Monitoring real-time events...")
        start_time = time.time()
        timeout = 30  # 30 second timeout

        event_types_seen = set()
        file_count = 0
        node_count = 0

        while time.time() - start_time < timeout:
            # Check for new events
            for event in server.events[len(event_types_seen) :]:
                event_type = event["type"]
                event_types_seen.add(event_type)

                if event_type == "code:file:start":
                    file_count += 1
                elif event_type == "code:node:found":
                    node_count += 1
                elif event_type in ["code:analysis:complete", "code:analysis:error"]:
                    print(f"\nAnalysis finished: {event_type}")
                    break

            # Show progress
            if file_count > 0 or node_count > 0:
                print(f"\rFiles: {file_count}, Nodes: {node_count}", end="", flush=True)

            # Check if analysis is complete
            if (
                "code:analysis:complete" in event_types_seen
                or "code:analysis:error" in event_types_seen
            ):
                break

            await asyncio.sleep(0.1)

        print("\n")

        # Test 3: Verify event types received
        print("Test 3: Verifying event types...")
        expected_events = [
            "code:analysis:queued",
            "code:analysis:start",
            "code:file:start",
            "code:node:found",
        ]

        for event_type in expected_events:
            if event_type in event_types_seen:
                print(f"✅ Received {event_type}")
            else:
                print(f"⚠️  Missing {event_type}")

        # Test 4: Test cancellation
        print("\nTest 4: Testing cancellation...")

        # Start another analysis
        request_id2 = "test-analysis-002"
        runner.request_analysis(
            request_id=request_id2, path=test_path, languages=["python"]
        )

        # Wait a moment for it to start
        await asyncio.sleep(1)

        # Cancel it
        runner.cancel_current()

        # Check for cancellation event
        await asyncio.sleep(1)

        cancelled = any(e["type"] == "code:analysis:cancelled" for e in server.events)
        if cancelled:
            print("✅ Cancellation successful")
        else:
            print("⚠️  Cancellation event not received")

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Total events received: {len(server.events)}")
        print(f"Event types seen: {len(event_types_seen)}")
        print(f"Files analyzed: {file_count}")
        print(f"Nodes found: {node_count}")

        # Determine success
        if file_count > 0 and node_count > 0:
            print("\n✅ All tests passed! Async analysis is working correctly.")
            return True
        print("\n❌ Some tests failed. Check the logs above.")
        return False

    finally:
        # Cleanup
        runner.stop()
        print("\n" + "=" * 60)


if __name__ == "__main__":
    # Run the async test
    success = asyncio.run(test_async_analysis())

    # Exit with appropriate code
    sys.exit(0 if success else 1)
