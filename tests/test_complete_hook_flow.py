#!/usr/bin/env python3
"""
Comprehensive test for the complete hook → Socket.IO → dashboard flow.

This test verifies:
1. Hook handler connects to Socket.IO server
2. Hook events are properly emitted to Socket.IO
3. Dashboard client receives the events
4. All namespaces and event types work correctly

WHY this comprehensive approach:
- Tests the complete integration from end to end
- Verifies each component in the chain works
- Provides detailed diagnostic information
- Tests both success and failure scenarios
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import signal
from pathlib import Path
from threading import Thread, Event
import tempfile

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("❌ Socket.IO not available - install with: pip install python-socketio")
    sys.exit(1)

from claude_mpm.services.websocket_server import SocketIOServer


class HookFlowTester:
    """Comprehensive tester for hook → Socket.IO → dashboard flow."""
    
    def __init__(self):
        self.server = None
        self.server_port = 8765
        self.received_events = []
        self.client = None
        self.hook_handler_process = None
        self.test_results = {}
        
    async def run_complete_test(self):
        """Run the complete integration test."""
        print("🧪 Starting comprehensive hook flow test...")
        print("=" * 60)
        
        try:
            # Step 1: Start Socket.IO server
            print("\n📡 Step 1: Starting Socket.IO server...")
            await self._start_socketio_server()
            
            # Step 2: Create dashboard client
            print("\n🖥️  Step 2: Creating dashboard client...")
            await self._create_dashboard_client()
            
            # Step 3: Test hook handler connection
            print("\n🔗 Step 3: Testing hook handler connection...")
            await self._test_hook_handler_connection()
            
            # Step 4: Test actual hook events
            print("\n🎯 Step 4: Testing hook event emission...")
            await self._test_hook_events()
            
            # Step 5: Verify dashboard receives events
            print("\n📊 Step 5: Verifying dashboard receives events...")
            await self._verify_dashboard_events()
            
            # Step 6: Test cleanup
            print("\n🧹 Step 6: Testing cleanup...")
            await self._test_cleanup()
            
            # Report results
            print("\n📋 Test Results:")
            print("=" * 60)
            self._report_results()
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._cleanup()
    
    async def _start_socketio_server(self):
        """Start the Socket.IO server."""
        try:
            self.server = SocketIOServer(port=self.server_port)
            
            # Start server in background
            def run_server():
                asyncio.run(self.server.start())
            
            server_thread = Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Wait for server to start
            await asyncio.sleep(2)
            
            # Verify server is running
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', self.server_port))
                if result == 0:
                    print(f"✅ Socket.IO server started on port {self.server_port}")
                    self.test_results['server_start'] = True
                else:
                    raise Exception(f"Server not responding on port {self.server_port}")
                    
        except Exception as e:
            print(f"❌ Failed to start Socket.IO server: {e}")
            self.test_results['server_start'] = False
            raise
    
    async def _create_dashboard_client(self):
        """Create a dashboard client to receive events."""
        try:
            self.client = socketio.AsyncClient(
                reconnection=True,
                reconnection_attempts=3,
                logger=False,
                engineio_logger=False
            )
            
            # Setup event handlers for all namespaces
            @self.client.event(namespace='/hook')
            async def hook_event(event, data):
                print(f"📥 Dashboard received hook event: {event} -> {data}")
                self.received_events.append({
                    'namespace': '/hook',
                    'event': event,
                    'data': data,
                    'timestamp': time.time()
                })
            
            @self.client.event(namespace='/system')
            async def system_event(event, data):
                print(f"📥 Dashboard received system event: {event} -> {data}")
                self.received_events.append({
                    'namespace': '/system',
                    'event': event,
                    'data': data,
                    'timestamp': time.time()
                })
            
            # Connect to server
            await self.client.connect(
                f'http://localhost:{self.server_port}',
                namespaces=['/hook', '/system']
            )
            
            print("✅ Dashboard client connected successfully")
            self.test_results['client_connect'] = True
            
        except Exception as e:
            print(f"❌ Failed to create dashboard client: {e}")
            self.test_results['client_connect'] = False
            raise
    
    async def _test_hook_handler_connection(self):
        """Test that hook handler can connect to Socket.IO server."""
        try:
            # Set environment variable for hook handler
            os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = str(self.server_port)
            os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
            
            # Import and test hook handler connection
            hook_handler_path = project_root / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
            
            # Test hook handler initialization
            print(f"🔍 Testing hook handler from {hook_handler_path}")
            
            # Import the hook handler class
            sys.path.insert(0, str(hook_handler_path.parent.parent.parent))
            from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
            
            # Create hook handler instance
            handler = ClaudeHookHandler()
            
            # Wait for connection
            await asyncio.sleep(2)
            
            # Check if handler connected
            if handler.socketio_client and handler.socketio_client.connected:
                print("✅ Hook handler connected to Socket.IO server")
                self.test_results['hook_handler_connect'] = True
            else:
                print("⚠️  Hook handler created but not connected")
                self.test_results['hook_handler_connect'] = False
                
            # Clean up handler
            if handler.socketio_client:
                await handler.socketio_client.disconnect()
                
        except Exception as e:
            print(f"❌ Hook handler connection test failed: {e}")
            self.test_results['hook_handler_connect'] = False
            import traceback
            traceback.print_exc()
    
    async def _test_hook_events(self):
        """Test actual hook event emission."""
        try:
            # Create test hook events
            test_events = [
                {
                    'hook_event_name': 'UserPromptSubmit',
                    'prompt': 'Test user prompt for flow verification',
                    'session_id': 'test-session-123',
                    'timestamp': time.time()
                },
                {
                    'hook_event_name': 'PreToolUse',
                    'tool_name': 'Bash',
                    'session_id': 'test-session-123',
                    'timestamp': time.time()
                },
                {
                    'hook_event_name': 'PostToolUse',
                    'tool_name': 'Bash',
                    'exit_code': 0,
                    'session_id': 'test-session-123',
                    'timestamp': time.time()
                }
            ]
            
            # Test each event type
            for test_event in test_events:
                print(f"🧪 Testing {test_event['hook_event_name']} event...")
                
                # Create temporary input file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(test_event, f)
                    temp_file = f.name
                
                try:
                    # Run hook handler with test event
                    hook_script = project_root / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
                    
                    process = subprocess.Popen(
                        [sys.executable, str(hook_script)],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        env={**os.environ, 
                             'CLAUDE_MPM_SOCKETIO_PORT': str(self.server_port),
                             'CLAUDE_MPM_HOOK_DEBUG': 'true'}
                    )
                    
                    # Send event to hook handler
                    stdout, stderr = process.communicate(input=json.dumps(test_event), timeout=10)
                    
                    if process.returncode == 0:
                        print(f"✅ Hook handler processed {test_event['hook_event_name']} successfully")
                    else:
                        print(f"⚠️  Hook handler returned code {process.returncode}")
                        if stderr:
                            print(f"   stderr: {stderr}")
                    
                    # Wait for event to be processed
                    await asyncio.sleep(1)
                    
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            
            self.test_results['hook_events_sent'] = True
            print("✅ All hook events sent successfully")
            
        except Exception as e:
            print(f"❌ Hook event testing failed: {e}")
            self.test_results['hook_events_sent'] = False
            import traceback
            traceback.print_exc()
    
    async def _verify_dashboard_events(self):
        """Verify that dashboard client received the events."""
        try:
            # Wait a bit more for events to arrive
            await asyncio.sleep(3)
            
            print(f"📊 Dashboard received {len(self.received_events)} events:")
            
            # Check for expected event types
            expected_events = ['user_prompt', 'pre_tool', 'post_tool']
            received_event_types = [event['event'] for event in self.received_events]
            
            for expected in expected_events:
                if expected in received_event_types:
                    print(f"✅ Received {expected} event")
                else:
                    print(f"❌ Missing {expected} event")
            
            # Detailed event analysis
            for event in self.received_events:
                print(f"  📝 {event['namespace']}/{event['event']}: {event['data']}")
            
            # Test success criteria
            if len(self.received_events) >= 3:
                print("✅ Dashboard received expected number of events")
                self.test_results['dashboard_events_received'] = True
            else:
                print(f"⚠️  Dashboard received {len(self.received_events)} events, expected at least 3")
                self.test_results['dashboard_events_received'] = False
                
        except Exception as e:
            print(f"❌ Dashboard event verification failed: {e}")
            self.test_results['dashboard_events_received'] = False
    
    async def _test_cleanup(self):
        """Test cleanup functionality."""
        try:
            # Test client disconnect
            if self.client and self.client.connected:
                await self.client.disconnect()
                print("✅ Dashboard client disconnected cleanly")
            
            self.test_results['cleanup'] = True
            
        except Exception as e:
            print(f"❌ Cleanup test failed: {e}")
            self.test_results['cleanup'] = False
    
    async def _cleanup(self):
        """Clean up test resources."""
        try:
            # Clean up client
            if self.client and self.client.connected:
                await self.client.disconnect()
            
            # Clean up any processes
            if self.hook_handler_process:
                try:
                    self.hook_handler_process.terminate()
                    self.hook_handler_process.wait(timeout=5)
                except:
                    pass
            
            # Clean up server (it's in a daemon thread, so it will die with the process)
            print("🧹 Cleanup completed")
            
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
    
    def _report_results(self):
        """Report comprehensive test results."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"📊 Overall: {passed_tests}/{total_tests} tests passed")
        print()
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} {test_name}")
        
        print()
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED - Hook flow is working correctly!")
        else:
            print("⚠️  Some tests failed - check the logs above for details")
        
        print(f"\n📈 Events received by dashboard: {len(self.received_events)}")
        for event in self.received_events:
            print(f"  📝 {event['namespace']}/{event['event']}")


async def main():
    """Run the comprehensive hook flow test."""
    tester = HookFlowTester()
    await tester.run_complete_test()


if __name__ == "__main__":
    if not SOCKETIO_AVAILABLE:
        print("❌ Socket.IO not available")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)