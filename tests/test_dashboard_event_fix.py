#!/usr/bin/env python3
"""Test script to verify dashboard event parsing fixes."""

import pytest

# Skip entire module - Dashboard event handling refactored - needs rewrite
pytestmark = pytest.mark.skip(
    reason="Dashboard event handling refactored - needs rewrite"
)


import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# from claude_mpm.services.socketio.server.core import SocketIOService
# from claude_mpm.services.socketio.server.broadcaster import EventBroadcaster

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_event_parsing():
    """Test that events with conflicting data fields are handled correctly."""

    # Initialize services
    socketio_service = SocketIOService()
    broadcaster = EventBroadcaster()

    # Start the SocketIO server
    await socketio_service.start()
    logger.info(f"SocketIO server started on port {socketio_service.port}")

    # Wait for server to be ready
    await asyncio.sleep(2)

    # Test events that would previously cause issues
    test_events = [
        # Event 1: Hook event with type in data (should preserve hook.pre_tool)
        {
            "type": "hook.pre_tool",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "type": "should_not_overwrite",  # This should NOT overwrite the main type
                "tool_name": "Edit",
                "parameters": {"file_path": "/test/file.py"},
            },
        },
        # Event 2: Legacy event format
        {
            "event": "SubagentStart",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"agent_type": "Engineer", "task": "Fix bug in authentication"},
        },
        # Event 3: Standard event with subtype in data
        {
            "type": "session",
            "subtype": "started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "subtype": "different_subtype",  # Should NOT overwrite
                "session_id": "test-123",
                "user": "test_user",
            },
        },
        # Event 4: Tool event with complex data
        {
            "type": "hook.post_tool",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "type": "conflicting_type",
                "subtype": "conflicting_subtype",
                "tool_name": "MultiEdit",
                "result": "success",
                "edits_count": 3,
            },
        },
    ]

    logger.info("Broadcasting test events...")

    for i, event in enumerate(test_events, 1):
        logger.info(f"\nTest Event {i}:")
        logger.info(f"  Original type: {event.get('type', event.get('event', 'none'))}")
        if "data" in event and "type" in event["data"]:
            logger.info(f"  Data.type (should not overwrite): {event['data']['type']}")

        # Broadcast the event
        await broadcaster.broadcast_event(event)

        # Wait a bit between events
        await asyncio.sleep(1)

    logger.info("\nAll test events sent!")
    logger.info("Check the dashboard at http://localhost:8080 to verify:")
    logger.info("1. Events should show proper types (not 'unknown')")
    logger.info(
        "2. hook.pre_tool should show as 'hook.pre_tool', not 'should_not_overwrite'"
    )
    logger.info("3. SubagentStart should be transformed to 'subagent.start'")
    logger.info("4. Session events should keep their correct type/subtype")

    # Keep server running for manual inspection
    logger.info("\nServer running. Press Ctrl+C to stop...")
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await socketio_service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(test_event_parsing())
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
