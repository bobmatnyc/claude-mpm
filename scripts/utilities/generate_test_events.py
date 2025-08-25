#!/usr/bin/env python3
"""
Generate Test Events for Dashboard

This script generates test events to verify the EventBus → Socket.IO → Dashboard flow.
Run this while monitoring the dashboard to see if events appear.

Usage:
    python scripts/generate_test_events.py [--count 10] [--interval 2]
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    # Import required modules for direct event emission
    import socketio

    print("✓ Socket.IO imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Install socketio: pip install python-socketio")
    sys.exit(1)


class TestEventGenerator:
    """Generate test events and emit them directly to the dashboard"""

    def __init__(self, port: int = 8765):
        self.port = port
        self.sio = socketio.AsyncClient()
        self.connected = False

    async def connect_to_dashboard(self):
        """Connect to the dashboard as a client"""

        @self.sio.event
        async def connect():
            self.connected = True
            print(f"✓ Connected to dashboard at localhost:{self.port}")

        @self.sio.event
        async def disconnect():
            self.connected = False
            print("❌ Disconnected from dashboard")

        try:
            url = f"http://localhost:{self.port}"
            print(f"🔌 Connecting to {url}...")
            await self.sio.connect(url)
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    async def generate_test_events(self, count: int = 10, interval: float = 2.0):
        """Generate test events and emit them directly"""

        if not self.connected:
            print("❌ Not connected to dashboard")
            return

        print(f"🧪 Generating {count} test events with {interval}s intervals...")

        for i in range(count):
            # Create test event in the format expected by dashboard
            test_event = {
                "id": f"test_event_{i}_{int(time.time())}",
                "type": "test",
                "subtype": "generated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "test_generator",
                "data": {
                    "test_number": i + 1,
                    "total_tests": count,
                    "message": f"Test event #{i + 1} generated from script",
                    "session_id": f"test_session_{int(time.time())}",
                    "test_data": {
                        "key1": f"value_{i}",
                        "key2": i * 2,
                        "key3": i % 2 == 0,
                    },
                },
            }

            try:
                # Emit as 'claude_event' which is what the dashboard listens for
                await self.sio.emit("claude_event", test_event)
                print(
                    f"📤 Emitted test event #{i + 1}: {test_event['type']}.{test_event['subtype']}"
                )

                # Also try alternative event names in case dashboard listens to others
                await self.sio.emit("test.event", test_event)

                if i < count - 1:  # Don't sleep after the last event
                    await asyncio.sleep(interval)

            except Exception as e:
                print(f"❌ Failed to emit event #{i + 1}: {e}")

        print(f"✓ Finished generating {count} test events")

    async def generate_hook_events(self, count: int = 5):
        """Generate hook-style events similar to what the real system generates"""

        if not self.connected:
            print("❌ Not connected to dashboard")
            return

        print(f"🔗 Generating {count} hook-style events...")

        hook_events = [
            {
                "type": "hook",
                "subtype": "user_prompt",
                "data": {
                    "prompt_text": "Test user prompt from generator",
                    "prompt_preview": "Test prompt...",
                    "session_id": f"hook_session_{int(time.time())}",
                },
            },
            {
                "type": "hook",
                "subtype": "pre_tool",
                "data": {
                    "tool_name": "Read",
                    "operation_type": "file_read",
                    "tool_parameters": {"file_path": "/test/file.txt"},
                    "session_id": f"hook_session_{int(time.time())}",
                },
            },
            {
                "type": "hook",
                "subtype": "post_tool",
                "data": {
                    "tool_name": "Read",
                    "success": True,
                    "duration_ms": 125,
                    "operation_type": "file_read",
                    "session_id": f"hook_session_{int(time.time())}",
                },
            },
            {
                "type": "hook",
                "subtype": "subagent_start",
                "data": {
                    "agent_type": "research",
                    "agent": "Research Agent",
                    "prompt": "Test research task from generator",
                    "description": "Research task description",
                    "session_id": f"hook_session_{int(time.time())}",
                },
            },
            {
                "type": "hook",
                "subtype": "subagent_stop",
                "data": {
                    "agent_type": "research",
                    "agent": "Research Agent",
                    "reason": "completed",
                    "structured_response": {"task_completed": True},
                    "session_id": f"hook_session_{int(time.time())}",
                },
            },
        ]

        for i, event_template in enumerate(hook_events[:count]):
            event = {
                "id": f"hook_event_{i}_{int(time.time())}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "hook_generator",
                **event_template,
            }

            try:
                await self.sio.emit("claude_event", event)
                print(
                    f"📤 Emitted hook event #{i + 1}: {event['type']}.{event['subtype']}"
                )
                await asyncio.sleep(1)

            except Exception as e:
                print(f"❌ Failed to emit hook event #{i + 1}: {e}")

        print(f"✓ Finished generating {count} hook events")

    async def disconnect_from_dashboard(self):
        """Disconnect from dashboard"""
        if self.connected:
            await self.sio.disconnect()


async def main():
    parser = argparse.ArgumentParser(description="Generate test events for dashboard")
    parser.add_argument(
        "--port", type=int, default=8765, help="Dashboard port (default: 8765)"
    )
    parser.add_argument(
        "--count", type=int, default=10, help="Number of test events (default: 10)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Interval between events in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--hook-events",
        action="store_true",
        help="Generate hook-style events instead of generic test events",
    )

    args = parser.parse_args()

    print(
        f"""
🧪 Test Event Generator
=======================

Connecting to dashboard at localhost:{args.port}
Will generate {'hook-style' if args.hook_events else 'test'} events.

Make sure the dashboard is open in your browser to see the events!
Open: http://localhost:{args.port}
"""
    )

    generator = TestEventGenerator(port=args.port)

    try:
        # Connect to dashboard
        if not await generator.connect_to_dashboard():
            return 1

        # Wait a moment for connection to stabilize
        await asyncio.sleep(1)

        # Generate events
        if args.hook_events:
            await generator.generate_hook_events(count=args.count)
        else:
            await generator.generate_test_events(
                count=args.count, interval=args.interval
            )

        # Wait a moment before disconnecting
        await asyncio.sleep(2)

    except KeyboardInterrupt:
        print("\n⏹️ Event generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Event generation failed: {e}")
        return 1
    finally:
        await generator.disconnect_from_dashboard()

    print(
        """
✓ Event generation completed!

If events appeared in the dashboard:
    ✅ Socket.IO connectivity is working
    ✅ Dashboard can receive and display events
    
If events did NOT appear:
    ❌ Check browser console for JavaScript errors
    ❌ Check Network tab for WebSocket 'claude_event' frames
    ❌ Verify EventViewer is processing events correctly
    
Next: Open browser dev tools and run the debug commands!
"""
    )

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
