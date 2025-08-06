#!/usr/bin/env python3
"""
Test dashboard integration with the fixed Socket.IO server.

This test starts the server and simulates hook events
to verify the dashboard would receive them.
"""

import asyncio
import requests
import socketio
import threading
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.websocket_server import SocketIOServer


class DashboardIntegrationTest:
    """Test dashboard integration."""
    
    def __init__(self):
        self.server = None
        self.received_events = []
        
    async def run_test(self):
        """Run dashboard integration test."""
        
        print("📊 DASHBOARD INTEGRATION TEST")
        print("=" * 35)
        
        try:
            # Start Claude MPM server
            await self._start_server()
            
            # Connect as dashboard (multiple namespaces)
            await self._connect_as_dashboard()
            
            # Simulate hook events (what hook handlers send)
            await self._simulate_hook_events()
            
            # Verify results
            self._report_results()
            
        finally:
            await self._cleanup()
    
    async def _start_server(self):
        """Start the Claude MPM server."""
        
        print("🚀 Starting Claude MPM server...")
        self.server = SocketIOServer(host="localhost", port=8765)
        
        server_thread = threading.Thread(target=self.server.start, daemon=True)
        server_thread.start()
        
        # Wait for startup
        for i in range(10):
            try:
                response = requests.get("http://localhost:8765/health", timeout=1)
                if response.status_code == 200:
                    print("✅ Server ready for dashboard connections")
                    return
            except:
                await asyncio.sleep(0.5)
        
        raise Exception("Server failed to start")
    
    async def _connect_as_dashboard(self):
        """Connect clients as the dashboard would (multiple namespaces)."""
        
        print("🔌 Connecting dashboard clients...")
        
        # Dashboard connects to all these namespaces
        dashboard_namespaces = ['/system', '/session', '/claude', '/agent', '/hook', '/todo', '/memory', '/log']
        self.clients = {}
        
        for namespace in dashboard_namespaces:
            client = socketio.AsyncClient()
            
            # Dashboard event handlers (like in the HTML)
            @client.event(namespace=namespace)
            async def connect():
                print(f"✅ Dashboard connected to {namespace}")
            
            # Listen for the events the dashboard expects
            event_types = ['start', 'end', 'status_changed', 'output', 'task_delegated',
                          'user_prompt', 'pre_tool', 'post_tool', 'updated', 'loaded',
                          'created', 'injected', 'message', 'test_connection']
            
            for event_type in event_types:
                def make_handler(ns, evt):
                    async def handler(data):
                        print(f"📊 DASHBOARD received {evt} from {ns}")
                        self.received_events.append((ns, evt, data))
                    return handler
                
                client.on(event_type, make_handler(namespace, event_type), namespace=namespace)
            
            # Connect
            await client.connect('http://localhost:8765', namespaces=[namespace])
            self.clients[namespace] = client
            
            await asyncio.sleep(0.1)  # Small delay between connections
        
        print(f"🎯 Dashboard connected to {len(self.clients)} namespaces")
        await asyncio.sleep(1)
    
    async def _simulate_hook_events(self):
        """Simulate the events that hook handlers would send."""
        
        print("📤 Simulating hook events...")
        
        # These are the exact events hook handlers send
        hook_events = [
            {
                "namespace": "/hook",
                "event": "user_prompt",
                "data": {
                    "prompt": "Test user prompt from hook",
                    "session_id": "dashboard_test_123"
                }
            },
            {
                "namespace": "/hook", 
                "event": "pre_tool",
                "data": {
                    "tool_name": "Bash",
                    "session_id": "dashboard_test_123"
                }
            },
            {
                "namespace": "/hook",
                "event": "post_tool", 
                "data": {
                    "tool_name": "Bash",
                    "exit_code": 0,
                    "session_id": "dashboard_test_123"
                }
            },
            {
                "namespace": "/memory",
                "event": "updated",
                "data": {
                    "agent_id": "test_agent",
                    "learning_type": "success",
                    "content": "Dashboard integration test completed",
                    "section": "learnings"
                }
            }
        ]
        
        for event in hook_events:
            try:
                response = requests.post(
                    "http://localhost:8765/emit",
                    json=event,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    print(f"✅ Sent {event['namespace']}/{event['event']}")
                else:
                    print(f"❌ Failed to send {event['namespace']}/{event['event']}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
            
            await asyncio.sleep(0.5)
        
        # Wait for events to be processed
        await asyncio.sleep(2)
    
    def _report_results(self):
        """Report integration test results."""
        
        print(f"\n📊 DASHBOARD INTEGRATION RESULTS")
        print("=" * 40)
        
        # Filter out test_connection events (sent during connection)
        hook_events = [(ns, evt, data) for ns, evt, data in self.received_events 
                      if evt != 'test_connection']
        
        print(f"📨 Hook events received by dashboard: {len(hook_events)}")
        
        if hook_events:
            print("\n✅ DASHBOARD RECEIVED:")
            for namespace, event_type, data in hook_events:
                print(f"   - {namespace}/{event_type}")
        
        expected_events = ['user_prompt', 'pre_tool', 'post_tool', 'updated']
        received_event_types = [evt for ns, evt, data in hook_events]
        success_count = sum(1 for expected in expected_events if expected in received_event_types)
        
        print(f"\n🎯 Success Rate: {success_count}/{len(expected_events)} expected hook events")
        
        if success_count == len(expected_events):
            print("\n🎉 DASHBOARD INTEGRATION SUCCESS! 🎉")
            print("✅ The dashboard will now receive hook events correctly!")
            print("✅ Users will see real-time hook activity!")
        elif success_count > 0:
            print(f"\n🟡 PARTIAL SUCCESS: {success_count} events received")
        else:
            print("\n❌ INTEGRATION FAILED: No hook events received")
    
    async def _cleanup(self):
        """Cleanup connections."""
        
        print("\n🧹 Cleaning up...")
        
        if hasattr(self, 'clients'):
            for namespace, client in self.clients.items():
                try:
                    await client.disconnect()
                except Exception as e:
                    print(f"❌ Error disconnecting from {namespace}: {e}")
        
        if self.server:
            try:
                self.server.stop()
            except Exception as e:
                print(f"❌ Error stopping server: {e}")


async def main():
    """Run the dashboard integration test."""
    test = DashboardIntegrationTest()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())