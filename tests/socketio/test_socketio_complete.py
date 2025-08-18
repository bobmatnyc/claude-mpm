#!/usr/bin/env python3
"""Complete Socket.IO dashboard test script.

This script tests the entire Socket.IO system end-to-end:
1. Verifies server is running
2. Connects as a client
3. Sends test events
4. Verifies events are received
5. Tests heartbeat functionality
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import socketio
except ImportError:
    print("❌ Error: python-socketio not installed")
    print("   Run: pip install python-socketio[asyncio_client]")
    sys.exit(1)

# Test configuration
SERVER_URL = "http://localhost:8765"
TEST_TIMEOUT = 10  # seconds


class SocketIOTestClient:
    """Test client for Socket.IO dashboard."""
    
    def __init__(self):
        self.sio = socketio.AsyncClient(
            logger=False,
            engineio_logger=False
        )
        self.connected = False
        self.events_received = []
        self.status_received = False
        self.heartbeat_received = False
        
        # Register event handlers
        self.register_handlers()
    
    def register_handlers(self):
        """Register Socket.IO event handlers."""
        
        @self.sio.event
        async def connect():
            print("✅ Connected to Socket.IO server")
            self.connected = True
        
        @self.sio.event
        async def disconnect():
            print("🔌 Disconnected from Socket.IO server")
            self.connected = False
        
        @self.sio.event
        async def status(data):
            print(f"📊 Received status: {json.dumps(data, indent=2)}")
            self.status_received = True
        
        @self.sio.event
        async def welcome(data):
            print(f"👋 Received welcome: {data.get('message')}")
        
        @self.sio.event
        async def event_history(data):
            count = len(data.get("events", []))
            print(f"📚 Received event history: {count} events")
            if count > 0:
                print(f"   Latest event: {data['events'][-1].get('type', 'unknown')}")
        
        @self.sio.event
        async def claude_event(data):
            event_type = data.get("type", "unknown")
            print(f"📡 Received claude_event: {event_type}")
            self.events_received.append(data)
            
            # Check for heartbeat
            if event_type == "heartbeat":
                self.heartbeat_received = True
                print(f"   💗 Heartbeat confirmed at {data.get('timestamp')}")
        
        @self.sio.event
        async def system_event(data):
            event_type = data.get("event", data.get("type", "unknown"))
            print(f"🖥️  Received system_event: {event_type}")
            self.events_received.append(data)
            
            # Check for heartbeat
            if event_type == "heartbeat":
                self.heartbeat_received = True
                print(f"   💗 System heartbeat confirmed at {data.get('timestamp')}")
        
        @self.sio.event
        async def error(data):
            print(f"❌ Error: {data}")
    
    async def run_test(self):
        """Run the complete test suite."""
        try:
            # Connect to server
            print(f"\n🔗 Connecting to {SERVER_URL}...")
            await self.sio.connect(SERVER_URL)
            await asyncio.sleep(1)
            
            if not self.connected:
                print("❌ Failed to connect to server")
                return False
            
            # Send test hook event
            print("\n📤 Sending test hook event...")
            test_hook_event = {
                "type": "hook",
                "event": "SubagentStart",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "agent": "test-agent",
                    "task": "testing Socket.IO dashboard",
                    "session_id": "test-session-123"
                }
            }
            await self.sio.emit("claude_event", test_hook_event)
            await asyncio.sleep(0.5)
            
            # Send another test event
            print("📤 Sending test status event...")
            test_status_event = {
                "type": "status",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": "Test status update",
                "level": "info"
            }
            await self.sio.emit("claude_event", test_status_event)
            await asyncio.sleep(0.5)
            
            # Request status
            print("📤 Requesting server status...")
            await self.sio.emit("get_status", {})
            await asyncio.sleep(0.5)
            
            # Wait a bit for any heartbeat
            print("\n⏳ Waiting for heartbeat (max 5 seconds)...")
            for i in range(5):
                if self.heartbeat_received:
                    break
                await asyncio.sleep(1)
                print(f"   Waiting... {i+1}/5")
            
            # Print results
            print("\n" + "="*50)
            print("📊 TEST RESULTS:")
            print("="*50)
            print(f"✅ Connected: {self.connected}")
            print(f"✅ Status received: {self.status_received}")
            print(f"✅ Events sent: 2")
            print(f"✅ Events received: {len(self.events_received)}")
            print(f"{'✅' if self.heartbeat_received else '⚠️'} Heartbeat received: {self.heartbeat_received}")
            
            if self.events_received:
                print(f"\n📋 Received event types:")
                for event in self.events_received:
                    print(f"   - {event.get('type', 'unknown')}")
            
            # Overall success
            success = (
                self.connected and 
                self.status_received and 
                len(self.events_received) >= 2
            )
            
            if success:
                print(f"\n✅ All tests passed!")
            else:
                print(f"\n⚠️  Some tests did not complete as expected")
                if not self.heartbeat_received:
                    print("   Note: Heartbeat may take up to 60 seconds to appear")
            
            return success
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.connected:
                print("\n🔌 Disconnecting...")
                await self.sio.disconnect()


async def check_server_running():
    """Check if the Socket.IO server is running."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SERVER_URL}/socket.io/?EIO=4") as resp:
                if resp.status == 200:
                    data = await resp.text()
                    # Socket.IO response starts with '0{' for the handshake
                    return data.startswith('0{')
    except Exception:
        return False


async def main():
    """Main test function."""
    print("🧪 Socket.IO Dashboard Complete Test")
    print("="*50)
    
    # Check if server is running
    print("🔍 Checking if Socket.IO server is running...")
    if not await check_server_running():
        print("❌ Socket.IO server is not running!")
        print("   Run: claude-mpm monitor start")
        return 1
    
    print("✅ Server is running")
    
    # Run the test
    client = SocketIOTestClient()
    success = await client.run_test()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)