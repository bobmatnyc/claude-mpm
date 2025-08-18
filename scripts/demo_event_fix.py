#!/usr/bin/env python3
"""
Demonstration script showing that dashboard events now display correctly
after fixing the field overwriting issue.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.socketio.server.core import SocketIOService
from claude_mpm.services.socketio.server.broadcaster import EventBroadcaster

async def demo_fixed_events():
    """Demonstrate that events with conflicting fields now work correctly."""
    
    # Initialize services
    socketio_service = SocketIOService()
    broadcaster = EventBroadcaster()
    
    # Start server
    await socketio_service.start()
    print(f"✅ SocketIO server started on port {socketio_service.port}")
    print(f"📊 Open http://localhost:8080 to view the dashboard\n")
    
    await asyncio.sleep(2)
    
    print("=" * 60)
    print("DEMONSTRATING FIXED EVENT PARSING")
    print("=" * 60)
    
    # The problematic event that would previously show as "unknown"
    problematic_event = {
        "type": "hook.pre_tool",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "type": "CONFLICT_TYPE",  # This used to overwrite the main type!
            "subtype": "CONFLICT_SUBTYPE",  # This used to overwrite the subtype!
            "tool_name": "Edit",
            "parameters": {
                "file_path": "/src/example.py",
                "old_string": "bug",
                "new_string": "fix"
            }
        }
    }
    
    print("\n🔴 BEFORE FIX: This event would show as 'CONFLICT_TYPE' or 'unknown'")
    print("🟢 AFTER FIX: This event correctly shows as 'hook.pre_tool'\n")
    
    print("Sending problematic event:")
    print(json.dumps(problematic_event, indent=2))
    
    await broadcaster.broadcast_event(problematic_event)
    
    print("\n✅ Event sent! Check the dashboard - it should show as 'hook.pre_tool'")
    print("   NOT as 'CONFLICT_TYPE' or 'unknown'\n")
    
    await asyncio.sleep(2)
    
    # Send a few more test events
    print("Sending additional test events...\n")
    
    # Legacy format event
    legacy_event = {
        "event": "SubagentStart",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "agent_type": "Engineer",
            "task": "Implement new feature"
        }
    }
    print("📤 Legacy SubagentStart event sent (should show as 'subagent.start')")
    await broadcaster.broadcast_event(legacy_event)
    await asyncio.sleep(1)
    
    # Session event with conflicting subtype
    session_event = {
        "type": "session",
        "subtype": "started",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "subtype": "wrong_subtype",  # Should NOT overwrite
            "session_id": "demo_session_123"
        }
    }
    print("📤 Session event sent (should show as 'session.started', not 'session.wrong_subtype')")
    await broadcaster.broadcast_event(session_event)
    await asyncio.sleep(1)
    
    # Tool event with clean data
    clean_event = {
        "type": "hook.post_tool",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "tool_name": "MultiEdit",
            "result": "success",
            "files_modified": 3
        }
    }
    print("📤 Clean hook.post_tool event sent (should show as 'hook.post_tool')")
    await broadcaster.broadcast_event(clean_event)
    
    print("\n" + "=" * 60)
    print("✅ DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("\n📊 Check the dashboard at http://localhost:8080")
    print("All events should display with their correct types, not 'unknown'!")
    print("\nPress Ctrl+C to stop the server...")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        await socketio_service.stop()

if __name__ == "__main__":
    try:
        asyncio.run(demo_fixed_events())
    except KeyboardInterrupt:
        print("\nDemo stopped.")