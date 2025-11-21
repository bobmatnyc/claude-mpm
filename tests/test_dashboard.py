#!/usr/bin/env python3
"""
Dashboard Verification Test Script
Tests all tabs and captures console logs
"""

import asyncio
import json

from playwright.async_api import async_playwright


async def test_dashboard():
    """Test all dashboard tabs and capture console output"""
    results = {"connection": {}, "console_logs": [], "tabs": {}, "errors": []}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Capture console messages
        def handle_console(msg):
            log_entry = {"type": msg.type, "text": msg.text, "location": msg.location}
            results["console_logs"].append(log_entry)
            print(f"[CONSOLE {msg.type.upper()}] {msg.text}")

        page.on("console", handle_console)

        # Navigate to dashboard
        print("\n=== ACCESSING DASHBOARD ===")
        try:
            response = await page.goto(
                "http://localhost:5001", wait_until="networkidle"
            )
            results["connection"]["status"] = response.status
            results["connection"]["success"] = response.ok
            print(f"✓ Page loaded: HTTP {response.status}")
        except Exception as e:
            results["errors"].append(f"Failed to load page: {e!s}")
            print(f"✗ Failed to load: {e}")
            return results

        # Wait for Socket.IO connection
        print("\n=== WAITING FOR SOCKET.IO CONNECTION ===")
        await asyncio.sleep(3)  # Wait for Socket.IO to connect and receive events

        # Test each tab
        tabs = ["Events", "Agents", "Tools", "Files", "Activity"]

        for tab_name in tabs:
            print(f"\n=== TESTING {tab_name.upper()} TAB ===")
            try:
                # Click the tab
                await page.click(f'button:has-text("{tab_name}")')
                await asyncio.sleep(1)  # Wait for tab content to render

                # Take screenshot
                screenshot_path = f"/Users/masa/Projects/claude-mpm/dashboard_{tab_name.lower()}_tab.png"
                await page.screenshot(path=screenshot_path)
                print(f"✓ Screenshot saved: {screenshot_path}")

                # Get tab content
                content = await page.content()

                # Check for empty state or data
                has_data = "No events" not in content and "No data" not in content

                results["tabs"][tab_name] = {
                    "screenshot": screenshot_path,
                    "has_data": has_data,
                    "timestamp": await page.evaluate("new Date().toISOString()"),
                }

                print(f"✓ {tab_name} tab: {'HAS DATA' if has_data else 'EMPTY'}")

            except Exception as e:
                results["tabs"][tab_name] = {"error": str(e)}
                results["errors"].append(f"{tab_name} tab error: {e!s}")
                print(f"✗ {tab_name} tab error: {e}")

        # Wait a bit more to capture any delayed console messages
        await asyncio.sleep(2)

        # Save results
        with open(
            "/Users/masa/Projects/claude-mpm/dashboard_test_results.json", "w"
        ) as f:
            json.dump(results, f, indent=2)

        print("\n=== TEST COMPLETE ===")
        print(f"Total console logs captured: {len(results['console_logs'])}")
        print(f"Tabs tested: {len(results['tabs'])}")
        print(f"Errors encountered: {len(results['errors'])}")

        await browser.close()

    return results


if __name__ == "__main__":
    results = asyncio.run(test_dashboard())

    # Print summary
    print("\n" + "=" * 60)
    print("DASHBOARD VERIFICATION SUMMARY")
    print("=" * 60)

    # Connection
    print(f"\n✓ Connection: HTTP {results['connection'].get('status', 'N/A')}")

    # Console logs summary
    log_types = {}
    for log in results["console_logs"]:
        log_types[log["type"]] = log_types.get(log["type"], 0) + 1

    print(f"\nConsole Logs ({len(results['console_logs'])} total):")
    for log_type, count in sorted(log_types.items()):
        print(f"  - {log_type}: {count}")

    # Tabs summary
    print("\nTabs Status:")
    for tab_name, tab_data in results["tabs"].items():
        if "error" in tab_data:
            print(f"  ✗ {tab_name}: ERROR - {tab_data['error']}")
        else:
            status = "HAS DATA" if tab_data["has_data"] else "EMPTY"
            print(f"  {'✓' if tab_data['has_data'] else '○'} {tab_name}: {status}")

    # Errors
    if results["errors"]:
        print(f"\n✗ Errors ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"  - {error}")
    else:
        print("\n✓ No errors encountered")

    print("\nResults saved to: dashboard_test_results.json")
    print("Screenshots saved to: dashboard_*_tab.png")
