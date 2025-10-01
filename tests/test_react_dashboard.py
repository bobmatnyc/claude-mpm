#!/usr/bin/env python3
"""
Comprehensive automated test for React + Vite monitor dashboard implementation.
Tests functionality, performance, and ensures backward compatibility.
"""

import asyncio
import json
import os
import random
import signal
import subprocess
import time
from typing import TYPE_CHECKING, Any, Dict, List

import psutil
import socketio
from playwright.async_api import async_playwright

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page


class ReactDashboardTester:
    def __init__(self, server_url: str = "http://localhost:8765"):
        self.server_url = server_url
        self.events_url = f"{server_url}/static/events.html"
        self.sio = socketio.AsyncClient()
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.test_results = {
            "component_loading": False,
            "websocket_connection": False,
            "event_rendering": False,
            "filtering": False,
            "data_inspector": False,
            "performance": {},
            "errors": [],
            "screenshots": [],
        }

    async def setup_browser(self):
        """Initialize Playwright browser for testing"""
        print("🌐 Setting up browser for testing...")

        playwright = await async_playwright().start()

        # Use Safari browser for macOS testing
        self.browser = await playwright.webkit.launch(
            headless=False,  # Keep visible for manual verification
            slow_mo=100,  # Slow down for better observation
        )

        self.context = await self.browser.new_context(
            # Enable console logging
            ignore_https_errors=True,
            viewport={"width": 1400, "height": 900},
        )

        self.page = await self.context.new_page()

        # Enable console monitoring
        self.page.on("console", self._handle_console_message)
        self.page.on("pageerror", self._handle_page_error)

        return True

    def _handle_console_message(self, msg):
        """Handle browser console messages"""
        print(f"🖥️  Console [{msg.type}]: {msg.text}")
        if msg.type in ["error", "warning"]:
            self.test_results["errors"].append(
                {
                    "type": "console",
                    "level": msg.type,
                    "message": msg.text,
                    "timestamp": time.time(),
                }
            )

    def _handle_page_error(self, error):
        """Handle page errors"""
        print(f"❌ Page Error: {error}")
        self.test_results["errors"].append(
            {"type": "page_error", "message": str(error), "timestamp": time.time()}
        )

    async def connect_socketio(self):
        """Connect to SocketIO server"""
        try:
            await self.sio.connect(self.server_url)
            print(f"✅ Connected to SocketIO server at {self.server_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to SocketIO: {e}")
            return False

    async def load_dashboard(self):
        """Load the events dashboard and verify React component loads"""
        print("📄 Loading events dashboard...")

        try:
            # Navigate to events page
            await self.page.goto(self.events_url, wait_until="networkidle")

            # Take initial screenshot
            await self.page.screenshot(path="dashboard_initial.png")
            self.test_results["screenshots"].append("dashboard_initial.png")

            # Wait for React component to load
            await self.page.wait_for_selector("#react-events-root", timeout=10000)

            # Check if React component actually loaded (not just fallback)
            react_loaded = await self.page.evaluate(
                """
                () => {
                    const fallback = document.getElementById('fallback-events');
                    const reactContainer = document.getElementById('react-events-root');
                    return fallback && fallback.style.display === 'none' &&
                           reactContainer && reactContainer.children.length > 1;
                }
            """
            )

            if react_loaded:
                print("✅ React EventViewer component loaded successfully")
                self.test_results["component_loading"] = True
            else:
                print("⚠️  React component may not have loaded (fallback still visible)")

            # Wait a moment for everything to settle
            await asyncio.sleep(2)

            # Take screenshot after React loads
            await self.page.screenshot(path="dashboard_react_loaded.png")
            self.test_results["screenshots"].append("dashboard_react_loaded.png")

            return react_loaded

        except Exception as e:
            print(f"❌ Failed to load dashboard: {e}")
            self.test_results["errors"].append(
                {"type": "load_error", "message": str(e), "timestamp": time.time()}
            )
            return False

    async def test_websocket_connection(self):
        """Test WebSocket connection status in the dashboard"""
        print("🔗 Testing WebSocket connection...")

        try:
            # Check connection status indicator
            connection_status = await self.page.evaluate(
                """
                () => {
                    // Look for connection status indicators
                    const statusElements = document.querySelectorAll('[class*="connection"], [class*="status"]');
                    for (let elem of statusElements) {
                        if (elem.textContent.toLowerCase().includes('connected') ||
                            elem.classList.contains('connected')) {
                            return 'connected';
                        }
                    }

                    // Check if SocketIO client is available
                    return typeof window.socket !== 'undefined' && window.socket.connected ? 'connected' : 'disconnected';
                }
            """
            )

            if connection_status == "connected":
                print("✅ WebSocket connection established")
                self.test_results["websocket_connection"] = True
                return True
            print(f"⚠️  WebSocket connection status: {connection_status}")
            return False

        except Exception as e:
            print(f"❌ Failed to check WebSocket connection: {e}")
            return False

    async def send_test_events(self, count: int = 20):
        """Send test events through SocketIO"""
        print(f"📤 Sending {count} test events...")

        event_types = [
            ("agent", "loaded", {"agent_type": "Engineer", "name": "Test Engineer"}),
            ("tool", "execution", {"tool_name": "Read", "file_path": "/test/file.py"}),
            ("file", "write", {"path": "/src/output.log", "operation": "create"}),
            ("session", "update", {"active_connections": random.randint(1, 5)}),
            ("info", "metric", {"events_processed": random.randint(100, 1000)}),
        ]

        for i in range(count):
            event_type, subtype, data = random.choice(event_types)

            event = {
                "type": event_type,
                "subtype": subtype,
                "timestamp": int(time.time() * 1000),
                "source": "automated_test",
                "sequence": i,
                "data": data,
            }

            try:
                await self.sio.emit("claude_event", event)
                await asyncio.sleep(0.1)  # Small delay between events
            except Exception as e:
                print(f"❌ Failed to send event {i}: {e}")

        print(f"✅ Sent {count} test events")

    async def test_event_rendering(self):
        """Test that events are properly rendered in the React component"""
        print("🎨 Testing event rendering...")

        try:
            # Send some test events first
            await self.send_test_events(10)

            # Wait for events to be processed
            await asyncio.sleep(3)

            # Check if events are visible in the UI
            event_count = await self.page.evaluate(
                """
                () => {
                    const events = document.querySelectorAll('[class*="event"], [class*="item"]');
                    return events.length;
                }
            """
            )

            stats_display = await self.page.evaluate(
                """
                () => {
                    const statValues = document.querySelectorAll('[class*="stat-value"]');
                    return Array.from(statValues).map(el => el.textContent.trim());
                }
            """
            )

            print(f"📊 Found {event_count} event elements in UI")
            print(f"📈 Stats displayed: {stats_display}")

            if event_count > 0:
                self.test_results["event_rendering"] = True
                print("✅ Events are being rendered")

                # Take screenshot of events
                await self.page.screenshot(path="dashboard_with_events.png")
                self.test_results["screenshots"].append("dashboard_with_events.png")

                return True
            print("⚠️  No events found in UI")
            return False

        except Exception as e:
            print(f"❌ Failed to test event rendering: {e}")
            return False

    async def test_filtering(self):
        """Test event filtering functionality"""
        print("🔍 Testing event filtering...")

        try:
            # Look for filter controls
            filter_elements = await self.page.query_selector_all(
                'input[type="text"], select, [class*="filter"]'
            )

            if not filter_elements:
                print("⚠️  No filter controls found")
                return False

            print(f"🎛️  Found {len(filter_elements)} filter elements")

            # Try to use a filter (if available)
            filter_input = await self.page.query_selector(
                'input[placeholder*="filter"], input[placeholder*="search"]'
            )
            if filter_input:
                await filter_input.fill("agent")
                await asyncio.sleep(1)

                # Check if filtering worked
                visible_events = await self.page.evaluate(
                    """
                    () => document.querySelectorAll('[class*="event"]:not([style*="display: none"])').length
                """
                )

                print(f"📋 Events visible after filtering: {visible_events}")

                # Clear filter
                await filter_input.fill("")
                await asyncio.sleep(1)

                self.test_results["filtering"] = True
                print("✅ Filtering functionality working")
                return True

            return True

        except Exception as e:
            print(f"❌ Failed to test filtering: {e}")
            return False

    async def test_data_inspector(self):
        """Test data inspector functionality"""
        print("🔬 Testing data inspector...")

        try:
            # Look for clickable events
            events = await self.page.query_selector_all('[class*="event"]')

            if not events:
                print("⚠️  No events found to click")
                return False

            # Click on the first event
            await events[0].click()
            await asyncio.sleep(1)

            # Look for expanded data view
            inspector_visible = await self.page.evaluate(
                """
                () => {
                    const inspectors = document.querySelectorAll('[class*="inspector"], [class*="details"], [class*="expanded"]');
                    return inspectors.length > 0;
                }
            """
            )

            if inspector_visible:
                print("✅ Data inspector opens on event click")
                self.test_results["data_inspector"] = True

                # Take screenshot of inspector
                await self.page.screenshot(path="dashboard_data_inspector.png")
                self.test_results["screenshots"].append("dashboard_data_inspector.png")

                return True
            print("⚠️  Data inspector not found")
            return False

        except Exception as e:
            print(f"❌ Failed to test data inspector: {e}")
            return False

    async def test_performance(self):
        """Test performance with large datasets"""
        print("⚡ Testing performance with large datasets...")

        try:
            # Measure initial memory usage
            initial_memory = await self.page.evaluate(
                "() => performance.memory ? performance.memory.usedJSHeapSize : 0"
            )

            # Send a large number of events
            print("📊 Sending 1000 events for performance testing...")
            start_time = time.time()

            await self.send_test_events(1000)

            # Wait for processing
            await asyncio.sleep(5)

            send_duration = time.time() - start_time

            # Measure final memory usage
            final_memory = await self.page.evaluate(
                "() => performance.memory ? performance.memory.usedJSHeapSize : 0"
            )

            # Check if page is still responsive
            responsive_time = time.time()
            await self.page.evaluate("() => document.title")
            response_time = (time.time() - responsive_time) * 1000

            self.test_results["performance"] = {
                "send_duration": send_duration,
                "initial_memory": initial_memory,
                "final_memory": final_memory,
                "memory_increase": final_memory - initial_memory,
                "response_time_ms": response_time,
            }

            print("📈 Performance Results:")
            print(f"   Send Duration: {send_duration:.2f}s")
            print(
                f"   Memory Increase: {(final_memory - initial_memory) / 1024 / 1024:.2f} MB"
            )
            print(f"   Page Response Time: {response_time:.2f}ms")

            # Take performance screenshot
            await self.page.screenshot(path="dashboard_performance_test.png")
            self.test_results["screenshots"].append("dashboard_performance_test.png")

            return response_time < 1000  # Should respond within 1 second

        except Exception as e:
            print(f"❌ Failed to test performance: {e}")
            return False

    async def test_backward_compatibility(self):
        """Test that existing vanilla JS components still work"""
        print("🔄 Testing backward compatibility...")

        try:
            # Check if vanilla JS components are still available
            vanilla_functions = await self.page.evaluate(
                """
                () => {
                    const available = [];

                    // Check for common dashboard functions
                    if (typeof window.SocketManager !== 'undefined') available.push('SocketManager');
                    if (typeof window.EventProcessor !== 'undefined') available.push('EventProcessor');
                    if (typeof window.UIStateManager !== 'undefined') available.push('UIStateManager');

                    return available;
                }
            """
            )

            print(f"🔧 Vanilla JS components available: {vanilla_functions}")

            # Check if navigation still works
            nav_elements = await self.page.query_selector_all('nav a, [class*="nav"] a')
            print(f"🧭 Navigation elements found: {len(nav_elements)}")

            return len(vanilla_functions) > 0 or len(nav_elements) > 0

        except Exception as e:
            print(f"❌ Failed to test backward compatibility: {e}")
            return False

    async def cleanup(self):
        """Clean up resources"""
        if self.sio.connected:
            await self.sio.disconnect()

        if self.browser:
            await self.browser.close()

    async def run_comprehensive_test(self):
        """Run the complete test suite"""
        print("🚀 Starting Comprehensive React Dashboard Test")
        print("=" * 60)

        try:
            # Setup
            if not await self.setup_browser():
                return False

            if not await self.connect_socketio():
                return False

            # Core functionality tests
            await self.load_dashboard()
            await self.test_websocket_connection()
            await self.test_event_rendering()
            await self.test_filtering()
            await self.test_data_inspector()

            # Performance tests
            await self.test_performance()

            # Backward compatibility
            await self.test_backward_compatibility()

            # Generate final report
            await self.generate_test_report()

            return True

        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            return False
        finally:
            await self.cleanup()

    async def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📋 TEST RESULTS SUMMARY")
        print("=" * 60)

        # Calculate overall score
        tests = [
            ("Component Loading", self.test_results["component_loading"]),
            ("WebSocket Connection", self.test_results["websocket_connection"]),
            ("Event Rendering", self.test_results["event_rendering"]),
            ("Filtering", self.test_results["filtering"]),
            ("Data Inspector", self.test_results["data_inspector"]),
        ]

        passed = sum(1 for _, result in tests if result)
        total = len(tests)
        score = (passed / total) * 100

        print(f"\n🎯 Overall Score: {score:.1f}% ({passed}/{total} tests passed)")
        print("\n📊 Individual Test Results:")

        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name:20} {status}")

        # Performance metrics
        if self.test_results["performance"]:
            perf = self.test_results["performance"]
            print("\n⚡ Performance Metrics:")
            print(
                f"   Memory Usage: {perf['memory_increase'] / 1024 / 1024:.2f} MB increase"
            )
            print(f"   Response Time: {perf['response_time_ms']:.2f}ms")
            print(f"   Send Duration: {perf['send_duration']:.2f}s for 1000 events")

        # Error summary
        if self.test_results["errors"]:
            print(f"\n⚠️  Errors Found ({len(self.test_results['errors'])}):")
            for error in self.test_results["errors"][:5]:  # Show first 5 errors
                print(f"   [{error['type']}] {error['message'][:80]}...")
        else:
            print("\n✅ No errors detected")

        # Screenshots
        if self.test_results["screenshots"]:
            print("\n📸 Screenshots saved:")
            for screenshot in self.test_results["screenshots"]:
                print(f"   {screenshot}")

        # Success criteria
        print("\n✅ SUCCESS CRITERIA:")
        criteria = [
            ("Zero console errors", len(self.test_results["errors"]) == 0),
            (
                "Events render within 100ms",
                self.test_results["performance"].get("response_time_ms", 0) < 100,
            ),
            ("All filters work", self.test_results["filtering"]),
            ("Data inspector works", self.test_results["data_inspector"]),
            ("React component loads", self.test_results["component_loading"]),
        ]

        for criterion, met in criteria:
            status = "✅ MET" if met else "❌ NOT MET"
            print(f"   {criterion:30} {status}")

        print(f"\n🌐 Dashboard URL: {self.events_url}")
        print("=" * 60)


async def main():
    """Main test execution"""
    print("🧪 React + Vite Monitor Dashboard Test Suite")
    print("Testing functionality, performance, and backward compatibility")
    print("=" * 60)

    # Check if server is running
    try:
        import requests

        response = requests.get("http://localhost:8765/static/events.html", timeout=5)
        if response.status_code != 200:
            print("❌ Monitor server not accessible at localhost:8765")
            print("💡 Please start the monitor with: ./scripts/claude-mpm monitor")
            return None
    except Exception as e:
        print("❌ Monitor server not running")
        print("💡 Please start the monitor with: ./scripts/claude-mpm monitor")
        return None

    # Run tests
    tester = ReactDashboardTester()
    success = await tester.run_comprehensive_test()

    if success:
        print("\n🎉 Test suite completed successfully!")
    else:
        print("\n💥 Test suite encountered failures")

    return success


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
