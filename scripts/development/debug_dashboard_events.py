#!/usr/bin/env python3
"""
Debug Dashboard Events Script

Comprehensive testing script to debug why only heartbeat events appear in the dashboard
instead of all EventBus events. This script will:

1. Generate various types of EventBus events
2. Monitor Socket.IO server emissions
3. Check the complete event flow from EventBus → Socket.IO → Dashboard
4. Provide detailed logging and diagnostics

Usage:
    python scripts/debug_dashboard_events.py [--port 8765] [--test-duration 30]
"""

import argparse
import asyncio
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    # Test EventBus availability
    from claude_mpm.services.event_bus.event_bus import EventBus
    from claude_mpm.services.events.core import Event
    from claude_mpm.services.events.producers.hook import HookEventProducer
    from claude_mpm.services.events.producers.system import SystemEventProducer
    from claude_mpm.services.socketio.server.broadcaster import EventBroadcaster
    from claude_mpm.services.socketio.server.core import SocketIOServer

    print("✓ All required imports loaded successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(
        "Make sure you're running from the project root and all dependencies are installed"
    )
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/tmp/debug_dashboard_events.log"),
    ],
)
logger = logging.getLogger(__name__)


class DashboardEventDebugger:
    """
    Comprehensive dashboard event debugging tool
    """

    def __init__(self, port: int = 8765):
        self.port = port
        self.event_bus = None
        self.socket_server = None
        self.events_generated = []
        self.events_emitted = []
        self.test_start_time = None

    async def initialize(self):
        """Initialize EventBus and Socket.IO server"""
        logger.info("Initializing EventBus and Socket.IO server...")

        try:
            # Initialize EventBus
            self.event_bus = EventBus()
            await self.event_bus.start()
            logger.info("✓ EventBus initialized and started")

            # Initialize Socket.IO server
            self.socket_server = SocketIOServer(port=self.port)
            await self.socket_server.start()
            logger.info(f"✓ Socket.IO server started on port {self.port}")

            # Set up event monitoring
            self._setup_event_monitoring()

        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            logger.error(traceback.format_exc())
            raise

    def _setup_event_monitoring(self):
        """Set up monitoring of events going through the system"""

        # Monitor EventBus events
        async def monitor_eventbus_event(event: Event):
            self.events_generated.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "EventBus",
                    "event_id": getattr(event, "id", "unknown"),
                    "event_type": (
                        f"{event.type}.{event.subtype}"
                        if hasattr(event, "subtype")
                        else event.type
                    ),
                    "data_keys": (
                        list(event.data.keys())
                        if hasattr(event, "data") and event.data
                        else []
                    ),
                }
            )
            logger.info(
                f"📨 EventBus event: {event.type}.{getattr(event, 'subtype', '')}"
            )

        # Subscribe to all EventBus events
        if hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe("*", monitor_eventbus_event)

        # Monitor Socket.IO emissions
        original_emit = None
        if hasattr(self.socket_server, "sio") and hasattr(
            self.socket_server.sio, "emit"
        ):
            original_emit = self.socket_server.sio.emit

            async def monitor_socket_emit(event_name, data=None, room=None, **kwargs):
                self.events_emitted.append(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "Socket.IO",
                        "event_name": event_name,
                        "data_type": type(data).__name__ if data else "None",
                        "data_size": len(str(data)) if data else 0,
                        "room": room,
                    }
                )
                logger.info(f"📡 Socket.IO emit: {event_name} -> {room or 'all'}")
                return await original_emit(event_name, data, room, **kwargs)

            self.socket_server.sio.emit = monitor_socket_emit

    async def generate_test_events(self, duration: int = 30):
        """Generate various test events for the specified duration"""
        logger.info(f"🧪 Starting test event generation for {duration} seconds...")
        self.test_start_time = time.time()

        # Create event producers
        hook_producer = HookEventProducer(self.event_bus)
        system_producer = SystemEventProducer(self.event_bus)

        event_types = [
            ("hook", "user_prompt"),
            ("hook", "pre_tool"),
            ("hook", "post_tool"),
            ("hook", "subagent_start"),
            ("hook", "subagent_stop"),
            ("session", "started"),
            ("session", "ended"),
            ("agent", "loaded"),
            ("agent", "executed"),
            ("todo", "updated"),
            ("memory", "operation"),
            ("log", "entry"),
            ("test", "event"),
            ("file", "operation"),
        ]

        end_time = time.time() + duration
        event_count = 0

        while time.time() < end_time:
            for event_type, subtype in event_types:
                if time.time() >= end_time:
                    break

                try:
                    # Generate event data based on type
                    event_data = self._generate_event_data(
                        event_type, subtype, event_count
                    )

                    # Create and emit event
                    event = Event(
                        type=event_type,
                        subtype=subtype,
                        data=event_data,
                        source="debug_script",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )

                    # Emit through EventBus
                    await self.event_bus.emit(event)
                    event_count += 1

                    logger.info(
                        f"📨 Generated {event_type}.{subtype} event #{event_count}"
                    )

                    # Small delay between events
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"❌ Failed to generate {event_type}.{subtype}: {e}")

            # Longer pause between rounds
            await asyncio.sleep(2)

        logger.info(
            f"✓ Test event generation completed. Generated {event_count} events."
        )

    def _generate_event_data(
        self, event_type: str, subtype: str, count: int
    ) -> Dict[str, Any]:
        """Generate realistic event data based on event type"""
        base_data = {
            "session_id": f"test_session_{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_event_id": count,
        }

        if event_type == "hook":
            if subtype == "user_prompt":
                return {
                    **base_data,
                    "prompt_text": f"Test user prompt #{count}",
                    "prompt_preview": f"Test prompt preview #{count}",
                }
            if subtype == "pre_tool":
                return {
                    **base_data,
                    "tool_name": "Read",
                    "operation_type": "file_read",
                    "tool_parameters": {"file_path": f"/test/file_{count}.txt"},
                }
            if subtype == "post_tool":
                return {
                    **base_data,
                    "tool_name": "Read",
                    "success": True,
                    "duration_ms": 123,
                    "operation_type": "file_read",
                }
            if subtype == "subagent_start":
                return {
                    **base_data,
                    "agent_type": "research",
                    "agent": "Research Agent",
                    "prompt": f"Test research task #{count}",
                    "description": f"Research task description #{count}",
                }
            if subtype == "subagent_stop":
                return {
                    **base_data,
                    "agent_type": "research",
                    "agent": "Research Agent",
                    "reason": "completed",
                    "structured_response": {"task_completed": True},
                }

        elif event_type == "session":
            return {**base_data, "session_id": f"session_{count}"}

        elif event_type == "agent":
            return {
                **base_data,
                "agent_type": "pm",
                "name": "PM Agent",
                "status": "active" if subtype == "loaded" else "completed",
            }

        elif event_type == "todo":
            return {
                **base_data,
                "todos": [
                    {
                        "id": f"todo_{count}",
                        "content": f"Test todo #{count}",
                        "status": "pending",
                    }
                ],
            }

        elif event_type == "memory":
            return {
                **base_data,
                "operation": "set",
                "key": f"test_key_{count}",
                "value": f"test_value_{count}",
            }

        elif event_type == "log":
            return {
                **base_data,
                "level": "info",
                "message": f"Test log message #{count}",
            }

        elif event_type == "test":
            return {
                **base_data,
                "test_name": f"Test Event #{count}",
                "test_data": {"key": f"value_{count}"},
            }

        elif event_type == "file":
            return {
                **base_data,
                "file_path": f"/test/file_{count}.txt",
                "operation": "read",
                "size": 1024,
            }

        return base_data

    async def monitor_dashboard_connection(self, duration: int = 30):
        """Monitor dashboard connections and events received"""
        logger.info("🔍 Monitoring dashboard connections...")

        # Check if there are any connected clients
        if hasattr(self.socket_server, "sio"):
            clients = []
            # Get connected clients
            for room_name, room_clients in self.socket_server.sio.manager.rooms.items():
                if room_name != "/":  # Skip the default room
                    continue
                clients.extend(room_clients)

            logger.info(f"📱 Connected clients: {len(set(clients))}")

            if not clients:
                logger.warning(
                    "⚠️  No dashboard clients connected! Please open http://localhost:8765 in your browser."
                )

        # Monitor for the specified duration
        start_time = time.time()
        while time.time() - start_time < duration:
            await asyncio.sleep(5)

            # Log periodic status
            elapsed = int(time.time() - start_time)
            logger.info(
                f"⏱️  Monitoring... {elapsed}s elapsed, {len(self.events_generated)} events generated, {len(self.events_emitted)} events emitted"
            )

    def generate_report(self) -> str:
        """Generate a comprehensive debug report"""
        total_time = time.time() - self.test_start_time if self.test_start_time else 0

        report = f"""
===============================================================================
📊 DASHBOARD EVENT DEBUG REPORT
===============================================================================

🕐 Test Duration: {total_time:.1f} seconds
📨 Events Generated (EventBus): {len(self.events_generated)}
📡 Events Emitted (Socket.IO): {len(self.events_emitted)}

===============================================================================
📨 EVENTBUS EVENTS GENERATED:
===============================================================================
"""

        # Group events by type
        eventbus_by_type = {}
        for event in self.events_generated:
            event_type = event["event_type"]
            if event_type not in eventbus_by_type:
                eventbus_by_type[event_type] = []
            eventbus_by_type[event_type].append(event)

        for event_type, events in sorted(eventbus_by_type.items()):
            report += f"\n{event_type}: {len(events)} events\n"
            for event in events[:3]:  # Show first 3 events of each type
                report += f"  - {event['timestamp']}: {event['data_keys']}\n"
            if len(events) > 3:
                report += f"  ... and {len(events) - 3} more\n"

        report += """
===============================================================================
📡 SOCKET.IO EVENTS EMITTED:
===============================================================================
"""

        # Group socket events by name
        socket_by_name = {}
        for event in self.events_emitted:
            event_name = event["event_name"]
            if event_name not in socket_by_name:
                socket_by_name[event_name] = []
            socket_by_name[event_name].append(event)

        for event_name, events in sorted(socket_by_name.items()):
            report += f"\n{event_name}: {len(events)} emissions\n"
            for event in events[:3]:  # Show first 3 events of each type
                report += f"  - {event['timestamp']}: {event['data_type']} ({event['data_size']} chars) -> {event['room'] or 'all'}\n"
            if len(events) > 3:
                report += f"  ... and {len(events) - 3} more\n"

        report += f"""
===============================================================================
🔍 ANALYSIS AND RECOMMENDATIONS:
===============================================================================

1. Event Flow Analysis:
   - EventBus generated {len(self.events_generated)} events
   - Socket.IO emitted {len(self.events_emitted)} events
   - Ratio: {len(self.events_emitted) / max(len(self.events_generated), 1):.2f} (ideally should be close to 1.0)

2. Event Type Distribution:
   - EventBus types: {len(eventbus_by_type)} unique types
   - Socket.IO events: {len(socket_by_name)} unique event names

3. Potential Issues:
"""

        # Analyze potential issues
        if len(self.events_emitted) == 0:
            report += "   ❌ NO SOCKET.IO EVENTS EMITTED - Check EventBus to Socket.IO integration\n"
        elif len(self.events_emitted) < len(self.events_generated) * 0.8:
            report += "   ⚠️  FEWER SOCKET.IO EVENTS THAN EVENTBUS EVENTS - Some events may be lost\n"
        elif "claude_event" not in socket_by_name:
            report += "   ❌ NO 'claude_event' EMISSIONS - Dashboard expects 'claude_event' events\n"
        elif "heartbeat" in socket_by_name and len(socket_by_name) == 1:
            report += (
                "   ❌ ONLY HEARTBEAT EVENTS - EventBus events not reaching Socket.IO\n"
            )
        else:
            report += "   ✓ Event flow appears normal\n"

        report += f"""
4. Next Steps:
   - Open browser dev tools at http://localhost:{self.port}
   - Check WebSocket frames for 'claude_event' messages
   - Verify dashboard JavaScript event handlers are working
   - Check for JavaScript errors in browser console

===============================================================================
"""

        return report

    async def run_debug_session(self, duration: int = 30):
        """Run a complete debug session"""
        try:
            await self.initialize()

            # Start both monitoring and event generation concurrently
            await asyncio.gather(
                self.generate_test_events(duration),
                self.monitor_dashboard_connection(duration),
            )

            # Generate and display report
            report = self.generate_report()
            print(report)

            # Save report to file
            report_file = f"/tmp/dashboard_debug_report_{int(time.time())}.txt"
            with open(report_file, "w") as f:
                f.write(report)
            logger.info(f"📄 Debug report saved to: {report_file}")

        except Exception as e:
            logger.error(f"❌ Debug session failed: {e}")
            logger.error(traceback.format_exc())
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up...")

        try:
            if self.event_bus:
                await self.event_bus.stop()
                logger.info("✓ EventBus stopped")
        except Exception as e:
            logger.error(f"Error stopping EventBus: {e}")

        try:
            if self.socket_server:
                await self.socket_server.stop()
                logger.info("✓ Socket.IO server stopped")
        except Exception as e:
            logger.error(f"Error stopping Socket.IO server: {e}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Debug dashboard event flow")
    parser.add_argument(
        "--port", type=int, default=8765, help="Socket.IO server port (default: 8765)"
    )
    parser.add_argument(
        "--test-duration",
        type=int,
        default=30,
        help="Test duration in seconds (default: 30)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print(
        f"""
🔍 Dashboard Event Flow Debugger
================================

This script will:
1. Start EventBus and Socket.IO server on port {args.port}
2. Generate various test events for {args.test_duration} seconds
3. Monitor event flow from EventBus → Socket.IO → Dashboard
4. Generate a comprehensive debug report

Please open http://localhost:{args.port} in your browser to see the dashboard.
Press Ctrl+C to stop early if needed.

Starting debug session...
"""
    )

    debugger = DashboardEventDebugger(port=args.port)

    try:
        await debugger.run_debug_session(duration=args.test_duration)
    except KeyboardInterrupt:
        print("\n⏹️  Debug session interrupted by user")
    except Exception as e:
        print(f"\n❌ Debug session failed: {e}")
        return 1

    print(
        "\n✓ Debug session completed. Check the browser console and network tab for detailed analysis."
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
