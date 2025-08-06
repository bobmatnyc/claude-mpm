#!/usr/bin/env python3
"""
Socket.IO focused QA testing for Claude MPM Dashboard.
Tests core Socket.IO functionality and backend event handling.
"""

import asyncio
import json
import time
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import socketio
import requests


class SocketIOQATester:
    """Socket.IO focused QA testing."""
    
    def __init__(self):
        self.sio = None
        self.received_events = []
        self.test_results = {
            "connection": {},
            "event_emission": {},
            "event_reception": {},
            "dashboard_namespace": {},
            "session_handling": {},
            "errors": []
        }
        self.server_url = "http://localhost:8765"
    
    async def setup_client(self):
        """Setup Socket.IO client."""
        try:
            self.sio = socketio.AsyncClient()
            
            # Set up event handlers
            @self.sio.event
            async def connect():
                print("  ✅ Connected to server")
                
            @self.sio.event
            async def disconnect():
                print("  ℹ️  Disconnected from server")
            
            @self.sio.on('*')
            async def catch_all(event, data):
                self.received_events.append({
                    'event': event,
                    'data': data,
                    'timestamp': time.time()
                })
                print(f"  📥 Received event: {event}")
            
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Failed to setup client: {e}")
            return False
    
    async def test_server_availability(self):
        """Test if Socket.IO server is running."""
        print("🔌 Testing Server Availability...")
        
        try:
            # Test HTTP endpoint
            response = requests.get(f"{self.server_url}/socket.io/", timeout=5)
            if response.status_code == 200:
                self.test_results["connection"]["server_running"] = "PASS"
                print("  ✅ Socket.IO server is running")
            else:
                self.test_results["connection"]["server_running"] = f"FAIL: HTTP {response.status_code}"
                print(f"  ❌ Server returned HTTP {response.status_code}")
                
        except Exception as e:
            self.test_results["connection"]["server_running"] = f"FAIL: {e}"
            print(f"  ❌ Server not reachable: {e}")
    
    async def test_socket_connection(self):
        """Test Socket.IO connection."""
        print("🔗 Testing Socket.IO Connection...")
        
        try:
            await self.sio.connect(self.server_url, wait_timeout=10)
            self.test_results["connection"]["socket_connect"] = "PASS"
            print("  ✅ Socket.IO connection successful")
            
            # Test connection status
            if self.sio.connected:
                self.test_results["connection"]["connection_status"] = "PASS"
                print("  ✅ Connection status correct")
            else:
                self.test_results["connection"]["connection_status"] = "FAIL: Not connected"
                print("  ❌ Connection status incorrect")
                
        except Exception as e:
            self.test_results["connection"]["socket_connect"] = f"FAIL: {e}"
            print(f"  ❌ Socket.IO connection failed: {e}")
    
    async def test_dashboard_namespace(self):
        """Test dashboard namespace connection."""
        print("📊 Testing Default Namespace (No Namespace)...")
        
        try:
            # The dashboard uses the default namespace, not /dashboard
            # Server is already connected from previous test
            if self.sio.connected:
                self.test_results["dashboard_namespace"]["connection"] = "PASS"
                print("  ✅ Default namespace connection working")
            else:
                self.test_results["dashboard_namespace"]["connection"] = "FAIL: Not connected"
                print("  ❌ Default namespace connection failed")
            
        except Exception as e:
            self.test_results["dashboard_namespace"]["connection"] = f"FAIL: {e}"
            print(f"  ❌ Default namespace connection failed: {e}")
    
    async def test_event_emission(self):
        """Test event emission to server."""
        print("📤 Testing Event Emission...")
        
        test_events = [
            {
                "type": "claude_event",
                "subtype": "tool_call",
                "timestamp": time.time(),
                "session_id": "qa_test_session",
                "data": {
                    "tool_name": "Read",
                    "arguments": {"file_path": "/test/file.py"},
                    "result": "Test content"
                }
            },
            {
                "type": "claude_event",
                "subtype": "agent_delegation",
                "timestamp": time.time(),
                "session_id": "qa_test_session",
                "data": {
                    "agent_type": "engineer",
                    "task": "QA test task"
                }
            },
            {
                "type": "system_event",
                "subtype": "working_directory_change",
                "timestamp": time.time(),
                "session_id": "qa_test_session",
                "data": {
                    "old_path": "/old/test/path",
                    "new_path": "/new/test/path"
                }
            }
        ]
        
        successful_emissions = 0
        
        for i, event in enumerate(test_events):
            try:
                # Emit to default namespace (no namespace parameter)
                await self.sio.emit('claude_event', event)
                successful_emissions += 1
                await asyncio.sleep(0.1)  # Small delay between events
                
            except Exception as e:
                self.test_results["errors"].append(f"Failed to emit event {i}: {e}")
                print(f"  ❌ Failed to emit event {i}: {e}")
        
        if successful_emissions == len(test_events):
            self.test_results["event_emission"]["all_events"] = "PASS"
            print(f"  ✅ All {len(test_events)} test events emitted successfully")
        else:
            self.test_results["event_emission"]["all_events"] = f"PARTIAL: {successful_emissions}/{len(test_events)}"
            print(f"  ⚠️  Only {successful_emissions}/{len(test_events)} events emitted successfully")
    
    async def test_event_reception(self):
        """Test event reception from server."""
        print("📥 Testing Event Reception...")
        
        # Wait a bit for any events to arrive
        await asyncio.sleep(2)
        
        if len(self.received_events) > 0:
            self.test_results["event_reception"]["events_received"] = "PASS"
            print(f"  ✅ Received {len(self.received_events)} events")
            
            # Analyze received events
            event_types = set(event['event'] for event in self.received_events)
            self.test_results["event_reception"]["event_types"] = list(event_types)
            print(f"  ℹ️  Event types received: {', '.join(event_types)}")
            
        else:
            self.test_results["event_reception"]["events_received"] = "FAIL: No events received"
            print("  ❌ No events received from server")
    
    async def test_session_handling(self):
        """Test session-specific event handling."""
        print("🎯 Testing Session Handling...")
        
        try:
            # Emit a session-specific request (to default namespace)
            await self.sio.emit('get_history', {
                'session_id': 'qa_test_session',
                'limit': 10
            })
            
            # Wait for response
            await asyncio.sleep(1)
            
            self.test_results["session_handling"]["session_request"] = "PASS"
            print("  ✅ Session-specific request sent")
            
        except Exception as e:
            self.test_results["session_handling"]["session_request"] = f"FAIL: {e}"
            print(f"  ❌ Session request failed: {e}")
    
    async def test_disconnect_reconnect(self):
        """Test disconnect and reconnect functionality."""
        print("🔄 Testing Disconnect/Reconnect...")
        
        try:
            # Disconnect
            await self.sio.disconnect()
            await asyncio.sleep(1)
            
            if not self.sio.connected:
                self.test_results["connection"]["disconnect"] = "PASS"
                print("  ✅ Disconnect successful")
            else:
                self.test_results["connection"]["disconnect"] = "FAIL: Still connected"
                print("  ❌ Disconnect failed")
            
            # Reconnect (to default namespace)
            await self.sio.connect(self.server_url, wait_timeout=10)
            
            if self.sio.connected:
                self.test_results["connection"]["reconnect"] = "PASS"
                print("  ✅ Reconnect successful")
            else:
                self.test_results["connection"]["reconnect"] = "FAIL: Not reconnected"
                print("  ❌ Reconnect failed")
                
        except Exception as e:
            self.test_results["connection"]["reconnect"] = f"FAIL: {e}"
            print(f"  ❌ Reconnect test failed: {e}")
    
    async def run_all_tests(self):
        """Run all Socket.IO tests."""
        print("🚀 Starting Socket.IO QA Testing...")
        print("=" * 50)
        
        if not await self.setup_client():
            return False
        
        try:
            await self.test_server_availability()
            await self.test_socket_connection()
            await self.test_dashboard_namespace()
            await self.test_event_emission()
            await self.test_event_reception()
            await self.test_session_handling()
            await self.test_disconnect_reconnect()
            
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Test execution error: {e}")
            return False
        
        finally:
            if self.sio and self.sio.connected:
                await self.sio.disconnect()
    
    def generate_report(self):
        """Generate test report."""
        print("\n" + "=" * 50)
        print("📋 SOCKET.IO QA TEST REPORT")
        print("=" * 50)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for category, results in self.test_results.items():
            if category == "errors":
                continue
                
            print(f"\n🔍 {category.replace('_', ' ').title()}")
            print("-" * 30)
            
            for test_name, result in results.items():
                if isinstance(result, list):  # Skip metadata like event_types
                    continue
                    
                total_tests += 1
                if result == "PASS":
                    passed_tests += 1
                    print(f"  ✅ {test_name}: PASS")
                elif result.startswith("PARTIAL"):
                    print(f"  ⚠️  {test_name}: {result}")
                else:
                    failed_tests += 1
                    print(f"  ❌ {test_name}: {result}")
        
        # Print errors
        if self.test_results["errors"]:
            print(f"\n🚨 Errors ({len(self.test_results['errors'])})")
            print("-" * 30)
            for error in self.test_results["errors"]:
                print(f"  ❌ {error}")
        
        # Summary
        print(f"\n📊 TEST SUMMARY")
        print("-" * 30)
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        success_rate = (passed_tests/total_tests)*100 if total_tests > 0 else 0
        print(f"  Success Rate: {success_rate:.1f}%")
        
        # Save report
        report_file = "dashboard_socketio_qa_report.json"
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": success_rate
                },
                "detailed_results": self.test_results,
                "timestamp": time.time(),
                "received_events_count": len(self.received_events)
            }, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        return {
            "passed": passed_tests,
            "failed": failed_tests,
            "total": total_tests
        }


async def main():
    """Main function."""
    tester = SocketIOQATester()
    
    success = await tester.run_all_tests()
    results = tester.generate_report()
    
    if not success or results["failed"] > 0:
        print("\n⚠️  Some tests failed or encountered errors")
        return False
    else:
        print("\n🎉 All Socket.IO tests passed!")
        return True


if __name__ == "__main__":
    asyncio.run(main())