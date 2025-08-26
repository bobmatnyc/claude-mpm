import pytest

#!/usr/bin/env python3
"""Test script to verify the Socket.IO dashboard file viewer is working.

WHY: This script sends test file operation events directly to the Socket.IO server
to verify that the file-tool-tracker.js fixes are working properly.

USAGE:
1. Start the dashboard: ./claude-mpm dashboard
2. Open browser to http://localhost:8765
3. Run this script: python scripts/test_dashboard_file_viewer.py
4. Check the Files tab in the dashboard to see if operations appear
"""

import asyncio
import sys
import time
from datetime import datetime

try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("❌ Socket.IO not available. Install with: pip install python-socketio")
    sys.exit(1)


@pytest.mark.asyncio
async def test_file_operations():
    """Generate test file operations to verify dashboard tracking."""

    print("🧪 Starting dashboard file viewer test...")

    # Create Socket.IO client
    sio = socketio.AsyncClient()

    try:
        # Connect to the dashboard server
        print("📡 Connecting to Socket.IO server on port 8765...")
        await sio.connect("http://localhost:8765")
        print("✅ Connected to Socket.IO server")

        # Wait a moment for connection to stabilize
        await asyncio.sleep(0.5)

        print("🔍 Generating file operation events...")

        session_id = "test-file-viewer"

        # Test 1: Read operation
        print("\n1️⃣ Testing Read operation...")
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "pre_tool",
                    "tool_name": "Read",
                    "tool_parameters": {"file_path": "/test/example.txt"},
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )
        await asyncio.sleep(0.1)
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "post_tool",
                    "tool_name": "Read",
                    "tool_parameters": {"file_path": "/test/example.txt"},
                    "result": "File contents here",
                    "success": True,
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )

        # Test 2: Write operation
        print("2️⃣ Testing Write operation...")
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "pre_tool",
                    "tool_name": "Write",
                    "tool_parameters": {
                        "file_path": "/test/output.py",
                        "content": "print('Hello World')",
                    },
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )
        await asyncio.sleep(0.1)
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "post_tool",
                    "tool_name": "Write",
                    "tool_parameters": {"file_path": "/test/output.py"},
                    "success": True,
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )

        # Test 3: Edit operation
        print("3️⃣ Testing Edit operation...")
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "pre_tool",
                    "tool_name": "Edit",
                    "tool_parameters": {
                        "file_path": "/test/config.json",
                        "old_string": "value: 1",
                        "new_string": "value: 2",
                    },
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )
        await asyncio.sleep(0.1)
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "post_tool",
                    "tool_name": "Edit",
                    "tool_parameters": {"file_path": "/test/config.json"},
                    "success": True,
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )

        # Test 4: Grep operation
        print("4️⃣ Testing Grep operation...")
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "pre_tool",
                    "tool_name": "Grep",
                    "tool_parameters": {"pattern": "TODO", "path": "/test/src"},
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )
        await asyncio.sleep(0.1)
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "post_tool",
                    "tool_name": "Grep",
                    "tool_parameters": {"pattern": "TODO", "path": "/test/src"},
                    "result": "Found 5 matches",
                    "success": True,
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )

        # Test 5: Glob operation (new tool)
        print("5️⃣ Testing Glob operation...")
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "pre_tool",
                    "tool_name": "Glob",
                    "tool_parameters": {"pattern": "*.py", "path": "/test"},
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )
        await asyncio.sleep(0.1)
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "post_tool",
                    "tool_name": "Glob",
                    "tool_parameters": {"pattern": "*.py", "path": "/test"},
                    "result": ["file1.py", "file2.py"],
                    "success": True,
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )

        # Test 6: LS operation (new tool)
        print("6️⃣ Testing LS operation...")
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "pre_tool",
                    "tool_name": "LS",
                    "tool_parameters": {"path": "/test/directory"},
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )
        await asyncio.sleep(0.1)
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "post_tool",
                    "tool_name": "LS",
                    "tool_parameters": {"path": "/test/directory"},
                    "result": ["file1.txt", "file2.txt", "subdir/"],
                    "success": True,
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )

        # Test 7: MultiEdit operation
        print("7️⃣ Testing MultiEdit operation...")
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "pre_tool",
                    "tool_name": "MultiEdit",
                    "tool_parameters": {
                        "file_path": "/test/multi.js",
                        "edits": [
                            {"old_string": "var", "new_string": "const"},
                            {"old_string": "function", "new_string": "const arrow ="},
                        ],
                    },
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )
        await asyncio.sleep(0.1)
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "post_tool",
                    "tool_name": "MultiEdit",
                    "tool_parameters": {"file_path": "/test/multi.js"},
                    "success": True,
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )

        # Test 8: Test with lowercase tool names (the original issue)
        print("8️⃣ Testing lowercase tool names (original issue)...")
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "pre_tool",
                    "tool_name": "read",  # lowercase
                    "tool_parameters": {"file_path": "/test/lowercase.txt"},
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )
        await asyncio.sleep(0.1)
        await sio.emit(
            "claude_event",
            {
                "type": "hook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "hook",
                    "subtype": "post_tool",
                    "tool_name": "read",  # lowercase
                    "tool_parameters": {"file_path": "/test/lowercase.txt"},
                    "success": True,
                    "session_id": session_id,
                    "timestamp": time.time(),
                },
            },
        )

        print("\n✅ Test events sent to dashboard!")
        print("📊 Check the Files tab in the dashboard at http://localhost:8765")
        print("   You should see 8 file operations listed")
        print("\n🔍 Expected files in the Files tab:")
        print("   - /test/example.txt (Read)")
        print("   - /test/output.py (Write)")
        print("   - /test/config.json (Edit)")
        print("   - /test/src (Grep search)")
        print("   - [glob] *.py (Glob search)")
        print("   - /test/directory (LS listing)")
        print("   - /test/multi.js (MultiEdit)")
        print("   - /test/lowercase.txt (read - lowercase)")

        # Keep connection alive for a moment to ensure events are processed
        await asyncio.sleep(2)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Disconnect
        await sio.disconnect()
        print("\n🏁 Test complete!")


if __name__ == "__main__":
    asyncio.run(test_file_operations())
