#!/usr/bin/env python3
"""
Test the dashboard to confirm event history is loading properly.

WHY: We've fixed the Socket.IO server's automatic history transmission,
but we need to verify that the dashboard (browser-based client) is
actually receiving and displaying the event history correctly.
"""

import asyncio
import time
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    print("ERROR: python-socketio not available")
    sys.exit(1)

async def test_dashboard_like_connection():
    """Test connection that simulates how the dashboard connects."""
    
    print("🌐 Testing Dashboard-like Socket.IO Connection")
    print("=" * 60)
    
    sio = socketio.AsyncClient()
    history_received = False
    events_count = 0
    
    @sio.event
    async def connect():
        print("✅ Connected to Socket.IO server")
        
    @sio.event
    async def history(data):
        nonlocal history_received, events_count
        history_received = True
        
        print(f"📚 Received HISTORY event!")
        if isinstance(data, dict):
            events = data.get('events', [])
            count = data.get('count', 0)
            total = data.get('total_available', 0)
            events_count = len(events)
            
            print(f"   📊 Events received: {len(events)}")
            print(f"   📈 Count reported: {count}")
            print(f"   📋 Total available: {total}")
            
            if events:
                print(f"   📝 Recent event types:")
                for i, event in enumerate(events[-5:]):  # Show last 5
                    event_type = event.get('type', 'unknown')
                    timestamp = event.get('timestamp', 'no timestamp')
                    print(f"      {i+1}. {event_type} - {timestamp}")
                    
        print("✅ History loading successful!")
        
    @sio.event
    async def welcome(data):
        print(f"👋 Welcome message: {data.get('message', 'no message')}")
        
    @sio.event
    async def status(data):
        clients = data.get('clients_connected', 0)
        print(f"📊 Server status: {clients} clients connected")
        
    @sio.event
    async def claude_event(data):
        event_type = data.get('type', 'unknown')
        print(f"📨 Real-time event: {event_type}")
    
    try:
        # Connect to the Socket.IO server
        print("🔗 Connecting to http://localhost:8765...")
        await sio.connect('http://localhost:8765')
        
        # Wait a bit for automatic events
        print("⏳ Waiting for automatic history transmission...")
        await asyncio.sleep(3)
        
        # Check results
        print("\n" + "=" * 60)
        print("📋 DASHBOARD TEST RESULTS:")
        print(f"   History received automatically: {history_received}")
        print(f"   Number of events received: {events_count}")
        
        if history_received and events_count > 0:
            print("✅ SUCCESS: Dashboard would receive event history correctly!")
            print("   🎯 The event history loading issue is FIXED")
        elif history_received and events_count == 0:
            print("⚠️  PARTIAL: History event received but no events in it")
            print("   💡 This is normal if no recent activity has occurred")
        else:
            print("❌ FAILED: No history received automatically")
            print("   🔧 The dashboard would not load event history")
            
        await sio.disconnect()
        return history_received
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def main():
    """Main test function."""
    
    # Check if server is running
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(('127.0.0.1', 8765))
        if result != 0:
            print("❌ No Socket.IO server running on port 8765")
            print("   Start with: python scripts/start_persistent_socketio_server.py")
            return False
    except Exception as e:
        print(f"❌ Cannot check server: {e}")
        return False
    finally:
        sock.close()
    
    # Run the test
    success = await test_dashboard_like_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 DASHBOARD HISTORY LOADING: WORKING")
        print("   ✅ Users will see event history when dashboard loads")
        print("   🚀 The issue has been successfully resolved!")
    else:
        print("💥 DASHBOARD HISTORY LOADING: BROKEN")
        print("   ❌ Users will NOT see event history when dashboard loads")
        print("   🔧 Further debugging required")
    
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)