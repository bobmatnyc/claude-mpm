#!/usr/bin/env python3
"""
Simulate multiple browser tab connections to test the Socket.IO fixes.
"""

import asyncio
import json
import logging
import signal
import sys
import time
import threading
from datetime import datetime
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.socketio_server import SocketIOServer, SOCKETIO_AVAILABLE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserTabSimulator:
    """Simulate multiple browser tabs connecting to Socket.IO server."""
    
    def __init__(self):
        self.server = None
        self.clients = []
        self.running = True
        
    async def simulate_browser_tab(self, tab_id: str, port: int = 8765):
        """Simulate a single browser tab connection."""
        if not SOCKETIO_AVAILABLE:
            logger.error(f"Tab {tab_id}: Socket.IO not available")
            return False
            
        import socketio
        
        try:
            client = socketio.AsyncClient()
            connection_events = []
            received_events = []
            
            @client.event
            async def connect():
                msg = f"Tab {tab_id}: Connected successfully"
                logger.info(msg)
                connection_events.append(("connect", msg))
                
            @client.event
            async def disconnect(reason):
                msg = f"Tab {tab_id}: Disconnected - {reason}"
                logger.info(msg)
                connection_events.append(("disconnect", msg))
                
            @client.event
            async def connect_error(data):
                msg = f"Tab {tab_id}: Connection error - {data}"
                logger.error(msg)
                connection_events.append(("error", msg))
                
            @client.event
            async def welcome(data):
                msg = f"Tab {tab_id}: Welcome - {data.get('message', 'No message')}"
                logger.info(msg)
                received_events.append(("welcome", data))
                
            @client.event
            async def status(data):
                clients_connected = data.get('clients_connected', 0)
                msg = f"Tab {tab_id}: Status - {clients_connected} clients connected"
                logger.info(msg)
                received_events.append(("status", data))
                
            @client.event 
            async def claude_event(data):
                event_type = data.get('type', 'unknown')
                msg = f"Tab {tab_id}: Event - {event_type}"
                logger.info(msg)
                received_events.append(("claude_event", data))
            
            # Connect with query parameters like a real browser
            url = f"http://localhost:{port}"
            logger.info(f"Tab {tab_id}: Connecting to {url}")
            
            await client.connect(url, transports=['websocket', 'polling'])
            
            # Stay connected and simulate user activity
            for i in range(3):
                await asyncio.sleep(2)
                if client.connected:
                    # Simulate user requesting status
                    await client.emit('get_status')
                    logger.info(f"Tab {tab_id}: Requested status update")
                else:
                    logger.warning(f"Tab {tab_id}: Connection lost during activity")
                    break
            
            # Disconnect cleanly
            if client.connected:
                await client.disconnect()
                logger.info(f"Tab {tab_id}: Disconnected cleanly")
            
            # Report results
            logger.info(f"Tab {tab_id}: Connection events: {len(connection_events)}")
            logger.info(f"Tab {tab_id}: Received events: {len(received_events)}")
            
            return len(connection_events) > 0 and any(event[0] == "connect" for event in connection_events)
            
        except Exception as e:
            logger.error(f"Tab {tab_id}: Exception - {e}")
            return False
    
    def start_server(self):
        """Start the Socket.IO server."""
        if not SOCKETIO_AVAILABLE:
            logger.error("Socket.IO packages not available")
            return False
            
        try:
            self.server = SocketIOServer(host="localhost", port=8765)
            self.server.start()
            
            # Generate test events
            def generate_events():
                time.sleep(1)  # Wait for server to start
                event_count = 0
                while self.running and self.server and self.server.running:
                    event_count += 1
                    self.server.broadcast_event("test.simulation", {
                        "event_number": event_count,
                        "message": f"Simulated event #{event_count}",
                        "timestamp": datetime.now().isoformat()
                    })
                    time.sleep(3)  # Send event every 3 seconds
            
            self.event_thread = threading.Thread(target=generate_events, daemon=True)
            self.event_thread.start()
            
            time.sleep(0.5)  # Give server time to start
            return True
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the server."""
        self.running = False
        if self.server:
            self.server.stop()
            self.server = None
    
    async def run_simulation(self):
        """Run the complete browser tab simulation."""
        logger.info("🌐 Starting Browser Tab Connection Simulation")
        logger.info("=" * 60)
        
        # Start server
        if not self.start_server():
            logger.error("❌ Failed to start server")
            return False
        
        logger.info("✅ Server started successfully")
        
        try:
            # Simulate multiple browser tabs connecting simultaneously
            tab_names = ["Tab-A", "Tab-B", "Tab-C", "Tab-D"]
            
            logger.info(f"🚀 Simulating {len(tab_names)} browser tabs connecting...")
            
            # Create concurrent connections like multiple browser tabs
            tasks = [self.simulate_browser_tab(tab_name) for tab_name in tab_names]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful_connections = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ {tab_names[i]}: Exception - {result}")
                elif result:
                    logger.info(f"✅ {tab_names[i]}: Successful connection")
                    successful_connections += 1
                else:
                    logger.error(f"❌ {tab_names[i]}: Failed to connect")
            
            # Summary
            logger.info("=" * 60)
            logger.info("📊 SIMULATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"📈 Successful connections: {successful_connections}/{len(tab_names)}")
            
            if successful_connections == len(tab_names):
                logger.info("🎉 All simulated browser tabs connected successfully!")
                logger.info("✅ Multiple client connection handling is working correctly")
                return True
            elif successful_connections > 0:
                logger.warning(f"⚠️  {len(tab_names) - successful_connections} connection(s) failed")
                return False
            else:
                logger.error("❌ All connections failed")
                return False
                
        finally:
            self.stop_server()
            logger.info("🛑 Server stopped")


def main():
    """Main simulation runner."""
    print("🔧 Socket.IO Multiple Browser Tab Simulation")
    print("=" * 60)
    
    simulator = BrowserTabSimulator()
    
    def signal_handler(sig, frame):
        print("\n🛑 Stopping simulation...")
        simulator.stop_server()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        success = asyncio.run(simulator.run_simulation())
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Simulation interrupted")
        simulator.stop_server()
        return 1
    except Exception as e:
        print(f"❌ Simulation error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())