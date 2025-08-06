#!/usr/bin/env python3
"""
Test script to check Socket.IO server logs and debug automatic history transmission.

WHY: The server should automatically call _send_event_history on client connection,
but our previous test shows this isn't working. This script adds more detailed
debugging to understand what's happening in the connection flow.
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

# Configure logging to see more detail
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('server_logs_debug')

class DetailedSocketIOTester:
    """Detailed Socket.IO server testing with enhanced logging."""
    
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.url = f'http://{host}:{port}'
        self.sio = socketio.AsyncClient(logger=True, engineio_logger=True)  # Enable logging
        self.connected = False
        self.events_received = []
        self.history_received = None
        
    async def test_automatic_history(self):
        """Test automatic history transmission on connection."""
        
        # Setup handlers to track everything
        @self.sio.event
        async def connect():
            logger.info(f"🔗 CLIENT: Connected to server")
            self.connected = True
            
        @self.sio.event  
        async def disconnect():
            logger.info(f"🔌 CLIENT: Disconnected")
            self.connected = False
            
        @self.sio.event
        async def history(data):
            logger.info(f"📚 CLIENT: Received history event!")
            logger.info(f"     Data type: {type(data)}")
            
            if isinstance(data, dict):
                events = data.get('events', [])
                count = data.get('count', 0) 
                total = data.get('total_available', 0)
                logger.info(f"     Events in history: {len(events)}")
                logger.info(f"     Count reported: {count}")
                logger.info(f"     Total available: {total}")
                
                # Show first few event types
                if events:
                    event_types = [e.get('type', 'unknown') for e in events[:5]]
                    logger.info(f"     First 5 event types: {event_types}")
                    
            self.history_received = data
            
        @self.sio.event
        async def welcome(data):
            logger.info(f"👋 CLIENT: Received welcome")
            
        @self.sio.event  
        async def status(data):
            logger.info(f"📊 CLIENT: Received status")
            
        @self.sio.event
        async def claude_event(data):
            logger.info(f"📨 CLIENT: Received claude_event: {data.get('type', 'unknown')}")
            
        # Connect and wait for automatic events
        logger.info(f"🔗 Connecting to {self.url}...")
        await self.sio.connect(self.url)
        
        logger.info("⏳ Waiting 5 seconds for automatic events...")
        await asyncio.sleep(5)
        
        logger.info(f"\n📋 AUTOMATIC TRANSMISSION RESULTS:")
        logger.info(f"  - Connected: {self.connected}")
        logger.info(f"  - History received automatically: {self.history_received is not None}")
        
        if self.history_received is None:
            logger.warning("❌ NO AUTOMATIC HISTORY RECEIVED")
            logger.info("📤 Testing manual history request...")
            
            await self.sio.emit('get_history', {'limit': 10})
            await asyncio.sleep(2)
            
            if self.history_received:
                logger.info("✅ Manual history request worked")
                if isinstance(self.history_received, dict):
                    events = self.history_received.get('events', [])
                    logger.info(f"   Manual request returned {len(events)} events")
            else:
                logger.error("❌ Even manual history request failed")
        else:
            logger.info("✅ AUTOMATIC HISTORY TRANSMISSION WORKING")
            
        await self.sio.disconnect()
        return self.history_received is not None

async def check_server_health():
    """Check server health and event storage."""
    logger.info("🏥 Checking server health...")
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8765/health') as resp:
                health = await resp.json()
                logger.info(f"Server health: {health}")
                
                clients = health.get('clients_connected', 0)
                logger.info(f"Current clients connected: {clients}")
                
    except Exception as e:
        logger.error(f"Health check failed: {e}")

async def main():
    """Main test."""
    print("🔍 Detailed Socket.IO Server Debug Test")
    print("=" * 60)
    
    # Check server availability
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(('127.0.0.1', 8765))
        if result != 0:
            print("❌ No Socket.IO server running on port 8765")
            return False
    except Exception as e:
        print(f"❌ Cannot check server: {e}")
        return False
    finally:
        sock.close()
    
    print("✅ Socket.IO server detected")
    
    # Check health first
    await check_server_health()
    
    print("\n🧪 Testing automatic history transmission...")
    
    # Run detailed test
    tester = DetailedSocketIOTester()
    success = await tester.test_automatic_history()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ History transmission working")
    else:
        print("❌ History transmission broken")
        print("\nSUGGESTED FIXES:")
        print("1. Check server logs for exceptions during _send_event_history")
        print("2. Verify event_history deque actually contains events")
        print("3. Check if the connect handler is executing _send_event_history")
        print("4. Look for any async/await issues in the connection handler")
    
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