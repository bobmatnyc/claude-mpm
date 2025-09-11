#!/usr/bin/env python3
"""
Test that simulates the browser monitor injection to verify:
1. Real browser logs DO appear in Browser Logs tab
2. Hook events do NOT appear in Browser Logs tab
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def send_browser_log(session):
    """Send a valid browser console log"""
    browser_log = {
        "browser_id": f"chrome-{int(datetime.now().timestamp())}",
        "level": "INFO",
        "message": "✅ This is a REAL browser console.log that SHOULD appear",
        "timestamp": datetime.now().isoformat(),
        "url": "https://example.com/test",
        "line_info": "app.js:42"
    }
    
    # This mimics what the browser monitor injection would send
    async with session.post(
        'http://localhost:8765/api/browser-log',
        json=browser_log
    ) as response:
        print(f"Sent browser log: {response.status}")
        return response.status == 204

async def send_fake_hook_as_browser_log(session):
    """Try to send a hook event disguised as browser log"""
    fake_hook = {
        "type": "hook.pre_tool",
        "source": "hook", 
        "message": "❌ This is a FAKE hook event that should NOT appear",
        "timestamp": datetime.now().isoformat()
    }
    
    # Try to send it to browser log endpoint
    async with session.post(
        'http://localhost:8765/api/browser-log',
        json=fake_hook
    ) as response:
        print(f"Sent fake hook as browser log: {response.status}")
        return response.status

async def main():
    print("🧪 Browser Monitor Injection Test")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Send a real browser log
        print("\n1. Sending REAL browser console log...")
        await send_browser_log(session)
        
        # Try to send a hook event as browser log
        print("\n2. Attempting to send hook event as browser log...")
        await send_fake_hook_as_browser_log(session)
        
        # Send another real browser log with different level
        print("\n3. Sending ERROR level browser log...")
        error_log = {
            "browser_id": f"firefox-{int(datetime.now().timestamp())}",
            "level": "ERROR",
            "message": "⚠️ This is a browser console.error that SHOULD appear",
            "timestamp": datetime.now().isoformat(),
            "url": "https://example.com/error",
            "line_info": "error.js:13"
        }
        
        async with session.post(
            'http://localhost:8765/api/browser-log',
            json=error_log
        ) as response:
            print(f"Sent error log: {response.status}")
    
    print("\n" + "=" * 50)
    print("✅ Test complete!")
    print("\nEXPECTED RESULTS in Browser Logs tab:")
    print("  ✅ Should see: 'This is a REAL browser console.log'")
    print("  ✅ Should see: 'This is a browser console.error'")
    print("  ❌ Should NOT see: Any hook events")
    print("\nPlease check http://localhost:8765 Browser Logs tab to verify!")

if __name__ == "__main__":
    asyncio.run(main())