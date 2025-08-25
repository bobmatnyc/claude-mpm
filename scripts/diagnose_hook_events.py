#!/usr/bin/env python3
"""
Diagnostic script to test hook event flow to dashboard.

This script tests the entire event flow from hook handler to dashboard:
1. Hook handler -> ConnectionManager -> SocketIO/EventBus
2. EventBus -> SocketIORelay -> Socket.IO server
3. Socket.IO server -> Dashboard clients

Run this to identify where hook events are failing to reach the dashboard.
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Try to import required components
try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("❌ Socket.IO not available - install with: pip install python-socketio")

from claude_mpm.core.socketio_pool import get_connection_pool
from claude_mpm.services.event_bus import EventBus
from claude_mpm.services.socketio.server.main import SocketIOServer


class HookEventDiagnostic:
    """Diagnose hook event flow issues."""

    def __init__(self):
        self.results = {
            "socketio_server": None,
            "eventbus": None,
            "relay": None,
            "connection_pool": None,
            "dashboard_connection": None,
            "event_flow": None,
        }
        self.server = None
        self.dashboard_client = None
        self.received_events = []

    async def test_socketio_server(self):
        """Test if Socket.IO server can start."""
        print("\n1. Testing Socket.IO Server...")
        try:
            self.server = SocketIOServer(port=8765)
            self.server.start_sync()
            time.sleep(2)  # Give server time to start

            if self.server.running:
                print("✅ Socket.IO server started successfully on port 8765")
                self.results["socketio_server"] = "OK"
                return True
            print("❌ Socket.IO server failed to start")
            self.results["socketio_server"] = "Server not running"
            return False
        except Exception as e:
            print(f"❌ Socket.IO server error: {e}")
            self.results["socketio_server"] = str(e)
            return False

    async def test_eventbus(self):
        """Test EventBus initialization and publishing."""
        print("\n2. Testing EventBus...")
        try:
            # Get EventBus instance
            event_bus = EventBus.get_instance()
            event_bus.enable()
            event_bus.set_debug(True)

            # Test publishing an event
            test_received = False

            async def test_handler(event_type, data):
                nonlocal test_received
                test_received = True
                print(f"   Received test event: {event_type}")

            # Subscribe to test event
            event_bus.on("test.event", test_handler)

            # Publish test event
            event_bus.publish("test.event", {"test": "data"})

            # Give time for async processing
            await asyncio.sleep(0.5)

            if test_received:
                print("✅ EventBus working correctly")
                self.results["eventbus"] = "OK"
                return True
            print("❌ EventBus not processing events")
            self.results["eventbus"] = "Events not processed"
            return False

        except Exception as e:
            print(f"❌ EventBus error: {e}")
            self.results["eventbus"] = str(e)
            return False

    async def test_relay(self):
        """Test SocketIORelay functionality."""
        print("\n3. Testing SocketIO Relay...")
        try:
            # Check if EventBus integration is active
            if hasattr(self.server, "eventbus_integration"):
                integration = self.server.eventbus_integration
                if integration and integration.is_active():
                    print("✅ EventBus integration is active")
                    if integration.relay:
                        print(f"✅ Relay connected: {integration.relay.connected}")
                        self.results["relay"] = "OK"
                        return True
                    print("❌ Relay not initialized")
                    self.results["relay"] = "Relay not initialized"
                    return False
                print("❌ EventBus integration not active")
                self.results["relay"] = "Integration not active"
                return False
            print("❌ No EventBus integration found")
            self.results["relay"] = "No integration"
            return False

        except Exception as e:
            print(f"❌ Relay error: {e}")
            self.results["relay"] = str(e)
            return False

    async def test_connection_pool(self):
        """Test SocketIO connection pool."""
        print("\n4. Testing Connection Pool...")
        try:
            pool = get_connection_pool()

            # Test emitting an event through the pool
            test_event = {
                "type": "hook",
                "subtype": "diagnostic_test",
                "timestamp": datetime.now().isoformat(),
                "data": {"test": "connection_pool"},
            }

            pool.emit("claude_event", test_event)
            print("✅ Connection pool emit successful")
            self.results["connection_pool"] = "OK"
            return True

        except Exception as e:
            print(f"❌ Connection pool error: {e}")
            self.results["connection_pool"] = str(e)
            return False

    async def test_dashboard_connection(self):
        """Test connecting to dashboard as a client."""
        print("\n5. Testing Dashboard Connection...")
        if not SOCKETIO_AVAILABLE:
            print("❌ Socket.IO client not available")
            self.results["dashboard_connection"] = "Socket.IO not installed"
            return False

        try:
            self.dashboard_client = socketio.AsyncClient()

            @self.dashboard_client.event
            async def claude_event(data):
                self.received_events.append(data)
                print(
                    f"   📨 Dashboard received: {data.get('type', 'unknown')}.{data.get('subtype', 'unknown')}"
                )

            await self.dashboard_client.connect("http://localhost:8765")
            print("✅ Connected to dashboard as client")
            self.results["dashboard_connection"] = "OK"
            return True

        except Exception as e:
            print(f"❌ Dashboard connection error: {e}")
            self.results["dashboard_connection"] = str(e)
            return False

    async def test_full_event_flow(self):
        """Test the complete event flow from hook to dashboard."""
        print("\n6. Testing Full Event Flow...")

        # Clear received events
        self.received_events = []

        try:
            # Test 1: Direct Socket.IO broadcast
            print("   Testing direct broadcast...")
            self.server.broadcast_event(
                "hook",
                {
                    "subtype": "direct_test",
                    "timestamp": datetime.now().isoformat(),
                    "data": {"source": "direct_broadcast"},
                },
            )
            await asyncio.sleep(1)

            # Test 2: Through EventBus
            print("   Testing EventBus publish...")
            event_bus = EventBus.get_instance()
            event_bus.publish(
                "hook.eventbus_test",
                {
                    "timestamp": datetime.now().isoformat(),
                    "data": {"source": "eventbus"},
                },
            )
            await asyncio.sleep(1)

            # Test 3: Through connection pool
            print("   Testing connection pool...")
            pool = get_connection_pool()
            pool.emit(
                "claude_event",
                {
                    "type": "hook",
                    "subtype": "pool_test",
                    "timestamp": datetime.now().isoformat(),
                    "data": {"source": "connection_pool"},
                },
            )
            await asyncio.sleep(1)

            # Check results
            if len(self.received_events) > 0:
                print(f"✅ Received {len(self.received_events)} events at dashboard")
                for event in self.received_events:
                    print(
                        f"     - {event.get('type', 'unknown')}.{event.get('subtype', 'unknown')}"
                    )
                self.results["event_flow"] = "OK"
                return True
            print("❌ No events received at dashboard")
            self.results["event_flow"] = "No events received"
            return False

        except Exception as e:
            print(f"❌ Event flow error: {e}")
            self.results["event_flow"] = str(e)
            return False

    async def run_diagnostics(self):
        """Run all diagnostic tests."""
        print("=" * 60)
        print("HOOK EVENT DIAGNOSTIC")
        print("=" * 60)

        # Run tests in sequence
        await self.test_socketio_server()
        await self.test_eventbus()
        await self.test_relay()
        await self.test_connection_pool()
        await self.test_dashboard_connection()
        await self.test_full_event_flow()

        # Print summary
        print("\n" + "=" * 60)
        print("DIAGNOSTIC RESULTS")
        print("=" * 60)

        all_ok = True
        for component, status in self.results.items():
            icon = "✅" if status == "OK" else "❌"
            print(f"{icon} {component}: {status}")
            if status != "OK":
                all_ok = False

        print("\n" + "=" * 60)
        if all_ok:
            print("✅ ALL TESTS PASSED - Hook events should work")
        else:
            print("❌ ISSUES FOUND - See above for details")

            # Provide specific recommendations
            print("\nRECOMMENDATIONS:")
            if self.results["socketio_server"] != "OK":
                print("1. Check if port 8765 is available")
                print("   Run: lsof -i :8765")

            if self.results["eventbus"] != "OK":
                print("2. Check EventBus configuration")
                print("   Set: export CLAUDE_MPM_EVENTBUS_ENABLED=true")

            if self.results["relay"] != "OK":
                print("3. Check relay configuration")
                print("   Set: export CLAUDE_MPM_RELAY_ENABLED=true")
                print("   The relay may not be starting properly")

            if self.results["event_flow"] != "OK":
                print("4. Check event routing between components")
                print("   Enable debug: export CLAUDE_MPM_EVENTBUS_DEBUG=true")
                print("                 export CLAUDE_MPM_RELAY_DEBUG=true")

        print("=" * 60)

        # Cleanup
        if self.dashboard_client:
            await self.dashboard_client.disconnect()
        if self.server:
            self.server.stop_sync()


if __name__ == "__main__":
    diagnostic = HookEventDiagnostic()
    asyncio.run(diagnostic.run_diagnostics())
