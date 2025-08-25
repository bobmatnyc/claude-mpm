#!/usr/bin/env python3
"""
Monitor real-time hook events from Claude tool usage.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    import socketio

    print("✅ python-socketio is available")
except ImportError:
    print("❌ python-socketio not found")
    sys.exit(1)


class RealTimeEventMonitor:
    """Monitor real-time events from the Socket.IO server."""

    def __init__(self):
        self.client = socketio.AsyncClient()
        self.events_captured = []

    async def start_monitoring(self):
        """Start monitoring events."""

        @self.client.event
        async def connect():
            print("🔗 Connected to Socket.IO server - monitoring for hook events...")
            print("📊 Waiting for Claude tool usage to generate hook events...")
            print("=" * 80)

        @self.client.event
        async def claude_event(data):
            timestamp = datetime.now().strftime("%H:%M:%S")
            event_type = data.get("type", "unknown")

            print(f"[{timestamp}] 📨 HOOK EVENT RECEIVED:")
            print(f"   Type: {event_type}")

            if event_type == "hook":
                subtype = data.get("subtype", "unknown")
                print(f"   Subtype: {subtype}")
                print(f"   Format: [hook] hook.{subtype}")
            elif event_type.startswith("hook."):
                hook_name = event_type[5:]
                print(f"   Hook: {hook_name}")
                print(f"   Format: [hook] {event_type}")

            # Show relevant data
            event_data = data.get("data", {})
            if "tool_name" in event_data:
                print(f"   Tool: {event_data['tool_name']}")
            if "prompt_text" in event_data:
                prompt = (
                    event_data["prompt_text"][:50] + "..."
                    if len(event_data["prompt_text"]) > 50
                    else event_data["prompt_text"]
                )
                print(f"   Prompt: {prompt}")
            if "agent_type" in event_data:
                print(f"   Agent: {event_data['agent_type']}")

            print(f"   Data: {json.dumps(event_data, indent=6)}")
            print("-" * 80)

            self.events_captured.append({"timestamp": timestamp, "event": data})

        @self.client.event
        async def system_event(data):
            if data.get("subtype") == "heartbeat":
                active_sessions = data.get("data", {}).get("active_sessions", [])
                if active_sessions:
                    print(f"💓 Active sessions: {len(active_sessions)}")
                    for session in active_sessions:
                        print(
                            f"   - {session.get('agent', 'pm')} session: {session.get('session_id', 'unknown')[:8]}..."
                        )

        try:
            await self.client.connect("http://localhost:8765")

            # Keep monitoring until interrupted
            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            print(f"📊 Total hook events captured: {len(self.events_captured)}")

            if self.events_captured:
                print("\n📋 Summary of captured events:")
                for i, captured in enumerate(self.events_captured, 1):
                    event = captured["event"]
                    event_type = event.get("type", "unknown")
                    print(f"   {i:2d}. [{captured['timestamp']}] {event_type}")

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            try:
                await self.client.disconnect()
            except:
                pass


async def main():
    """Main monitoring function."""
    print("🚀 Starting real-time hook event monitor")
    print("🎯 Use Claude tools (Read, Bash, etc.) to generate hook events")
    print("⏹️  Press Ctrl+C to stop monitoring")
    print()

    monitor = RealTimeEventMonitor()
    await monitor.start_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
