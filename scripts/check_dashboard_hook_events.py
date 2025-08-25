#!/usr/bin/env python3
"""
Targeted check for hook events on dashboard after sending test events
"""

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

DASHBOARD_URL = "http://localhost:8765"
SCREENSHOTS_DIR = Path("screenshots")


async def capture_dashboard_state(browser_context):
    """Capture current dashboard state and analyze for hook events"""
    page = await browser_context.new_page()

    try:
        print(f"🌐 Navigating to dashboard: {DASHBOARD_URL}")
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Take screenshot
        SCREENSHOTS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
        screenshot_path = SCREENSHOTS_DIR / f"hook_events_check_{timestamp}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"📸 Screenshot: {screenshot_path.name}")

        # Get page content for analysis
        content = await page.content()

        # Look for hook events in various ways
        hook_patterns = [
            r"\[hook\]",
            r"pre_tool",
            r"post_tool",
            r"subagent_stop",
            r"hook.*pre_tool",
            r"hook.*post_tool",
            r"hook.*subagent_stop",
        ]

        found_patterns = {}
        for pattern in hook_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                found_patterns[pattern] = len(matches)

        # Try to extract event list items
        try:
            # Look for event items in the events list
            event_items = await page.query_selector_all(
                'div[class*="event"], li[class*="event"], .event-item, [data-testid*="event"]'
            )

            events_text = []
            for item in event_items[:20]:  # Check first 20 items
                try:
                    text = await item.inner_text()
                    if text.strip():
                        events_text.append(text.strip())
                except Exception:
                    continue

            print(f"\n📋 Found {len(events_text)} event items:")
            hook_events = []
            other_events = []

            for event in events_text:
                if any(
                    keyword in event.lower()
                    for keyword in ["hook", "pre_tool", "post_tool", "subagent"]
                ):
                    hook_events.append(event)
                else:
                    other_events.append(event)

            print(f"  🎯 Hook events: {len(hook_events)}")
            for event in hook_events[:5]:
                print(f"    - {event}")

            print(f"  🔄 Other events: {len(other_events)}")
            for event in other_events[:3]:
                print(f"    - {event}")

        except Exception as e:
            print(f"❌ Error extracting events: {e}")

        # Check raw content for hook indicators
        print("\n🔍 Pattern Analysis:")
        for pattern, count in found_patterns.items():
            print(f"  {pattern}: {count} matches")

        # Look specifically in the Events tab
        try:
            # Make sure we're on the Events tab
            events_tab = await page.query_selector('text="Events"')
            if events_tab:
                await events_tab.click()
                await asyncio.sleep(1)

                # Scroll to see more events
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

                # Look for hook-specific content in the events area
                events_section = await page.query_selector(
                    '[data-testid*="events"], div:has-text("Events")'
                )
                if events_section:
                    events_content = await events_section.inner_text()
                    hook_indicators = [
                        "[hook]",
                        "pre_tool",
                        "post_tool",
                        "subagent_stop",
                    ]

                    print("\n📊 Events Section Analysis:")
                    for indicator in hook_indicators:
                        count = events_content.lower().count(indicator.lower())
                        print(f"  {indicator}: {count} occurrences")

        except Exception as e:
            print(f"❌ Error checking Events tab: {e}")

        # Final assessment
        total_hook_indicators = sum(found_patterns.values())
        has_hook_events = total_hook_indicators > 0

        print("\n📈 Summary:")
        print(f"  Total hook indicators found: {total_hook_indicators}")
        print(f"  Hook events detected: {'✅ YES' if has_hook_events else '❌ NO'}")

        if has_hook_events:
            print("  🎉 SUCCESS: Hook events are visible on the dashboard!")
        else:
            print("  ⚠️ ISSUE: No hook events detected, may need investigation")

        return has_hook_events, screenshot_path

    except Exception as e:
        print(f"❌ Error during dashboard check: {e}")
        return False, None

    finally:
        await page.close()


async def main():
    """Main test function"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context()

        try:
            print("🚀 Checking Claude MPM Dashboard for Hook Events\n")

            # First check - current state
            print("=== CHECKING CURRENT DASHBOARD STATE ===")
            has_hooks, screenshot = await capture_dashboard_state(context)

            if not has_hooks:
                print(
                    "\n🔄 No hook events found. Sending test events and checking again...\n"
                )

                # Send test events (import here to avoid startup issues)
                import sys

                sys.path.insert(0, str(Path(__file__).parent / "src"))

                try:
                    from claude_mpm.core.socketio_pool import get_connection_pool

                    pool = get_connection_pool()
                    test_event = {
                        "type": "hook",
                        "subtype": "pre_tool",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {
                            "tool_name": "PlaywrightTest",
                            "args": {"action": "verify_hook_events"},
                            "session_id": "playwright_test",
                        },
                    }

                    print("📤 Sending test hook event...")
                    pool.emit("claude_event", test_event)
                    print("✅ Test event sent")

                    # Wait for event to propagate
                    await asyncio.sleep(3)

                    print("\n=== RE-CHECKING AFTER SENDING TEST EVENT ===")
                    has_hooks_after, screenshot_after = await capture_dashboard_state(
                        context
                    )

                    if has_hooks_after:
                        print(
                            "\n🎉 SUCCESS: Hook events now visible after sending test event!"
                        )
                    else:
                        print(
                            "\n⚠️ Still no hook events visible. EventBus relay may need investigation."
                        )

                except Exception as e:
                    print(f"❌ Error sending test event: {e}")

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
