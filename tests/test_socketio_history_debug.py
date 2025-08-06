#!/usr/bin/env python3
"""
Test script to debug Socket.IO event history loading issues.

WHY: The dashboard is not receiving event history when it connects. This script
tests the Socket.IO server API directly to verify:
1. If the server is storing events in event_history deque
2. If the server sends event history on client connection
3. What data is actually being transmitted
4. If there are any connection/handshake issues

This isolates whether the issue is on the server side or client side.
"""

import asyncio
import json
import time
import sys
import os
import logging
from datetime import datetime

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    print("ERROR: python-socketio not available. Install with: pip install python-socketio")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('socketio_history_test')

class SocketIOHistoryTester:
    """Test Socket.IO server history functionality."""
    
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.url = f'http://{host}:{port}'
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.events_received = []
        self.history_received = None
        self.welcome_received = None
        
    async def connect_and_test(self):
        """Connect to the server and test history functionality."""
        
        # Setup event handlers
        @self.sio.event
        async def connect():
            logger.info(f"✅ CONNECTED to Socket.IO server at {self.url}")
            self.connected = True
            
        @self.sio.event  
        async def disconnect():
            logger.info(f"🔌 DISCONNECTED from Socket.IO server")
            self.connected = False
            
        @self.sio.event
        async def connect_error(data):
            logger.error(f"❌ CONNECTION ERROR: {data}")
            
        @self.sio.event
        async def claude_event(data):
            logger.info(f"📨 Received claude_event: {data.get('type', 'unknown')}")
            self.events_received.append(data)
            
        @self.sio.event
        async def history(data):
            logger.info(f"📚 Received HISTORY event!")
            logger.info(f"📄 History data structure: {type(data)}")
            if isinstance(data, dict):
                events = data.get('events', [])
                count = data.get('count', 0)
                total = data.get('total_available', 0)
                logger.info(f"📊 History contains {count} events (out of {total} total available)")
                logger.info(f"📝 Events: {[e.get('type', 'unknown') for e in events]}")
            elif isinstance(data, list):
                logger.info(f"📊 History is a list with {len(data)} events")
                logger.info(f"📝 Events: {[e.get('type', 'unknown') for e in data]}")
            else:
                logger.warning(f"⚠️  Unexpected history format: {data}")
            self.history_received = data
            
        @self.sio.event
        async def welcome(data):
            logger.info(f"👋 Received WELCOME: {data}")
            self.welcome_received = data
            
        @self.sio.event
        async def status(data):
            logger.info(f"📊 Received STATUS: {data}")
            
        # Test connection
        try:
            logger.info(f"🔗 Attempting to connect to {self.url}...")
            await self.sio.connect(self.url)
            
            # Wait for initial events (server should send history automatically)
            logger.info("⏳ Waiting 3 seconds for automatic history transmission...")
            await asyncio.sleep(3)
            
            # Check what we received
            logger.info(f"\n📋 RESULTS AFTER AUTO-TRANSMISSION:")
            logger.info(f"  - Connected: {self.connected}")
            logger.info(f"  - Welcome received: {self.welcome_received is not None}")
            logger.info(f"  - History received: {self.history_received is not None}")
            logger.info(f"  - Claude events received: {len(self.events_received)}")
            
            if self.history_received is None:
                logger.warning("⚠️  NO HISTORY RECEIVED AUTOMATICALLY - Testing manual request...")
                
                # Try requesting history manually
                logger.info("📤 Sending get_history request...")
                await self.sio.emit('get_history', {'limit': 50})
                await asyncio.sleep(2)
                
                logger.info("📤 Sending request_history request...")  
                await self.sio.emit('request_history', {'limit': 50})
                await asyncio.sleep(2)
                
                logger.info(f"\n📋 RESULTS AFTER MANUAL REQUESTS:")
                logger.info(f"  - History received: {self.history_received is not None}")
                
            if self.history_received:
                logger.info(f"✅ HISTORY SUCCESSFULLY RECEIVED!")
                if isinstance(self.history_received, dict):
                    events = self.history_received.get('events', [])
                    logger.info(f"📄 Sample events:")
                    for i, event in enumerate(events[:3]):  # Show first 3 events
                        logger.info(f"  {i+1}. {event.get('type', 'unknown')} - {event.get('timestamp', 'no timestamp')}")
                        if event.get('data'):
                            logger.info(f"     Data: {json.dumps(event['data'], indent=2)[:200]}...")
            else:
                logger.error("❌ NO HISTORY RECEIVED - Server may not have events or transmission is broken")
                
            # Test server health
            logger.info("🏥 Testing server health endpoint...")
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.url}/health") as resp:
                        health_data = await resp.json()
                        logger.info(f"🏥 Server health: {health_data}")
            except Exception as e:
                logger.error(f"❌ Health check failed: {e}")
                
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
            
        finally:
            if self.connected:
                await self.sio.disconnect()
                
        return self.history_received is not None

async def main():
    """Main test function."""
    print("🧪 Socket.IO History Debug Test")
    print("=" * 50)
    
    # Check if server is running
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(('127.0.0.1', 8765))
        if result != 0:
            print("❌ No Socket.IO server running on port 8765")
            print("   Start server with: python -m claude_mpm.services.socketio_server")
            return False
    except Exception as e:
        print(f"❌ Cannot check server status: {e}")
        return False
    finally:
        sock.close()
    
    print("✅ Socket.IO server detected on port 8765")
    print()
    
    # Run the test
    tester = SocketIOHistoryTester()
    success = await tester.connect_and_test()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ TEST PASSED: Event history transmission is working")
    else:
        print("❌ TEST FAILED: Event history transmission is broken")
        print("\nDEBUG TIPS:")
        print("1. Check if the Socket.IO server has events in its event_history deque")
        print("2. Check server logs for _send_event_history method calls")
        print("3. Verify the server's connect handler is calling _send_event_history")
        print("4. Check if there are any server-side exceptions during history transmission")
    
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)