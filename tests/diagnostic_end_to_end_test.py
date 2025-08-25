#!/usr/bin/env python3
"""End-to-End Socket.IO Event Flow Diagnostic.

This script provides a comprehensive test of the entire event flow:
1. Starts a diagnostic Socket.IO server
2. Simulates hook handler events
3. Tests dashboard connections
4. Verifies event routing and delivery
5. Measures timing and reliability

WHY this comprehensive test:
- Tests the complete event pipeline from hook -> server -> dashboard
- Identifies timing issues and race conditions
- Validates authentication and namespace routing
- Provides performance metrics and reliability data
"""

import asyncio
import sys
import threading
import time
from datetime import datetime

try:
    import socketio
    from aiohttp import web

    SOCKETIO_AVAILABLE = True
except ImportError:
    print(
        "ERROR: python-socketio package not installed. Run: pip install python-socketio[asyncio_client] aiohttp"
    )
    sys.exit(1)


class EndToEndDiagnosticTest:
    """Comprehensive end-to-end diagnostic test orchestrator."""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.server_url = f"http://{host}:{port}"
        self.start_time = datetime.now()

        # Test state
        self.server_running = False
        self.hook_client_connected = False
        self.dashboard_clients_connected = {}
        self.events_sent = 0
        self.events_received = {}
        self.timing_data = []
        self.errors = []

        # Components
        self.server = None
        self.hook_client = None
        self.dashboard_clients = {}

        print("🔍 END-TO-END DIAGNOSTIC TEST")
        print(f"🌐 Server URL: {self.server_url}")
        print(f"📅 Start time: {self.start_time.isoformat()}")
        print("=" * 80)

    async def setup_diagnostic_server(self):
        """Setup Socket.IO server with comprehensive monitoring."""
        print("🚀 Setting up diagnostic Socket.IO server...")

        # Create Socket.IO server with logging
        self.sio_server = socketio.AsyncServer(
            cors_allowed_origins="*",
            async_mode="aiohttp",
            ping_timeout=60,
            ping_interval=25,
            logger=False,
            engineio_logger=False,
        )

        # Create aiohttp app
        self.app = web.Application()
        self.sio_server.attach(self.app)

        # Track connections
        self.server_connections = {}
        self.server_events = []

        # Setup namespace handlers
        namespaces = [
            "/system",
            "/session",
            "/claude",
            "/agent",
            "/hook",
            "/todo",
            "/memory",
            "/log",
        ]

        for namespace in namespaces:
            await self._setup_server_namespace(namespace)

        # Setup health endpoints
        async def health_check(request):
            return web.json_response(
                {
                    "status": "running",
                    "connections": len(self.server_connections),
                    "events_received": len(self.server_events),
                    "uptime_seconds": (
                        datetime.now() - self.start_time
                    ).total_seconds(),
                }
            )

        self.app.router.add_get("/health", health_check)

        print("✅ Diagnostic server setup complete")

    async def _setup_server_namespace(self, namespace: str):
        """Setup handlers for a specific namespace."""

        @self.sio_server.event(namespace=namespace)
        async def connect(sid, environ, auth):
            self.server_connections[sid] = {
                "namespace": namespace,
                "connect_time": datetime.now(),
                "auth": auth,
            }

            event_data = {
                "type": "connection",
                "namespace": namespace,
                "sid": sid,
                "auth": auth,
                "timestamp": datetime.now().isoformat(),
            }
            self.server_events.append(event_data)

            print(f"🔗 SERVER: Connection to {namespace} from {sid}")

            # Join namespace room
            room_name = f"{namespace.lstrip('/')}_room"
            await self.sio_server.enter_room(sid, room_name, namespace=namespace)

            return True

        @self.sio_server.event(namespace=namespace)
        async def disconnect(sid):
            if sid in self.server_connections:
                del self.server_connections[sid]

            event_data = {
                "type": "disconnection",
                "namespace": namespace,
                "sid": sid,
                "timestamp": datetime.now().isoformat(),
            }
            self.server_events.append(event_data)

            print(f"❌ SERVER: Disconnection from {namespace} - {sid}")

        # Listen for all events in this namespace
        @self.sio_server.event(namespace=namespace)
        async def catch_all_events(event, sid, data):
            event_data = {
                "type": "event",
                "namespace": namespace,
                "event": event,
                "sid": sid,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            }
            self.server_events.append(event_data)

            print(f"📨 SERVER: Received {namespace}/{event} from {sid}")

            # Echo back to all clients in namespace
            room_name = f"{namespace.lstrip('/')}_room"
            await self.sio_server.emit(
                f"echo_{event}",
                {
                    **data,
                    "echoed_at": datetime.now().isoformat(),
                    "original_sender": sid,
                },
                room=room_name,
                namespace=namespace,
            )

    def start_server(self):
        """Start the diagnostic server in a background thread."""
        print("🚀 Starting diagnostic server...")

        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def server_main():
                await self.setup_diagnostic_server()
                runner = web.AppRunner(self.app)
                await runner.setup()
                site = web.TCPSite(runner, self.host, self.port)
                await site.start()
                self.server_running = True
                print(f"✅ Diagnostic server running on {self.server_url}")

                # Keep server running
                while self.server_running:
                    await asyncio.sleep(0.1)

            try:
                loop.run_until_complete(server_main())
            except Exception as e:
                self.errors.append(f"Server error: {e}")
                print(f"❌ Server error: {e}")

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait for server to start
        for i in range(50):  # 5 second timeout
            if self.server_running:
                break
            time.sleep(0.1)

        if not self.server_running:
            self.errors.append("Server failed to start within timeout")
            return False

        return True

    def stop_server(self):
        """Stop the diagnostic server."""
        self.server_running = False
        if hasattr(self, "server_thread"):
            self.server_thread.join(timeout=5)

    def setup_hook_client(self):
        """Setup hook handler simulation client."""
        print("🎣 Setting up hook handler simulation client...")

        try:
            self.hook_client = socketio.Client(
                reconnection=True,
                reconnection_attempts=3,
                reconnection_delay=0.5,
                logger=False,
                engineio_logger=False,
            )

            @self.hook_client.event
            def connect():
                self.hook_client_connected = True
                print("✅ HOOK CLIENT: Connected to server")

            @self.hook_client.event
            def disconnect():
                self.hook_client_connected = False
                print("❌ HOOK CLIENT: Disconnected from server")

            @self.hook_client.event
            def connect_error(data):
                self.errors.append(f"Hook client connection error: {data}")
                print(f"🚨 HOOK CLIENT: Connection error - {data}")

            # Connect to hook and system namespaces (same as real hook handler)
            auth_data = {"token": "dev-token"}
            self.hook_client.connect(
                self.server_url,
                auth=auth_data,
                namespaces=["/hook", "/system"],
                wait=True,
                wait_timeout=10,
            )

            return True

        except Exception as e:
            self.errors.append(f"Hook client setup error: {e}")
            print(f"❌ HOOK CLIENT: Setup error - {e}")
            return False

    def setup_dashboard_clients(self):
        """Setup multiple dashboard simulation clients."""
        print("📊 Setting up dashboard simulation clients...")

        namespaces = [
            "/system",
            "/session",
            "/claude",
            "/agent",
            "/hook",
            "/todo",
            "/memory",
            "/log",
        ]

        for namespace in namespaces:
            try:
                client = socketio.Client(
                    reconnection=True,
                    reconnection_attempts=3,
                    reconnection_delay=0.5,
                    logger=False,
                    engineio_logger=False,
                )

                # Track events for this namespace
                if namespace not in self.events_received:
                    self.events_received[namespace] = []

                @client.event
                def connect():
                    self.dashboard_clients_connected[namespace] = True
                    print(f"✅ DASHBOARD CLIENT: Connected to {namespace}")

                @client.event
                def disconnect():
                    self.dashboard_clients_connected[namespace] = False
                    print(f"❌ DASHBOARD CLIENT: Disconnected from {namespace}")

                # Listen for all events in this namespace
                def make_event_handler(ns):
                    def handle_any_event(event, data):
                        event_info = {
                            "namespace": ns,
                            "event": event,
                            "data": data,
                            "received_at": datetime.now().isoformat(),
                        }
                        self.events_received[ns].append(event_info)
                        print(f"📥 DASHBOARD CLIENT: Received {ns}/{event}")

                    return handle_any_event

                client.on("*", make_event_handler(namespace), namespace=namespace)

                # Connect with auth
                auth_data = {"token": "dev-token"}
                client.connect(
                    self.server_url + namespace,
                    auth=auth_data,
                    wait=True,
                    wait_timeout=10,
                )

                self.dashboard_clients[namespace] = client

            except Exception as e:
                self.errors.append(f"Dashboard client setup error for {namespace}: {e}")
                print(f"❌ DASHBOARD CLIENT: Setup error for {namespace} - {e}")

        connected_count = sum(
            1 for connected in self.dashboard_clients_connected.values() if connected
        )
        print(
            f"✅ Dashboard clients setup: {connected_count}/{len(namespaces)} connected"
        )

        return connected_count > 0

    def send_test_events(self, count: int = 10):
        """Send test events from hook client."""
        print(f"📤 Sending {count} test events from hook client...")

        if not self.hook_client or not self.hook_client_connected:
            self.errors.append("Hook client not connected - cannot send events")
            return

        event_types = [
            {
                "namespace": "/hook",
                "event": "user_prompt",
                "data_template": {
                    "prompt": "Test user prompt #{i}",
                    "session_id": "diagnostic-session",
                    "timestamp": None,
                },
            },
            {
                "namespace": "/hook",
                "event": "pre_tool",
                "data_template": {
                    "tool_name": "DiagnosticTool#{i}",
                    "session_id": "diagnostic-session",
                    "timestamp": None,
                },
            },
            {
                "namespace": "/hook",
                "event": "post_tool",
                "data_template": {
                    "tool_name": "DiagnosticTool#{i}",
                    "exit_code": 0,
                    "session_id": "diagnostic-session",
                    "timestamp": None,
                },
            },
        ]

        for i in range(count):
            for event_config in event_types:
                try:
                    # Prepare event data
                    data = event_config["data_template"].copy()
                    for key, value in data.items():
                        if isinstance(value, str) and "#{i}" in value:
                            data[key] = value.replace("#{i}", str(i + 1))
                    data["timestamp"] = datetime.now().isoformat()

                    # Record timing
                    send_time = time.time()

                    # Send event
                    namespace = event_config["namespace"]
                    event = event_config["event"]

                    self.hook_client.emit(event, data, namespace=namespace)
                    self.events_sent += 1

                    # Record timing data
                    self.timing_data.append(
                        {
                            "event_id": f"{namespace}/{event}_{i+1}",
                            "send_time": send_time,
                            "data": data,
                        }
                    )

                    print(f"📤 Sent {namespace}/{event} #{i+1}")
                    time.sleep(0.1)  # Small delay between events

                except Exception as e:
                    self.errors.append(f"Failed to send event {i}: {e}")
                    print(f"❌ Failed to send event {i}: {e}")

    def analyze_results(self):
        """Analyze test results and provide diagnostic summary."""
        print("\n" + "=" * 80)
        print("📊 END-TO-END DIAGNOSTIC ANALYSIS")
        print("=" * 80)

        # Connection analysis
        print("🔗 SERVER CONNECTIONS:")
        print(f"   Server running: {self.server_running}")
        print(f"   Hook client connected: {self.hook_client_connected}")
        print(
            f"   Dashboard clients connected: {len([k for k, v in self.dashboard_clients_connected.items() if v])}/{len(self.dashboard_clients)}"
        )

        # Event flow analysis
        print("\n📤 EVENT SENDING:")
        print(f"   Total events sent: {self.events_sent}")
        print(f"   Timing records: {len(self.timing_data)}")

        print("\n📥 EVENT RECEIVING:")
        total_received = sum(len(events) for events in self.events_received.values())
        print(f"   Total events received: {total_received}")

        for namespace, events in self.events_received.items():
            if events:
                print(f"   {namespace}: {len(events)} events")
                # Show event types
                event_types = set(event["event"] for event in events)
                print(f"      Event types: {', '.join(event_types)}")

        # Server-side analysis
        print("\n🖥️  SERVER-SIDE EVENTS:")
        print(f"   Total server events recorded: {len(self.server_events)}")

        event_type_counts = {}
        for event in self.server_events:
            event_type = event["type"]
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

        for event_type, count in event_type_counts.items():
            print(f"   {event_type}: {count}")

        # Timing analysis
        if self.timing_data:
            print("\n⏱️  TIMING ANALYSIS:")
            avg_response_time = "N/A (not implemented)"
            print(f"   Average response time: {avg_response_time}")

        # Error analysis
        print("\n🚨 ERRORS:")
        print(f"   Total errors: {len(self.errors)}")
        if self.errors:
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")

        # Diagnostic conclusions
        print("\n🔍 DIAGNOSTIC CONCLUSIONS:")

        if self.server_running and self.hook_client_connected:
            print("   ✅ Basic connectivity: PASS")
        else:
            print("   ❌ Basic connectivity: FAIL")

        if self.events_sent > 0 and total_received > 0:
            print("   ✅ Event flow: PASS")
        else:
            print("   ❌ Event flow: FAIL")

        if len(self.errors) == 0:
            print("   ✅ Error-free execution: PASS")
        else:
            print("   ❌ Error-free execution: FAIL")

        dashboard_connected_count = sum(
            1 for connected in self.dashboard_clients_connected.values() if connected
        )
        if (
            dashboard_connected_count >= len(self.dashboard_clients) * 0.8
        ):  # 80% threshold
            print("   ✅ Dashboard connectivity: PASS")
        else:
            print("   ❌ Dashboard connectivity: FAIL")

        print(f"\n⏰ Test completed at: {datetime.now().isoformat()}")
        test_duration = (datetime.now() - self.start_time).total_seconds()
        print(f"🕒 Total test duration: {test_duration:.2f} seconds")

    def cleanup(self):
        """Cleanup all connections and resources."""
        print("\n🧹 Cleaning up test resources...")

        # Disconnect hook client
        if self.hook_client and self.hook_client_connected:
            try:
                self.hook_client.disconnect()
            except:
                pass

        # Disconnect dashboard clients
        for namespace, client in self.dashboard_clients.items():
            try:
                if self.dashboard_clients_connected.get(namespace):
                    client.disconnect()
            except:
                pass

        # Stop server
        self.stop_server()

        print("✅ Cleanup complete")

    def run_full_test(self, event_count: int = 10):
        """Run the complete end-to-end test."""
        try:
            # Step 1: Start server
            if not self.start_server():
                print("❌ Failed to start server - aborting test")
                return False

            time.sleep(1)  # Give server time to stabilize

            # Step 2: Setup hook client
            if not self.setup_hook_client():
                print("❌ Failed to setup hook client - aborting test")
                return False

            time.sleep(0.5)

            # Step 3: Setup dashboard clients
            if not self.setup_dashboard_clients():
                print(
                    "❌ Failed to setup dashboard clients - continuing with limited test"
                )

            time.sleep(1)

            # Step 4: Send test events
            self.send_test_events(event_count)

            # Step 5: Wait for events to propagate
            print("⏳ Waiting for events to propagate...")
            time.sleep(2)

            # Step 6: Analyze results
            self.analyze_results()

            return True

        except KeyboardInterrupt:
            print("\n🛑 Test interrupted by user")
            return False
        except Exception as e:
            self.errors.append(f"Test execution error: {e}")
            print(f"❌ Test execution error: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            self.cleanup()


def main():
    """Main diagnostic function."""
    import argparse

    parser = argparse.ArgumentParser(description="End-to-End Socket.IO Diagnostic Test")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument(
        "--events", type=int, default=10, help="Number of test events to send"
    )
    args = parser.parse_args()

    test = EndToEndDiagnosticTest(args.host, args.port)
    success = test.run_full_test(args.events)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
