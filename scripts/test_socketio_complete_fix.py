#!/usr/bin/env python3
"""
Comprehensive test to verify Socket.IO broadcasting fix is working.

This test:
1. Starts a Socket.IO server
2. Connects multiple clients to different namespaces
3. Sends events via HTTP POST
4. Verifies events are received by the appropriate clients
5. Reports success/failure
"""

import asyncio
import json
import requests
import time
import threading
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.websocket_server import SocketIOServer

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("❌ python-socketio not available")
    sys.exit(1)


class ComprehensiveSocketIOTest:
    """Complete Socket.IO broadcasting test."""
    
    def __init__(self):
        self.server = None
        self.clients = {}
        self.received_events = []
        self.test_results = {
            'server_started': False,
            'clients_connected': 0,
            'events_sent': 0,
            'events_received': 0,
            'success': False
        }
    
    async def run_test(self):
        """Run the complete test suite."""
        
        print("🧪 COMPREHENSIVE SOCKET.IO BROADCASTING TEST")
        print("=" * 50)
        
        try:
            # Step 1: Start server
            await self._start_server()
            
            # Step 2: Connect clients
            await self._connect_clients()
            
            # Step 3: Send test events
            await self._send_test_events()
            
            # Step 4: Wait and verify
            await self._verify_results()
            
            # Step 5: Report results
            self._report_results()
            
        finally:
            await self._cleanup()
    
    async def _start_server(self):
        """Start the Socket.IO server."""
        
        print("🚀 Step 1: Starting Socket.IO server...")
        
        self.server = SocketIOServer(host="localhost", port=8765)
        
        # Start server in a separate thread
        server_thread = threading.Thread(target=self.server.start, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        for i in range(10):
            try:
                response = requests.get("http://localhost:8765/health", timeout=1)
                if response.status_code == 200:
                    print("✅ Server started successfully")
                    self.test_results['server_started'] = True
                    break
            except requests.exceptions.ConnectionError:
                await asyncio.sleep(0.5)
        else:
            raise Exception("Server failed to start")
    
    async def _connect_clients(self):
        """Connect test clients to different namespaces."""
        
        print("🔌 Step 2: Connecting test clients...")
        
        # Test namespaces
        test_namespaces = ['/hook', '/session', '/memory']
        
        for namespace in test_namespaces:
            try:
                client = socketio.AsyncClient(logger=False, engineio_logger=False)
                
                # Set up event handlers
                @client.event
                async def connect():
                    print(f"✅ Connected to {namespace}")
                    self.test_results['clients_connected'] += 1
                
                # Listen for all events including test_connection
                event_types = ['pre_tool', 'post_tool', 'start', 'end', 'updated', 'loaded', 'test_connection']
                for event_type in event_types:
                    def make_handler(ns, evt):
                        async def handler(data):
                            event_info = {
                                'namespace': ns,
                                'event': evt,
                                'data': data,
                                'timestamp': time.time()
                            }
                            self.received_events.append(event_info)
                            print(f"📨 RECEIVED: {ns}/{evt}")
                            self.test_results['events_received'] += 1
                        return handler
                    
                    client.on(event_type, make_handler(namespace, event_type))
                
                # Connect to the namespace
                await client.connect(f"http://localhost:8765{namespace}")
                self.clients[namespace] = client
                
            except Exception as e:
                print(f"❌ Failed to connect to {namespace}: {e}")
        
        # Wait for connections to stabilize
        await asyncio.sleep(1)
        print(f"🎯 Connected {self.test_results['clients_connected']} clients")
    
    async def _send_test_events(self):
        """Send test events via HTTP POST."""
        
        print("📤 Step 3: Sending test events...")
        
        test_events = [
            {
                "namespace": "/hook",
                "event": "pre_tool",
                "data": {"tool_name": "test_broadcast", "session_id": "test_123"}
            },
            {
                "namespace": "/session", 
                "event": "start",
                "data": {"session_id": "test_123", "launch_method": "test"}
            },
            {
                "namespace": "/memory",
                "event": "updated", 
                "data": {"agent_id": "test_agent", "learning_type": "broadcast_test"}
            }
        ]
        
        for event in test_events:
            try:
                response = requests.post(
                    "http://localhost:8765/emit",
                    json=event,
                    timeout=5.0  # Increased timeout
                )
                
                if response.status_code == 200:
                    print(f"✅ Sent {event['namespace']}/{event['event']}")
                    self.test_results['events_sent'] += 1
                else:
                    print(f"❌ Failed to send {event['namespace']}/{event['event']}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error sending event: {e}")
            
            # Small delay between events
            await asyncio.sleep(0.5)
    
    async def _verify_results(self):
        """Wait for events and verify results."""
        
        print("⏳ Step 4: Waiting for events to be received...")
        
        # Wait for events with timeout
        for i in range(10):  # Wait up to 5 seconds
            if self.test_results['events_received'] >= self.test_results['events_sent']:
                break
            await asyncio.sleep(0.5)
        
        # Analyze results
        if self.test_results['events_received'] >= self.test_results['events_sent']:
            self.test_results['success'] = True
    
    def _report_results(self):
        """Report final test results."""
        
        print("\n📊 TEST RESULTS")
        print("=" * 30)
        print(f"Server Started: {'✅' if self.test_results['server_started'] else '❌'}")
        print(f"Clients Connected: {self.test_results['clients_connected']}")
        print(f"Events Sent: {self.test_results['events_sent']}")
        print(f"Events Received: {self.test_results['events_received']}")
        
        if self.test_results['success']:
            print("\n🎉 SUCCESS: Socket.IO broadcasting is working correctly!")
            print("✅ Events are being properly broadcasted to connected clients")
        else:
            print("\n❌ FAILURE: Broadcasting issue persists")
            print("🔧 Events are not reaching clients properly")
        
        if self.received_events:
            print("\n📨 RECEIVED EVENTS:")
            for event in self.received_events:
                print(f"   - {event['namespace']}/{event['event']}")
    
    async def _cleanup(self):
        """Cleanup connections and server."""
        
        print("\n🧹 Cleaning up...")
        
        # Disconnect clients
        for namespace, client in self.clients.items():
            try:
                await client.disconnect()
            except Exception as e:
                print(f"Error disconnecting from {namespace}: {e}")
        
        # Stop server
        if self.server:
            try:
                self.server.stop()
            except Exception as e:
                print(f"Error stopping server: {e}")
        
        print("✅ Cleanup complete")


async def main():
    """Run the comprehensive test."""
    
    test = ComprehensiveSocketIOTest()
    await test.run_test()
    
    # Return exit code based on success
    return 0 if test.test_results['success'] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())