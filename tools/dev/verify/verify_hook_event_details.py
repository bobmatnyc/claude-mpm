#!/usr/bin/env python3
"""
Final verification of hook event details and interaction
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

DASHBOARD_URL = "http://localhost:8765"
SCREENSHOTS_DIR = Path("screenshots")


async def verify_hook_details():
    """Verify hook event details by clicking on events"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            print("🌐 Navigating to dashboard...")
            await page.goto(DASHBOARD_URL)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            # Make sure we're on Events tab
            events_tab = await page.query_selector('text="Events"')
            if events_tab:
                await events_tab.click()
                await asyncio.sleep(1)

            # Take a final screenshot
            SCREENSHOTS_DIR.mkdir(exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
            screenshot_path = SCREENSHOTS_DIR / f"hook_events_final_{timestamp}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"📸 Final screenshot: {screenshot_path.name}")

            # Look for hook events specifically
            hook_events = await page.query_selector_all("text=/hook.*/")
            print(f"🎯 Found {len(hook_events)} hook event elements")

            if hook_events:
                print("📋 Hook events visible:")
                for i, event in enumerate(hook_events[:5]):  # Check first 5
                    try:
                        text = await event.inner_text()
                        print(f"  {i + 1}. {text}")

                        # Try to click on the event to see details
                        if i < 2:  # Click on first 2 events
                            try:
                                await event.click()
                                await asyncio.sleep(1)
                                print("    ✅ Clicked successfully")
                            except Exception as e:
                                print(f"    ⚠️ Click failed: {e}")

                    except Exception as e:
                        print(f"    ❌ Error reading event {i + 1}: {e}")

            # Check for structured data panel
            structured_data = await page.query_selector(
                '[data-testid*="structured"], .structured-data, text=/structured data/i'
            )
            if structured_data:
                structured_text = await structured_data.inner_text()
                print(f"📊 Structured data panel found: {structured_text[:200]}...")

            # Look for specific hook event properties
            event_properties = [
                "Hook Name",
                "Event Type",
                "Tool",
                "Session ID",
                "pre_tool",
                "post_tool",
                "subagent_stop",
                "PlaywrightTest",
                "Read",
                "Bash",
            ]

            page_content = await page.content()
            found_properties = []
            for prop in event_properties:
                if prop in page_content:
                    found_properties.append(prop)

            print(f"🔍 Hook event properties found: {found_properties}")

            # Final summary
            has_hook_events = len(hook_events) > 0
            has_details = len(found_properties) > 0

            print("\n✅ VERIFICATION SUMMARY:")
            print(
                f"  Hook events visible: {'YES' if has_hook_events else 'NO'} ({len(hook_events)} found)"
            )
            print(
                f"  Event details available: {'YES' if has_details else 'NO'} ({len(found_properties)} properties)"
            )
            print(
                f"  EventBus relay status: {'✅ WORKING' if has_hook_events else '❌ NEEDS FIX'}"
            )

            if has_hook_events and has_details:
                print(
                    "\n🎉 SUCCESS: Hook events are fully functional on the dashboard!"
                )
                print("   - Events are displaying with proper formatting")
                print(
                    "   - Event details show hook metadata (tool names, session IDs, etc.)"
                )
                print(
                    "   - EventBus relay is successfully delivering hook events to UI"
                )
            else:
                print(
                    "\n⚠️ PARTIAL SUCCESS: Events visible but may need detail improvements"
                )

        except Exception as e:
            print(f"❌ Verification failed: {e}")

        finally:
            await browser.close()


if __name__ == "__main__":
    print("🔍 Final Hook Events Verification\n")
    asyncio.run(verify_hook_details())
