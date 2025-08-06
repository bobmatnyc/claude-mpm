#!/usr/bin/env python3
"""
Complete test of the Socket.IO broadcasting solution.

This test verifies that the real Claude MPM server with our fixes
can properly broadcast events to clients connecting to namespaces.
"""

import asyncio
import requests
import socketio
import time
import threading
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.websocket_server import SocketIOServer


class CompleteSolutionTest:
    """Test the complete Socket.IO solution."""
    
    def __init__(self):
        self.server = None
        self.received_events = []
        self.clients = {}
        
    async def run_test(self):
        """Run the complete solution test."""
        
        print("🎯 COMPLETE SOCKET.IO SOLUTION TEST")
        print("=" * 42)
        
        try:
            # Step 1: Start the real Claude MPM server
            await self._start_claude_mpm_server()
            
            # Step 2: Connect clients using correct namespace approach
            await self._connect_namespace_clients()
            
            # Step 3: Send events via the real HTTP endpoint
            await self._send_real_events()
            
            # Step 4: Verify events are received
            await self._verify_solution()
            
            # Step 5: Report final results
            self._report_final_results()
            
        finally:
            await self._cleanup()
    
    async def _start_claude_mpm_server(self):
        """Start the real Claude MPM Socket.IO server."""
        
        print("🚀 Starting Claude MPM Socket.IO server...")
        
        self.server = SocketIOServer(host="localhost", port=8765)
        
        # Start in background thread
        server_thread = threading.Thread(target=self.server.start, daemon=True)
        server_thread.start()
        
        # Wait for server startup
        for i in range(15):
            try:
                response = requests.get("http://localhost:8765/health", timeout=1)
                if response.status_code == 200:
                    print("✅ Claude MPM server started successfully")
                    return
            except:
                await asyncio.sleep(0.5)
        
        raise Exception("Claude MPM server failed to start")
    
    async def _connect_namespace_clients(self):
        """Connect clients to namespaces using the correct approach."""
        
        print("🔌 Connecting clients to namespaces...")
        
        # Test the key namespaces that hook events use
        test_namespaces = ['/hook', '/session', '/memory']
        
        for namespace in test_namespaces:
            print(f"🎯 Connecting to {namespace}...")
            
            client = socketio.AsyncClient()
            
            # Register namespace-specific event handlers (the key fix!)
            @client.event(namespace=namespace)
            async def connect():
                print(f"✅ Connected to {namespace}")
            
            @client.event(namespace=namespace) 
            async def test_connection(data):
                print(f"📨 Test connection from {namespace}: {data}")
                self.received_events.append((namespace, 'test_connection', data))
            
            # Register event handlers for actual events using the proper approach
            event_types = ['pre_tool', 'post_tool', 'start', 'end', 'updated', 'loaded']
            for event_type in event_types:
                # This is the correct way to register namespace-specific handlers
                def make_handler(ns, evt):
                    async def handler(data):
                        print(f"📨 RECEIVED {evt} from {ns}: {data}")
                        self.received_events.append((ns, evt, data))
                    return handler
                
                # Register using the client.on method with namespace parameter
                client.on(event_type, make_handler(namespace, event_type), namespace=namespace)
            
            # Connect to the namespace
            await client.connect('http://localhost:8765', namespaces=[namespace])
            self.clients[namespace] = client
            
            # Small delay between connections
            await asyncio.sleep(0.3)
        
        print(f"🎯 Connected {len(self.clients)} namespace clients")
        await asyncio.sleep(1)  # Let connections stabilize
    
    async def _send_real_events(self):
        """Send events via the real Claude MPM HTTP endpoint."""
        
        print("📤 Sending events via Claude MPM HTTP endpoint...")
        
        # Test events that match real hook usage
        test_events = [
            {
                "namespace": "/hook",
                "event": "pre_tool",
                "data": {
                    "tool_name": "Bash",
                    "session_id": "solution_test_123",
                    "timestamp": time.time()
                }
            },
            {
                "namespace": "/session",
                "event": "start",
                "data": {
                    "session_id": "solution_test_123",
                    "launch_method": "test_solution",
                    "working_directory": "/test/path"
                }
            },
            {
                "namespace": "/memory",
                "event": "updated",
                "data": {
                    "agent_id": "solution_test_agent",
                    "learning_type": "broadcast_success",
                    "content": "Socket.IO broadcasting fixed!"
                }
            }
        ]
        
        for event in test_events:
            try:
                response = requests.post(
                    "http://localhost:8765/emit",
                    json=event,
                    timeout=10.0  # Generous timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Sent {event['namespace']}/{event['event']}: {result['message']}")
                else:
                    print(f"❌ Failed to send {event['namespace']}/{event['event']}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error sending event: {e}")
            
            # Delay between events
            await asyncio.sleep(1)
    
    async def _verify_solution(self):
        """Wait and verify the solution works."""
        
        print("⏳ Waiting for events to be received...")
        
        # Wait for events with timeout
        for i in range(15):  # Wait up to 15 seconds
            if len(self.received_events) >= 3:  # At least our 3 test events
                break
            await asyncio.sleep(1)
            if i % 3 == 0:
                print(f"   ... {len(self.received_events)} events received so far")
    
    def _report_final_results(self):
        """Report the final test results."""
        
        print(f"\n🎯 FINAL SOLUTION TEST RESULTS")
        print("=" * 40)
        print(f"📊 Total events received: {len(self.received_events)}")
        
        if self.received_events:
            print("\n📨 RECEIVED EVENTS:")
            for namespace, event_type, data in self.received_events:
                print(f"   ✓ {namespace}/{event_type}")
        
        # Check for our test events
        expected_events = [
            ('/hook', 'pre_tool'),
            ('/session', 'start'), 
            ('/memory', 'updated')
        ]
        
        received_event_types = [(ns, evt) for ns, evt, data in self.received_events]
        success_count = sum(1 for expected in expected_events if expected in received_event_types)
        
        print(f"\n🎯 Success Rate: {success_count}/{len(expected_events)} expected events received")
        
        if success_count == len(expected_events):
            print("\n🎉 🎉 🎉 SUCCESS! 🎉 🎉 🎉")
            print("✅ Socket.IO broadcasting is now working correctly!")
            print("✅ Hook events will reach the dashboard!")
            print("✅ The broadcasting issue is FIXED!")
        elif success_count > 0:
            print(f"\n🟡 PARTIAL SUCCESS: {success_count} out of {len(expected_events)} events received")
            print("🔧 Some events are getting through - the fix is working but may need refinement")
        else:
            print("\n❌ FAILURE: No expected events received")
            print("🔧 The broadcasting issue persists")
    
    async def _cleanup(self):
        """Cleanup connections and server."""
        
        print("\n🧹 Cleaning up...")
        
        # Disconnect clients
        for namespace, client in self.clients.items():
            try:
                await client.disconnect()
                print(f"🔌 Disconnected from {namespace}")
            except Exception as e:
                print(f"❌ Error disconnecting from {namespace}: {e}")
        
        # Stop server
        if self.server:
            try:
                self.server.stop()
                print("🛑 Server stopped")
            except Exception as e:
                print(f"❌ Error stopping server: {e}")


async def main():
    """Run the complete solution test."""
    test = CompleteSolutionTest()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())