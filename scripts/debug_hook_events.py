#!/usr/bin/env python3
"""
Debug script to investigate hook events not appearing in the dashboard.

This script will:
1. Test the socket.io server directly
2. Send various hook event formats
3. Monitor browser console for events
4. Check event transformation
5. Identify where hook events are being lost
"""

import asyncio
import socketio
import json
import time
import subprocess
import sys
from datetime import datetime, timezone

# Add src to path for importing claude_mpm modules
sys.path.insert(0, '/Users/masa/Projects/claude-mpm/src')

try:
    from claude_mpm.services.socketio.server.core import SocketIOServerCore
    from claude_mpm.services.socketio.handlers.connection import ConnectionHandler
    from claude_mpm.services.socketio.server.broadcaster import EventBroadcaster
except ImportError as e:
    print(f"Warning: Failed to import claude_mpm modules: {e}")
    print("Continuing with basic debug functionality...")

class HookEventDebugger:
    def __init__(self):
        self.sio_client = None
        self.server_port = 8765
        self.received_events = []
        
    async def connect_to_server(self):
        """Connect to the socket.io server"""
        print(f"Connecting to socket.io server at http://localhost:{self.server_port}")
        
        self.sio_client = socketio.AsyncClient()
        
        # Set up event handlers
        @self.sio_client.event
        async def connect():
            print("✅ Connected to socket.io server")
            
        @self.sio_client.event
        async def disconnect():
            print("❌ Disconnected from socket.io server")
            
        @self.sio_client.event
        async def claude_event(data):
            print(f"📨 Received claude_event: {json.dumps(data, indent=2)}")
            self.received_events.append(('claude_event', data))
            
        # Legacy event handlers
        @self.sio_client.event
        async def hook_pre(data):
            print(f"📨 Received hook.pre: {json.dumps(data, indent=2)}")
            self.received_events.append(('hook.pre', data))
            
        @self.sio_client.event 
        async def hook_post(data):
            print(f"📨 Received hook.post: {json.dumps(data, indent=2)}")
            self.received_events.append(('hook.post', data))
            
        try:
            await self.sio_client.connect(f'http://localhost:{self.server_port}')
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    async def send_test_events(self):
        """Send various test hook events to see which format works"""
        if not self.sio_client or not self.sio_client.connected:
            print("❌ Not connected to server")
            return
            
        print("\n🧪 Sending test hook events...")
        
        # Test 1: Standard hook event format
        test_hook_1 = {
            'type': 'hook.user_prompt',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': {
                'prompt': 'Debug test 1 - standard format',
                'session_id': 'debug-session-1'
            }
        }
        print(f"🔬 Test 1 - Standard format: {json.dumps(test_hook_1, indent=2)}")
        await self.sio_client.emit('claude_event', test_hook_1)
        await asyncio.sleep(1)
        
        # Test 2: Pre-tool hook event
        test_hook_2 = {
            'type': 'hook.pre_tool',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': {
                'tool_name': 'debug_tool',
                'parameters': {'test': 'value'},
                'session_id': 'debug-session-2'
            }
        }
        print(f"🔬 Test 2 - Pre-tool format: {json.dumps(test_hook_2, indent=2)}")
        await self.sio_client.emit('claude_event', test_hook_2)
        await asyncio.sleep(1)
        
        # Test 3: Legacy format with event field
        test_hook_3 = {
            'event': 'UserPrompt',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'prompt': 'Debug test 3 - legacy format',
            'session_id': 'debug-session-3'
        }
        print(f"🔬 Test 3 - Legacy format: {json.dumps(test_hook_3, indent=2)}")
        await self.sio_client.emit('claude_event', test_hook_3)
        await asyncio.sleep(1)
        
        # Test 4: Direct hook.pre emission
        test_hook_4 = {
            'prompt': 'Debug test 4 - direct hook.pre',
            'session_id': 'debug-session-4'
        }
        print(f"🔬 Test 4 - Direct hook.pre: {json.dumps(test_hook_4, indent=2)}")
        await self.sio_client.emit('hook.pre', test_hook_4)
        await asyncio.sleep(1)
        
        print(f"\n📊 Sent 4 test events. Received {len(self.received_events)} events.")
        
    def check_server_running(self):
        """Check if socket.io server is running"""
        try:
            import requests
            response = requests.get(f'http://localhost:{self.server_port}', timeout=2)
            if response.status_code == 200:
                print(f"✅ Socket.io server is running on port {self.server_port}")
                return True
        except Exception as e:
            print(f"❌ Socket.io server not responding on port {self.server_port}: {e}")
            return False
        
    def start_dashboard_server_if_needed(self):
        """Start the dashboard server if it's not running"""
        if not self.check_server_running():
            print("🚀 Starting dashboard server...")
            try:
                subprocess.Popen([
                    sys.executable, "-m", "claude_mpm.dashboard.app"
                ], cwd="/Users/masa/Projects/claude-mpm")
                print("⏳ Waiting for server to start...")
                time.sleep(3)
                
                if self.check_server_running():
                    print("✅ Dashboard server started successfully")
                    return True
                else:
                    print("❌ Dashboard server failed to start")
                    return False
            except Exception as e:
                print(f"❌ Failed to start dashboard server: {e}")
                return False
        return True
    
    async def test_real_hook_generation(self):
        """Test if real claude-mpm commands generate hook events"""
        print("\n🔧 Testing real hook event generation...")
        
        # Run a simple claude-mpm command that should generate hooks
        try:
            result = subprocess.run([
                sys.executable, "-m", "claude_mpm.cli.main", "agents", "list"
            ], cwd="/Users/masa/Projects/claude-mpm", capture_output=True, text=True, timeout=10)
            
            print(f"📝 Command output: {result.stdout}")
            if result.stderr:
                print(f"⚠️  Command errors: {result.stderr}")
                
            # Wait a moment for events to propagate
            await asyncio.sleep(2)
            
            print(f"📊 Events received after real command: {len(self.received_events)}")
            
        except subprocess.TimeoutExpired:
            print("⏰ Command timed out")
        except Exception as e:
            print(f"❌ Failed to run command: {e}")
    
    def analyze_event_transformation(self):
        """Analyze how events are being transformed"""
        print("\n🔍 Analyzing event transformation...")
        
        for event_type, event_data in self.received_events:
            print(f"\n📥 Event type: {event_type}")
            print(f"📄 Event data: {json.dumps(event_data, indent=2)}")
            
            # Check if this would pass dashboard filters
            event_type_field = event_data.get('type', '')
            event_subtype = event_data.get('subtype', '')
            
            print(f"🏷️  Type field: '{event_type_field}'")
            print(f"🏷️  Subtype field: '{event_subtype}'")
            
            # Check if it's a hook event
            is_hook = (
                event_type_field.startswith('hook.') or 
                event_type_field == 'hook' or
                'hook' in event_type.lower()
            )
            print(f"🎣 Is hook event: {is_hook}")
    
    def print_dashboard_debug_instructions(self):
        """Print instructions for debugging in the browser"""
        print("\n🌐 Dashboard Debug Instructions:")
        print("1. Open http://localhost:8765/ in your browser")
        print("2. Open DevTools (F12) and go to Console tab")
        print("3. Look for messages like:")
        print("   - 'Received claude_event: ...'")
        print("   - 'Transformed event: ...'")
        print("   - Hook events being filtered out")
        print("4. Check the Events tab to see if hook events appear")
        print("5. Look for any JavaScript errors that might prevent event display")
        print("\n💡 If events aren't appearing:")
        print("   - Check if they're being filtered by type")
        print("   - Look for JavaScript parsing errors")
        print("   - Verify event transformation is working correctly")
        
    async def run_debug_session(self):
        """Run the complete debug session"""
        print("🔍 Starting Hook Event Debug Session")
        print("=" * 50)
        
        # Check server
        if not self.start_dashboard_server_if_needed():
            return
            
        # Connect to server
        if not await self.connect_to_server():
            return
            
        # Send test events
        await self.send_test_events()
        
        # Test real hook generation
        await self.test_real_hook_generation()
        
        # Analyze results
        self.analyze_event_transformation()
        
        # Print debug instructions
        self.print_dashboard_debug_instructions()
        
        # Keep connection open for manual testing
        print("\n⏳ Keeping connection open for 30 seconds for manual testing...")
        await asyncio.sleep(30)
        
        if self.sio_client:
            await self.sio_client.disconnect()
        
        print("\n📊 Debug Session Summary:")
        print(f"   - Events sent: 4 test events + real command")
        print(f"   - Events received: {len(self.received_events)}")
        
        if len(self.received_events) == 0:
            print("🚨 NO EVENTS RECEIVED - Possible issues:")
            print("   1. Socket.io server not properly broadcasting events")
            print("   2. Hook service not sending events to socket.io")
            print("   3. Event format mismatch")
        elif len(self.received_events) < 4:
            print("⚠️  SOME EVENTS MISSING - Check event format compatibility")
        else:
            print("✅ EVENTS RECEIVED - Issue likely in dashboard JavaScript")

async def main():
    debugger = HookEventDebugger()
    await debugger.run_debug_session()

if __name__ == "__main__":
    asyncio.run(main())