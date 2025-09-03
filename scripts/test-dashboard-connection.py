#!/usr/bin/env python3
"""
Test script to verify dashboard SocketIO connection and functionality.

This script tests:
1. HTTP endpoints (dashboard, static files, API)
2. SocketIO connection and events
3. Mock AST analysis functionality
"""

import asyncio
import json
import sys
from pathlib import Path

import aiohttp
import socketio

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def test_http_endpoints():
    """Test HTTP endpoints."""
    print("🌐 Testing HTTP endpoints...")

    async with aiohttp.ClientSession() as session:
        # Test dashboard
        try:
            async with session.get("http://localhost:8765/") as resp:
                if resp.status == 200:
                    print("  ✅ Dashboard HTML: OK")
                else:
                    print(f"  ❌ Dashboard HTML: {resp.status}")
        except Exception as e:
            print(f"  ❌ Dashboard HTML: {e}")

        # Test version endpoint
        try:
            async with session.get("http://localhost:8765/version.json") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"  ✅ Version API: {data}")
                else:
                    print(f"  ❌ Version API: {resp.status}")
        except Exception as e:
            print(f"  ❌ Version API: {e}")

        # Test directory API
        try:
            async with session.get(
                "http://localhost:8765/api/directory/list?path=."
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"  ✅ Directory API: {len(data.get('contents', []))} items")
                else:
                    print(f"  ❌ Directory API: {resp.status}")
        except Exception as e:
            print(f"  ❌ Directory API: {e}")


async def test_socketio_connection():
    """Test SocketIO connection and events."""
    print("\n📡 Testing SocketIO connection...")

    # Create SocketIO client
    sio = socketio.AsyncClient()

    # Track events
    events_received = []

    @sio.event
    async def connect():
        print("  ✅ SocketIO connected successfully")
        events_received.append("connect")

    @sio.event
    async def disconnect():
        print("  ❌ SocketIO disconnected")
        events_received.append("disconnect")

    @sio.event
    async def connection_test(data):
        print(f"  ✅ Received connection_test: {data}")
        events_received.append("connection_test")

    @sio.event
    async def git_branch_response(data):
        print(f"  ✅ Received git_branch_response: {data}")
        events_received.append("git_branch_response")

    @sio.event
    async def status_response(data):
        print(f"  ✅ Received status_response: {data}")
        events_received.append("status_response")

    @sio.event
    async def code_file_analyzed(data):
        print(
            f"  ✅ Received code:file:analyzed: {len(data.get('elements', []))} elements"
        )
        events_received.append("code_file_analyzed")

    try:
        # Connect to server
        await sio.connect("http://localhost:8765")

        # Wait a moment for connection_test
        await asyncio.sleep(1)

        # Test git branch request
        print("  📤 Sending get_git_branch request...")
        await sio.emit("get_git_branch", "/test/path")

        # Test status request
        print("  📤 Sending request.status...")
        await sio.emit("request.status", None)

        # Test file analysis
        print("  📤 Sending code:analyze:file request...")
        await sio.emit("code:analyze:file", {"path": "/test/file.py"})

        # Wait for responses
        await asyncio.sleep(2)

        # Disconnect
        await sio.disconnect()

        print(f"\n  📊 Events received: {events_received}")

        # Check if we got expected events
        expected_events = [
            "connect",
            "connection_test",
            "git_branch_response",
            "code_file_analyzed",
        ]
        missing_events = [e for e in expected_events if e not in events_received]

        if missing_events:
            print(f"  ⚠️  Missing events: {missing_events}")
        else:
            print("  ✅ All expected events received!")

        return len(missing_events) == 0

    except Exception as e:
        print(f"  ❌ SocketIO connection failed: {e}")
        return False


async def test_mock_ast_analysis():
    """Test mock AST analysis functionality."""
    print("\n🔍 Testing mock AST analysis...")

    sio = socketio.AsyncClient()
    analysis_result = None

    @sio.event
    async def connect():
        print("  ✅ Connected for AST test")

    @sio.event
    async def code_file_analyzed(data):
        nonlocal analysis_result
        analysis_result = data
        print("  ✅ AST analysis result received:")
        print(f"    - Path: {data.get('path')}")
        print(f"    - Elements: {len(data.get('elements', []))}")
        print(f"    - Complexity: {data.get('complexity')}")
        print(f"    - Stats: {data.get('stats')}")

        # Show elements detail
        for elem in data.get("elements", []):
            print(
                f"    - {elem.get('type')}: {elem.get('name')} (line {elem.get('line')})"
            )
            if elem.get("methods"):
                for method in elem["methods"]:
                    print(
                        f"      - method: {method.get('name')} (line {method.get('line')})"
                    )

    try:
        await sio.connect("http://localhost:8765")
        await asyncio.sleep(0.5)

        # Test Python file analysis
        await sio.emit("code:analyze:file", {"path": "/test/example.py"})
        await asyncio.sleep(1)

        # Test JavaScript file analysis
        await sio.emit("code:analyze:file", {"path": "/test/example.js"})
        await asyncio.sleep(1)

        await sio.disconnect()

        return analysis_result is not None

    except Exception as e:
        print(f"  ❌ AST analysis test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Claude MPM Dashboard Connection Test")
    print("=" * 50)

    # Test HTTP endpoints
    await test_http_endpoints()

    # Test SocketIO connection
    socketio_ok = await test_socketio_connection()

    # Test AST analysis
    ast_ok = await test_mock_ast_analysis()

    # Summary
    print("\n📊 Test Summary:")
    print(f"  SocketIO Connection: {'✅ PASS' if socketio_ok else '❌ FAIL'}")
    print(f"  AST Analysis: {'✅ PASS' if ast_ok else '❌ FAIL'}")

    if socketio_ok and ast_ok:
        print("\n🎉 All tests passed! Dashboard should be working.")
        return 0
    print("\n❌ Some tests failed. Check server logs for details.")
    return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
