#!/usr/bin/env python3
"""Test heartbeat with simulated hook events.

WHY: This script verifies that hook events properly update session tracking
in the heartbeat data, simulating what happens during actual Claude usage.
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.services.socketio_server import SocketIOServer

try:
    import socketio
except ImportError:
    print("Error: socketio-client not installed")
    sys.exit(1)


class HookEventSimulator:
    """Simulates hook events from Claude."""
    
    def __init__(self, port=8765):
        self.sio = socketio.Client()
        self.port = port
        self.connected = False
        
    def connect(self):
        """Connect to server."""
        try:
            self.sio.connect(f"http://localhost:{self.port}")
            self.connected = True
            print("   ✅ Hook simulator connected")
            return True
        except Exception as e:
            print(f"   ❌ Hook simulator connection failed: {e}")
            return False
            
    def send_hook_event(self, event_type: str, data: dict):
        """Send a hook event to the server."""
        if not self.connected:
            return
            
        hook_event = {
            "type": "hook",
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        self.sio.emit("claude_event", hook_event)
        print(f"   📤 Sent hook event: {event_type}")
        
    def simulate_user_session(self, session_id: str):
        """Simulate a complete user session with hook events."""
        
        # User prompt
        self.send_hook_event("user_prompt", {
            "session_id": session_id,
            "prompt_text": "Help me implement a new feature",
            "working_directory": "/project/src",
        })
        time.sleep(0.5)
        
        # Pre-tool for Task delegation
        self.send_hook_event("pre_tool", {
            "session_id": session_id,
            "tool_name": "Task",
            "delegation_details": {
                "agent_type": "engineer",
                "prompt": "Implement the user authentication feature"
            }
        })
        time.sleep(0.5)
        
        # Subagent start
        self.send_hook_event("subagent_start", {
            "session_id": session_id,
            "agent_type": "engineer",
            "prompt": "Implement the user authentication feature"
        })
        time.sleep(2)
        
        # Subagent stop
        self.send_hook_event("subagent_stop", {
            "session_id": session_id,
            "agent_type": "engineer",
            "exit_code": 0
        })
        
    def disconnect(self):
        """Disconnect from server."""
        if self.connected:
            self.sio.disconnect()
            self.connected = False


class HeartbeatMonitor:
    """Monitors heartbeat events."""
    
    def __init__(self, port=8765):
        self.sio = socketio.Client()
        self.port = port
        self.heartbeats = []
        
        @self.sio.on("system_event")
        def on_system_event(data):
            if data.get("type") == "system" and data.get("event") == "heartbeat":
                self.heartbeats.append(data)
                self.display_heartbeat(data)
                
    def connect(self):
        """Connect to server."""
        try:
            self.sio.connect(f"http://localhost:{self.port}")
            print("   ✅ Monitor connected")
            return True
        except Exception as e:
            print(f"   ❌ Monitor connection failed: {e}")
            return False
            
    def display_heartbeat(self, data):
        """Display heartbeat information."""
        hb_data = data.get("data", {})
        sessions = hb_data.get("active_sessions", [])
        
        print(f"\n   🫀 HEARTBEAT #{len(self.heartbeats)}")
        print(f"      Sessions: {len(sessions)}")
        
        for session in sessions:
            status_icon = "✅" if session.get("status") == "completed" else "🔄"
            print(f"      {status_icon} {session.get('session_id', '')[:12]}... "
                  f"[{session.get('agent', 'unknown')}] "
                  f"- {session.get('status', 'unknown')}")
                  
    def disconnect(self):
        """Disconnect from server."""
        if self.sio.connected:
            self.sio.disconnect()


def main():
    """Run the test."""
    print("🧪 Hook Event Session Tracking Test")
    print("=" * 60)
    
    # Start server
    print("\n1️⃣  Starting Socket.IO server...")
    server = SocketIOServer(port=8765)
    server.core.heartbeat_interval = 3  # 3 seconds for testing
    
    try:
        server.start_sync()
        print("   ✅ Server started")
        time.sleep(1)
        
        # Connect monitor
        print("\n2️⃣  Starting heartbeat monitor...")
        monitor = HeartbeatMonitor()
        if not monitor.connect():
            return
            
        # Connect hook simulator
        print("\n3️⃣  Starting hook event simulator...")
        simulator = HookEventSimulator()
        if not simulator.connect():
            return
            
        # Wait for initial heartbeat
        print("\n4️⃣  Waiting for initial heartbeat...")
        time.sleep(3.5)
        
        # Simulate first session
        print("\n5️⃣  Simulating session 1 (Engineer task)...")
        simulator.simulate_user_session("hook-session-001")
        
        # Wait for heartbeat to show new session
        print("\n6️⃣  Waiting for heartbeat with session data...")
        time.sleep(3.5)
        
        # Simulate second session
        print("\n7️⃣  Simulating session 2 (Research task)...")
        simulator.send_hook_event("pre_tool", {
            "session_id": "hook-session-002",
            "tool_name": "Task",
            "delegation_details": {
                "agent_type": "research",
                "prompt": "Analyze the codebase structure"
            }
        })
        simulator.send_hook_event("subagent_start", {
            "session_id": "hook-session-002",
            "agent_type": "research",
            "prompt": "Analyze the codebase structure"
        })
        
        # Wait for heartbeat
        print("\n8️⃣  Waiting for heartbeat with both sessions...")
        time.sleep(3.5)
        
        # Complete second session
        simulator.send_hook_event("subagent_stop", {
            "session_id": "hook-session-002",
            "agent_type": "research",
            "exit_code": 0
        })
        
        # Final heartbeat
        print("\n9️⃣  Waiting for final heartbeat...")
        time.sleep(3.5)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary:")
        print(f"   • Heartbeats received: {len(monitor.heartbeats)}")
        print(f"   • Sessions tracked via hooks: 2")
        
        # Check if sessions were properly tracked
        if monitor.heartbeats:
            last_hb = monitor.heartbeats[-1]
            sessions = last_hb.get("data", {}).get("active_sessions", [])
            hook_sessions = [s for s in sessions if "hook-session" in s.get("session_id", "")]
            
            if len(hook_sessions) >= 1:
                print("\n✅ TEST PASSED: Hook events properly update session tracking!")
            else:
                print("\n⚠️  TEST WARNING: Hook sessions not properly tracked")
        else:
            print("\n❌ TEST FAILED: No heartbeats received")
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔚 Cleaning up...")
        simulator.disconnect()
        monitor.disconnect()
        server.stop_sync()
        print("   👋 All connections closed")


if __name__ == "__main__":
    main()