#!/usr/bin/env python3
"""Simple script to start the Event Aggregator service.

WHY: Provides a quick way to start the event aggregator that captures
Socket.IO events and saves them as structured session documents.

USAGE:
    python scripts/start_event_aggregator.py
    # or
    ./scripts/start_event_aggregator.py

The aggregator will:
1. Connect to the Socket.IO dashboard server on port 8765
2. Capture all claude_event emissions
3. Build complete agent sessions from the event stream
4. Save sessions as JSON documents in .claude-mpm/sessions/
"""

import signal
import sys
import time
from pathlib import Path

# Add parent directory to path so we can import claude_mpm
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.logger import get_logger
from claude_mpm.services.event_aggregator import (
    aggregator_status,
    start_aggregator,
    stop_aggregator,
)

logger = get_logger("start_event_aggregator")


def check_socketio_server():
    """Check if the Socket.IO server is running.

    Returns:
        True if server is running, False otherwise
    """
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", 8765))
            return result == 0
    except Exception as e:
        logger.error(f"Error checking server: {e}")
        return False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("\n\nReceived shutdown signal, stopping aggregator...")

    # Get final statistics
    status = aggregator_status()

    # Stop the aggregator
    stop_aggregator()

    # Print summary
    print("\n" + "=" * 60)
    print("Event Aggregator Session Summary")
    print("=" * 60)
    print(f"Total events captured: {status['total_events']}")
    print(f"Sessions completed: {status['sessions_completed']}")
    print(f"Active sessions saved: {status['active_sessions']}")

    if status["events_by_type"]:
        print("\nTop event types:")
        for event_type, count in sorted(
            status["events_by_type"].items(), key=lambda x: x[1], reverse=True
        )[:5]:
            print(f"  {event_type:30s} {count:6d}")

    print(f"\nSessions saved to: {status['save_directory']}")
    print("\nGoodbye!")
    sys.exit(0)


def main():
    """Main entry point for the aggregator startup script."""
    print("=" * 60)
    print("Claude MPM Event Aggregator")
    print("=" * 60)

    # Check if Socket.IO is available
    try:
        import socketio

        print("✅ Socket.IO client library available")
    except ImportError:
        print("❌ Socket.IO client library not installed")
        print("   Install with: pip install python-socketio")
        return 1

    # Check if server is running
    print("\nChecking for Socket.IO dashboard server...")
    if check_socketio_server():
        print("✅ Socket.IO server detected on port 8765")
    else:
        print("⚠️  Socket.IO server not detected on port 8765")
        print("   The dashboard server should be running for the aggregator to work.")
        print("   Start it with: claude-mpm monitor")
        print()
        response = input("Start aggregator anyway? (y/N): ")
        if response.lower() != "y":
            print("Exiting.")
            return 0

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the aggregator
    print("\nStarting Event Aggregator...")
    if start_aggregator():
        print("✅ Event Aggregator started successfully")
        print()
        print("The aggregator is now:")
        print("  • Listening for events from the Socket.IO server")
        print("  • Building complete session documents from events")
        print("  • Saving sessions to .claude-mpm/sessions/")
        print()
        print("Press Ctrl+C to stop the aggregator...")
        print()

        # Keep running and show periodic status
        last_status_time = time.time()
        status_interval = 30  # Show status every 30 seconds

        try:
            while True:
                time.sleep(1)

                # Show periodic status
                current_time = time.time()
                if current_time - last_status_time >= status_interval:
                    status = aggregator_status()
                    if status["total_events"] > 0:
                        print("\n📊 Status Update:")
                        print(f"   Events captured: {status['total_events']}")
                        print(f"   Active sessions: {status['active_sessions']}")
                        print(f"   Completed sessions: {status['sessions_completed']}")

                        if status["active_session_ids"]:
                            print("   Active session IDs:")
                            for sid in status["active_session_ids"][:3]:
                                print(f"     - {sid}")
                            if len(status["active_session_ids"]) > 3:
                                print(
                                    f"     ... and {len(status['active_session_ids']) - 3} more"
                                )

                    last_status_time = current_time

        except KeyboardInterrupt:
            # Signal handler will take care of cleanup
            pass
    else:
        print("❌ Failed to start Event Aggregator")
        print("   Check the logs for more details")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
