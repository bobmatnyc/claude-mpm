#!/usr/bin/env python3
"""Test script to verify React component exports are working."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.monitor.server import UnifiedMonitorServer


async def test_react_exports():
    """Test that React exports are accessible in the browser."""

    print("Starting monitor server...")
    server = UnifiedMonitorServer(port=8765)

    # Start server in background
    server_task = asyncio.create_task(server.start())

    # Give server time to start
    await asyncio.sleep(2)

    print("\n" + "=" * 60)
    print("Testing React Component Exports")
    print("=" * 60)

    print("\n1. Server running at http://localhost:8765")
    print("2. Open http://localhost:8765/static/events.html in browser")
    print("3. Open browser console (F12)")
    print("4. Run these commands to test:")
    print("   - typeof window.initializeReactEvents")
    print("   - typeof window.ClaudeMPMReact")
    print("   - window.initializeReactEvents()")
    print("\n5. Expected results:")
    print("   - First command should return 'function'")
    print("   - Second command should return 'object'")
    print("   - Third command should initialize React and return true")
    print("\n6. Check for console messages:")
    print("   - 'React events initialization function exposed on window'")
    print("   - 'React EventViewer initialized'")

    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60 + "\n")

    try:
        # Keep server running
        await server_task
    except KeyboardInterrupt:
        print("\nShutting down server...")
        await server.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(test_react_exports())
    except KeyboardInterrupt:
        print("\nTest stopped by user")
