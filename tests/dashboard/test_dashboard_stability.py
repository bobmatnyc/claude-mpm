#!/usr/bin/env python3
"""
Claude MPM Dashboard Connection Stability Test

This script tests the stability of WebSocket connections to the Claude MPM dashboard
for the specified duration using browser automation with Playwright.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from playwright.async_api import (
    BrowserContext,
    ConsoleMessage,
    Page,
    Request,
    Response,
    async_playwright,
)

# Test configuration
DASHBOARD_URL = "http://localhost:8765"
TEST_DURATION_MINUTES = 10
MULTI_TAB_TEST_DURATION_MINUTES = 5
MULTI_TAB_COUNT = 3
SCREENSHOT_DIR = Path("test_results/screenshots")
REPORT_DIR = Path("test_results")
PING_INTERVAL_MS = 45000  # 45 seconds as configured
PONG_TIMEOUT_MS = 20000  # 20 seconds as configured

# Create directories
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(REPORT_DIR / "test_log.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ConnectionMonitor:
    def __init__(self, page: Page, tab_id: str = "main"):
        self.page = page
        self.tab_id = tab_id
        self.console_messages: List[Dict[str, Any]] = []
        self.websocket_events: List[Dict[str, Any]] = []
        self.connection_events: List[Dict[str, Any]] = []
        self.disconnections = 0
        self.reconnections = 0
        self.start_time = None
        self.ping_timeouts = 0

    def start_monitoring(self):
        """Start monitoring console and network events"""
        self.start_time = datetime.now(timezone.utc)

        # Monitor console messages
        self.page.on("console", self._handle_console_message)

        # Monitor WebSocket connections
        self.page.on("websocket", self._handle_websocket)

        # Monitor network requests
        self.page.on("request", self._handle_request)
        self.page.on("response", self._handle_response)

        logger.info(
            f"[{self.tab_id}] Started connection monitoring at {self.start_time}"
        )

    def _handle_console_message(self, msg: ConsoleMessage):
        """Handle browser console messages"""
        timestamp = datetime.now(timezone.utc)
        message_data = {
            "timestamp": timestamp.isoformat(),
            "type": msg.type,
            "text": msg.text,
            "location": msg.location,
        }

        self.console_messages.append(message_data)

        # Check for specific connection events
        text_lower = msg.text.lower()
        if "socket.io" in text_lower or "websocket" in text_lower:
            logger.info(f"[{self.tab_id}] Socket.IO event: {msg.text}")

        if "ping timeout" in text_lower:
            self.ping_timeouts += 1
            logger.warning(f"[{self.tab_id}] PING TIMEOUT detected: {msg.text}")

        if "disconnect" in text_lower:
            self.disconnections += 1
            self.connection_events.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "type": "disconnect",
                    "message": msg.text,
                }
            )
            logger.warning(f"[{self.tab_id}] DISCONNECT detected: {msg.text}")

        if "reconnect" in text_lower or "connect" in text_lower:
            if "disconnect" not in text_lower:  # Avoid double counting
                self.reconnections += 1
                self.connection_events.append(
                    {
                        "timestamp": timestamp.isoformat(),
                        "type": "reconnect",
                        "message": msg.text,
                    }
                )
                logger.info(f"[{self.tab_id}] RECONNECT detected: {msg.text}")

    def _handle_websocket(self, ws):
        """Handle WebSocket connections"""
        timestamp = datetime.now(timezone.utc)

        def on_close():
            self.websocket_events.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "type": "websocket_close",
                    "url": ws.url,
                }
            )
            logger.warning(f"[{self.tab_id}] WebSocket closed: {ws.url}")

        def on_frame_sent(payload):
            self.websocket_events.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "type": "frame_sent",
                    "payload": str(payload)[:100],  # Truncate long payloads
                }
            )

        def on_frame_received(payload):
            self.websocket_events.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "type": "frame_received",
                    "payload": str(payload)[:100],  # Truncate long payloads
                }
            )

        ws.on("close", on_close)
        ws.on("framesent", on_frame_sent)
        ws.on("framereceived", on_frame_received)

        logger.info(f"[{self.tab_id}] WebSocket opened: {ws.url}")

        self.websocket_events.append(
            {
                "timestamp": timestamp.isoformat(),
                "type": "websocket_open",
                "url": ws.url,
            }
        )

    def _handle_request(self, request: Request):
        """Handle network requests"""
        if (
            request.url.startswith("ws://")
            or request.url.startswith("wss://")
            or "socket.io" in request.url
        ):
            logger.debug(f"[{self.tab_id}] WebSocket request: {request.url}")

    def _handle_response(self, response: Response):
        """Handle network responses"""
        if "socket.io" in response.url or response.status == 101:  # WebSocket upgrade
            logger.debug(
                f"[{self.tab_id}] WebSocket response: {response.status} - {response.url}"
            )

    async def take_screenshot(self, name: str):
        """Take a screenshot of the current page"""
        screenshot_path = (
            SCREENSHOT_DIR / f"{self.tab_id}_{name}_{int(time.time())}.png"
        )
        await self.page.screenshot(path=screenshot_path, full_page=True)
        logger.info(f"[{self.tab_id}] Screenshot saved: {screenshot_path}")
        return screenshot_path

    def get_duration(self) -> timedelta:
        """Get the monitoring duration"""
        if self.start_time:
            return datetime.now(timezone.utc) - self.start_time
        return timedelta(0)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        duration = self.get_duration()
        return {
            "tab_id": self.tab_id,
            "duration_seconds": duration.total_seconds(),
            "disconnections": self.disconnections,
            "reconnections": self.reconnections,
            "ping_timeouts": self.ping_timeouts,
            "console_messages_count": len(self.console_messages),
            "websocket_events_count": len(self.websocket_events),
            "connection_events_count": len(self.connection_events),
        }


async def test_single_tab_stability(
    browser_context: BrowserContext, duration_minutes: int
) -> ConnectionMonitor:
    """Test connection stability in a single tab"""
    logger.info(f"Starting single tab stability test for {duration_minutes} minutes")

    page = await browser_context.new_page()
    monitor = ConnectionMonitor(page, "single_tab")
    monitor.start_monitoring()

    try:
        # Navigate to dashboard
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state("networkidle")

        # Take initial screenshot
        await monitor.take_screenshot("initial_load")

        # Wait for Socket.IO connection to establish
        await asyncio.sleep(5)

        # Take screenshot after connection
        await monitor.take_screenshot("after_connection")

        # Monitor for specified duration
        end_time = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        check_interval = 30  # Check every 30 seconds

        while datetime.now(timezone.utc) < end_time:
            remaining = end_time - datetime.now(timezone.utc)
            logger.info(
                f"[single_tab] Monitoring... {remaining.total_seconds():.0f} seconds remaining"
            )

            # Check if page is still responsive
            try:
                await page.evaluate("() => window.location.href")
            except Exception as e:
                logger.error(f"[single_tab] Page unresponsive: {e}")
                await monitor.take_screenshot("page_unresponsive")

            await asyncio.sleep(min(check_interval, remaining.total_seconds()))

        # Take final screenshot
        await monitor.take_screenshot("final")

    except Exception as e:
        logger.error(f"[single_tab] Error during test: {e}")
        await monitor.take_screenshot("error")
    finally:
        await page.close()

    return monitor


async def test_multi_tab_stability(
    browser_context: BrowserContext, tab_count: int, duration_minutes: int
) -> List[ConnectionMonitor]:
    """Test connection stability across multiple tabs"""
    logger.info(
        f"Starting multi-tab stability test with {tab_count} tabs for {duration_minutes} minutes"
    )

    monitors = []
    pages = []

    try:
        # Create multiple tabs
        for i in range(tab_count):
            page = await browser_context.new_page()
            monitor = ConnectionMonitor(page, f"tab_{i+1}")
            monitor.start_monitoring()

            await page.goto(DASHBOARD_URL)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # Stagger the connections

            await monitor.take_screenshot("initial")

            pages.append(page)
            monitors.append(monitor)

            logger.info(f"[tab_{i+1}] Created and connected")

        # Monitor all tabs for specified duration
        end_time = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        check_interval = 30

        while datetime.now(timezone.utc) < end_time:
            remaining = end_time - datetime.now(timezone.utc)
            logger.info(
                f"[multi_tab] Monitoring {tab_count} tabs... {remaining.total_seconds():.0f} seconds remaining"
            )

            # Check each tab is still responsive
            for i, page in enumerate(pages):
                try:
                    await page.evaluate("() => window.location.href")
                except Exception as e:
                    logger.error(f"[tab_{i+1}] Page unresponsive: {e}")
                    await monitors[i].take_screenshot("unresponsive")

            await asyncio.sleep(min(check_interval, remaining.total_seconds()))

        # Take final screenshots
        for i, monitor in enumerate(monitors):
            await monitor.take_screenshot("final")

    except Exception as e:
        logger.error(f"[multi_tab] Error during test: {e}")
    finally:
        # Close all pages
        for page in pages:
            try:
                await page.close()
            except Exception as e:
                logger.error(f"Error closing page: {e}")

    return monitors


async def generate_report(
    single_monitor: ConnectionMonitor, multi_monitors: List[ConnectionMonitor]
):
    """Generate comprehensive test report"""
    logger.info("Generating comprehensive test report...")

    report = {
        "test_metadata": {
            "dashboard_url": DASHBOARD_URL,
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "single_tab_duration_minutes": TEST_DURATION_MINUTES,
            "multi_tab_duration_minutes": MULTI_TAB_TEST_DURATION_MINUTES,
            "multi_tab_count": MULTI_TAB_COUNT,
            "ping_interval_ms": PING_INTERVAL_MS,
            "pong_timeout_ms": PONG_TIMEOUT_MS,
        },
        "single_tab_test": {
            "stats": single_monitor.get_stats(),
            "console_messages": single_monitor.console_messages,
            "websocket_events": single_monitor.websocket_events,
            "connection_events": single_monitor.connection_events,
        },
        "multi_tab_test": {
            "stats": [monitor.get_stats() for monitor in multi_monitors],
            "total_disconnections": sum(m.disconnections for m in multi_monitors),
            "total_reconnections": sum(m.reconnections for m in multi_monitors),
            "total_ping_timeouts": sum(m.ping_timeouts for m in multi_monitors),
            "all_console_messages": [
                {"tab_id": m.tab_id, "messages": m.console_messages}
                for m in multi_monitors
            ],
            "all_websocket_events": [
                {"tab_id": m.tab_id, "events": m.websocket_events}
                for m in multi_monitors
            ],
            "all_connection_events": [
                {"tab_id": m.tab_id, "events": m.connection_events}
                for m in multi_monitors
            ],
        },
    }

    # Save detailed JSON report
    report_path = REPORT_DIR / f"dashboard_stability_report_{int(time.time())}.json"
    with report_path.open("w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"Detailed report saved to: {report_path}")

    # Generate summary report
    summary_path = REPORT_DIR / f"dashboard_stability_summary_{int(time.time())}.txt"
    with summary_path.open("w") as f:
        f.write("Claude MPM Dashboard Connection Stability Test Results\n")
        f.write("=" * 60 + "\n\n")

        f.write(
            f"Test Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        f.write(f"Dashboard URL: {DASHBOARD_URL}\n\n")

        # Single tab results
        single_stats = single_monitor.get_stats()
        f.write("SINGLE TAB TEST RESULTS:\n")
        f.write("-" * 30 + "\n")
        f.write(
            f"Duration: {single_stats['duration_seconds']:.1f} seconds ({single_stats['duration_seconds']/60:.1f} minutes)\n"
        )
        f.write(f"Disconnections: {single_stats['disconnections']}\n")
        f.write(f"Reconnections: {single_stats['reconnections']}\n")
        f.write(f"Ping Timeouts: {single_stats['ping_timeouts']}\n")
        f.write(f"Console Messages: {single_stats['console_messages_count']}\n")
        f.write(f"WebSocket Events: {single_stats['websocket_events_count']}\n\n")

        # Multi-tab results
        f.write("MULTI-TAB TEST RESULTS:\n")
        f.write("-" * 30 + "\n")
        f.write(f"Number of tabs: {len(multi_monitors)}\n")

        total_disconnections = sum(m.disconnections for m in multi_monitors)
        total_reconnections = sum(m.reconnections for m in multi_monitors)
        total_ping_timeouts = sum(m.ping_timeouts for m in multi_monitors)

        f.write(f"Total Disconnections: {total_disconnections}\n")
        f.write(f"Total Reconnections: {total_reconnections}\n")
        f.write(f"Total Ping Timeouts: {total_ping_timeouts}\n\n")

        for i, monitor in enumerate(multi_monitors):
            stats = monitor.get_stats()
            f.write(f"Tab {i+1} Stats:\n")
            f.write(f"  Duration: {stats['duration_seconds']:.1f} seconds\n")
            f.write(f"  Disconnections: {stats['disconnections']}\n")
            f.write(f"  Reconnections: {stats['reconnections']}\n")
            f.write(f"  Ping Timeouts: {stats['ping_timeouts']}\n\n")

        # Overall assessment
        f.write("OVERALL ASSESSMENT:\n")
        f.write("-" * 30 + "\n")

        total_test_duration = single_stats["duration_seconds"] + (
            multi_monitors[0].get_stats()["duration_seconds"] if multi_monitors else 0
        )
        all_disconnections = single_stats["disconnections"] + total_disconnections
        all_ping_timeouts = single_stats["ping_timeouts"] + total_ping_timeouts

        if all_disconnections == 0 and all_ping_timeouts == 0:
            f.write("✅ PASS: No disconnections or ping timeouts detected\n")
            f.write("✅ Connection stability: EXCELLENT\n")
        elif all_disconnections <= 2 and all_ping_timeouts <= 1:
            f.write("⚠️  MARGINAL: Minor connection issues detected\n")
            f.write("⚠️  Connection stability: ACCEPTABLE\n")
        else:
            f.write("❌ FAIL: Significant connection stability issues\n")
            f.write("❌ Connection stability: POOR\n")

        f.write(
            f"\nTotal test duration: {total_test_duration:.1f} seconds ({total_test_duration/60:.1f} minutes)\n"
        )
        f.write(f"Screenshots saved to: {SCREENSHOT_DIR}\n")
        f.write(f"Detailed report: {report_path}\n")

    logger.info(f"Summary report saved to: {summary_path}")

    # Print results to console
    print("\n" + "=" * 60)
    print("CLAUDE MPM DASHBOARD STABILITY TEST RESULTS")
    print("=" * 60)
    print(
        f"Test completed at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print()

    print("SINGLE TAB TEST:")
    print(
        f"  Duration: {single_stats['duration_seconds']:.1f} seconds ({single_stats['duration_seconds']/60:.1f} minutes)"
    )
    print(f"  Disconnections: {single_stats['disconnections']}")
    print(f"  Reconnections: {single_stats['reconnections']}")
    print(f"  Ping Timeouts: {single_stats['ping_timeouts']}")
    print()

    print(f"MULTI-TAB TEST ({len(multi_monitors)} tabs):")
    print(f"  Total Disconnections: {total_disconnections}")
    print(f"  Total Reconnections: {total_reconnections}")
    print(f"  Total Ping Timeouts: {total_ping_timeouts}")
    print()

    if all_disconnections == 0 and all_ping_timeouts == 0:
        print("✅ OVERALL RESULT: PASS - Excellent connection stability")
    elif all_disconnections <= 2 and all_ping_timeouts <= 1:
        print("⚠️  OVERALL RESULT: MARGINAL - Acceptable with minor issues")
    else:
        print("❌ OVERALL RESULT: FAIL - Poor connection stability")

    print(f"\nDetailed reports saved to: {REPORT_DIR}")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}")
    print("=" * 60)


async def main():
    """Main test execution"""
    logger.info("Starting Claude MPM Dashboard Connection Stability Test")

    async with async_playwright() as p:
        # Launch browser with appropriate settings
        browser = await p.chromium.launch(
            headless=False,  # Show browser for visibility
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
                "--allow-running-insecure-content",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )

        try:
            # Run single tab test
            logger.info(f"Phase 1: Single tab test for {TEST_DURATION_MINUTES} minutes")
            single_monitor = await test_single_tab_stability(
                context, TEST_DURATION_MINUTES
            )

            # Short break between tests
            await asyncio.sleep(5)

            # Run multi-tab test
            logger.info(
                f"Phase 2: Multi-tab test with {MULTI_TAB_COUNT} tabs for {MULTI_TAB_TEST_DURATION_MINUTES} minutes"
            )
            multi_monitors = await test_multi_tab_stability(
                context, MULTI_TAB_COUNT, MULTI_TAB_TEST_DURATION_MINUTES
            )

            # Generate comprehensive report
            await generate_report(single_monitor, multi_monitors)

        except Exception as e:
            logger.error(f"Test execution error: {e}")
        finally:
            await browser.close()

    logger.info("Test execution completed")


if __name__ == "__main__":
    asyncio.run(main())
