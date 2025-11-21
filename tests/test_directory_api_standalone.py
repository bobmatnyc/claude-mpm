#!/usr/bin/env python3
"""Standalone test of the simple directory API"""

import asyncio
import os
import sys
from pathlib import Path

from aiohttp import web

# Add the src directory to the Python path so we can import our module
sys.path.insert(0, "/Users/masa/Projects/claude-mpm/src")


async def test_directory_api():
    """Test the directory API in a minimal server"""

    print("🚀 Starting minimal test server for directory API...")

    # Import our directory API
    from claude_mpm.dashboard.api.simple_directory import register_routes

    # Create a simple aiohttp app
    app = web.Application()

    # Register our routes
    register_routes(app)

    # Start the server on port 8766 to avoid conflicts
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "localhost", 8767)
    await site.start()

    print("✅ Test server started on http://localhost:8767")

    # Test the API endpoints
    import aiohttp

    async with aiohttp.ClientSession() as session:
        # Test cases
        test_cases = [
            {"path": "/Users/masa/Projects/claude-mpm/src", "name": "src directory"},
            {
                "path": "/Users/masa/Projects/claude-mpm/src/claude_mpm",
                "name": "claude_mpm directory",
            },
            {
                "path": "/Users/masa/Projects/claude-mpm/scripts",
                "name": "scripts directory",
            },
            {"path": ".", "name": "current directory"},
            {"path": "/nonexistent", "name": "nonexistent directory"},
        ]

        for test_case in test_cases:
            print(f"\n📁 Testing {test_case['name']}: {test_case['path']}")

            try:
                url = (
                    f"http://localhost:8767/api/directory/list?path={test_case['path']}"
                )
                async with session.get(url) as response:
                    data = await response.json()

                    print(f"   Path: {data['path']}")
                    print(f"   Exists: {data['exists']}")
                    print(f"   Is Directory: {data['is_directory']}")

                    if data.get("contents"):
                        print(f"   Contents ({len(data['contents'])} items):")
                        for item in data["contents"][:10]:  # Show first 10 items
                            icon = "📁" if item["is_directory"] else "📄"
                            print(f"     {icon} {item['name']}")
                        if len(data["contents"]) > 10:
                            print(
                                f"     ... and {len(data['contents']) - 10} more items"
                            )
                    elif data.get("error"):
                        print(f"   ❌ Error: {data['error']}")
                    else:
                        print("   📭 Empty directory")

            except Exception as e:
                print(f"   ❌ Test failed: {e}")

    # Clean up
    await site.stop()
    await runner.cleanup()
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_directory_api())
