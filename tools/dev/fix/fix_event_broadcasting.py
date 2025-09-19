#!/usr/bin/env python3
"""Fix event broadcasting issues in dashboard server."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def fix_server_broadcasting():
    """Fix the server to properly normalize and broadcast events."""

    server_path = Path(__file__).parent.parent / "src/claude_mpm/services/socketio/server/core.py"

    print("Fixing server event broadcasting...")

    content = server_path.read_text()

    # Find the api_events_handler section
    old_handler = '''            try:
                # Parse JSON payload
                event_data = await request.json()

                # Log receipt if debugging
                event_type = event_data.get("subtype", "unknown")
                self.logger.debug(f"Received HTTP event: {event_type}")

                # Broadcast to all connected dashboard clients via SocketIO
                if self.sio:
                    # The event is already in claude_event format from the hook handler
                    await self.sio.emit("claude_event", event_data)'''

    new_handler = '''            try:
                # Parse JSON payload
                event_data = await request.json()

                # Log receipt if debugging
                event_type = event_data.get("subtype") or event_data.get("hook_event_name") or "unknown"
                self.logger.debug(f"Received HTTP event: {event_type}")
                
                # Transform hook event format to claude_event format if needed
                if "hook_event_name" in event_data and "event" not in event_data:
                    # This is a raw hook event, transform it
                    from claude_mpm.services.socketio.event_normalizer import EventNormalizer
                    normalizer = EventNormalizer()
                    
                    # Create the format expected by normalizer
                    raw_event = {
                        "type": "hook",
                        "subtype": event_data.get("hook_event_name", "unknown").lower().replace("submit", "").replace("use", "_use"),
                        "timestamp": event_data.get("timestamp"),
                        "data": event_data.get("hook_input_data", {}),
                        "source": "claude_hooks",
                        "session_id": event_data.get("session_id"),
                    }
                    
                    # Map hook event names to dashboard subtypes
                    subtype_map = {
                        "UserPromptSubmit": "user_prompt",
                        "PreToolUse": "pre_tool",
                        "PostToolUse": "post_tool",
                        "Stop": "stop",
                        "SubagentStop": "subagent_stop",
                        "AssistantResponse": "assistant_response"
                    }
                    raw_event["subtype"] = subtype_map.get(event_data.get("hook_event_name"), "unknown")
                    
                    normalized = normalizer.normalize(raw_event, source="hook")
                    event_data = normalized.to_dict()

                # Broadcast to all connected dashboard clients via SocketIO
                if self.sio:
                    # Now the event is properly normalized
                    await self.sio.emit("claude_event", event_data)'''

    if old_handler in content:
        content = content.replace(old_handler, new_handler)
        server_path.write_text(content)
        print("✅ Fixed server event broadcasting with normalization")
        return True
    print("⚠️ Could not find exact match in server, trying alternative...")
    return False


def add_debug_logging():
    """Add debug logging to see what's being broadcast."""

    server_path = Path(__file__).parent.parent / "src/claude_mpm/services/socketio/server/core.py"
    content = server_path.read_text()

    # Add debug logging
    old_emit = '''                # Broadcast to all connected dashboard clients via SocketIO
                if self.sio:
                    # The event is already in claude_event format from the hook handler
                    await self.sio.emit("claude_event", event_data)'''

    new_emit = '''                # Broadcast to all connected dashboard clients via SocketIO
                if self.sio:
                    # Debug: Log what we're broadcasting
                    self.logger.info(f"Broadcasting claude_event to {len(self.connected_clients)} clients")
                    self.logger.debug(f"Event data keys: {list(event_data.keys())}")
                    
                    # The event is already in claude_event format from the hook handler
                    await self.sio.emit("claude_event", event_data)
                    self.logger.info(f"✅ Broadcast complete")'''

    if old_emit in content and new_emit not in content:
        content = content.replace(old_emit, new_emit)
        server_path.write_text(content)
        print("✅ Added debug logging for broadcasting")
        return True

    return False


def main():
    """Main entry point."""
    print("=" * 60)
    print("Fixing Event Broadcasting Issues")
    print("=" * 60)

    success = False

    if fix_server_broadcasting():
        success = True

    if add_debug_logging():
        success = True

    if success:
        print("\n✅ Fixes applied!")
        print("\nNext steps:")
        print("1. Restart the dashboard server:")
        print("   pkill -f socketio_daemon")
        print("   python src/claude_mpm/scripts/socketio_daemon.py start")
        print("2. Run the test again to see if events are broadcast")
        print("3. Check dashboard at http://localhost:8765")
    else:
        print("\n⚠️ No fixes were needed or could not apply fixes")


if __name__ == "__main__":
    main()
