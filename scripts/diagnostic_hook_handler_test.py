#!/usr/bin/env python3
"""Hook Handler Event Sending Diagnostic.

This script simulates the hook handler's event sending process to diagnose:
1. Socket.IO client connection establishment
2. Authentication with dev-token
3. Event emission to correct namespaces
4. Connection persistence and reconnection

WHY this diagnostic:
- Tests the exact same connection logic as the real hook handler
- Simulates hook events (user_prompt, pre_tool, post_tool)
- Shows detailed connection status and error information
- Validates namespace targeting and event formats
"""

import json
import sys
import time
from datetime import datetime
from typing import Dict, Any

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    print("ERROR: python-socketio package not installed. Run: pip install python-socketio[asyncio_client]")
    sys.exit(1)


class DiagnosticHookHandler:
    """Diagnostic version of the hook handler with detailed logging."""
    
    def __init__(self, server_url: str = "http://localhost:8765"):
        self.server_url = server_url
        self.socketio_client = None
        self.connected = False
        self.connection_attempts = 0
        self.events_sent = 0
        self.errors = []
        
        print(f"🔍 DIAGNOSTIC: Hook Handler Test")
        print(f"🌐 Server URL: {server_url}")
        print(f"📅 Start time: {datetime.now().isoformat()}")
        print("=" * 80)
        
        self._init_socketio_client()
    
    def _init_socketio_client(self):
        """Initialize Socket.IO client with diagnostic logging."""
        try:
            print("🔧 Initializing Socket.IO client...")
            
            self.socketio_client = socketio.Client(
                reconnection=True,
                reconnection_attempts=3,
                reconnection_delay=0.5,
                reconnection_delay_max=2,
                randomization_factor=0.2,
                logger=True,  # Enable Socket.IO client logging
                engineio_logger=True
            )
            
            # Setup detailed event handlers
            @self.socketio_client.event
            def connect():
                self.connected = True
                timestamp = datetime.now().isoformat()
                print(f"✅ CONNECTED to Socket.IO server at {timestamp}")
                print(f"   Server URL: {self.server_url}")
                print(f"   Connection attempts: {self.connection_attempts}")
            
            @self.socketio_client.event
            def disconnect():
                self.connected = False
                timestamp = datetime.now().isoformat()
                print(f"❌ DISCONNECTED from Socket.IO server at {timestamp}")
            
            @self.socketio_client.event
            def connect_error(data):
                self.connected = False
                timestamp = datetime.now().isoformat()
                error_msg = f"Connection error: {data}"
                self.errors.append(error_msg)
                print(f"🚨 CONNECTION ERROR at {timestamp}: {data}")
            
            # Setup namespace-specific handlers
            @self.socketio_client.event(namespace='/hook')
            def connect():
                timestamp = datetime.now().isoformat()
                print(f"✅ CONNECTED to /hook namespace at {timestamp}")
            
            @self.socketio_client.event(namespace='/hook')
            def disconnect():
                timestamp = datetime.now().isoformat()
                print(f"❌ DISCONNECTED from /hook namespace at {timestamp}")
            
            @self.socketio_client.event(namespace='/system')
            def connect():
                timestamp = datetime.now().isoformat()
                print(f"✅ CONNECTED to /system namespace at {timestamp}")
            
            @self.socketio_client.event(namespace='/system')
            def disconnect():
                timestamp = datetime.now().isoformat()
                print(f"❌ DISCONNECTED from /system namespace at {timestamp}")
            
            print("✅ Socket.IO client initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize Socket.IO client: {e}"
            self.errors.append(error_msg)
            print(f"❌ INITIALIZATION ERROR: {error_msg}")
            self.socketio_client = None
    
    def connect_to_server(self):
        """Connect to the Socket.IO server with authentication."""
        if not self.socketio_client:
            print("❌ Cannot connect - Socket.IO client not initialized")
            return False
        
        try:
            self.connection_attempts += 1
            print(f"🔄 Attempting connection #{self.connection_attempts}...")
            
            # Use the same auth data as the real hook handler
            auth_data = {'token': 'dev-token'}
            print(f"🔐 Using auth data: {auth_data}")
            
            # Connect to the same namespaces as the real hook handler
            namespaces = ['/hook', '/system']
            print(f"📡 Connecting to namespaces: {namespaces}")
            
            self.socketio_client.connect(
                self.server_url,
                auth=auth_data,
                namespaces=namespaces,
                wait=True,
                wait_timeout=10
            )
            
            if self.socketio_client.connected:
                print("✅ CONNECTION SUCCESSFUL")
                return True
            else:
                error_msg = "Connection failed - client not connected"
                self.errors.append(error_msg)
                print(f"❌ CONNECTION FAILED: {error_msg}")
                return False
                
        except Exception as e:
            error_msg = f"Connection attempt failed: {e}"
            self.errors.append(error_msg)
            print(f"❌ CONNECTION EXCEPTION: {error_msg}")
            return False
    
    def test_event_emission(self):
        """Test emitting events to different namespaces."""
        if not self.socketio_client or not self.connected:
            print("❌ Cannot test events - not connected to server")
            return
        
        print("\n🧪 TESTING EVENT EMISSION")
        print("=" * 50)
        
        # Test events that the real hook handler sends
        test_events = [
            {
                'namespace': '/hook',
                'event': 'user_prompt',
                'data': {
                    'prompt': 'Test user prompt for diagnostic',
                    'session_id': 'diagnostic-session-123',
                    'timestamp': datetime.now().isoformat()
                }
            },
            {
                'namespace': '/hook', 
                'event': 'pre_tool',
                'data': {
                    'tool_name': 'DiagnosticTool',
                    'session_id': 'diagnostic-session-123',
                    'timestamp': datetime.now().isoformat()
                }
            },
            {
                'namespace': '/hook',
                'event': 'post_tool', 
                'data': {
                    'tool_name': 'DiagnosticTool',
                    'exit_code': 0,
                    'session_id': 'diagnostic-session-123',
                    'timestamp': datetime.now().isoformat()
                }
            },
            {
                'namespace': '/system',
                'event': 'diagnostic_ping',
                'data': {
                    'message': 'Hook handler diagnostic ping',
                    'timestamp': datetime.now().isoformat()
                }
            }
        ]
        
        for i, test_event in enumerate(test_events, 1):
            try:
                namespace = test_event['namespace']
                event = test_event['event']
                data = test_event['data']
                
                print(f"📤 Test {i}: Emitting {namespace}/{event}")
                print(f"   Data: {json.dumps(data, indent=2)[:200]}...")
                
                self.socketio_client.emit(event, data, namespace=namespace)
                self.events_sent += 1
                
                print(f"   ✅ Event emitted successfully")
                time.sleep(0.5)  # Small delay between events
                
            except Exception as e:
                error_msg = f"Failed to emit event {i}: {e}"
                self.errors.append(error_msg)
                print(f"   ❌ Event emission failed: {error_msg}")
    
    def test_continuous_events(self, duration_seconds: int = 30):
        """Send continuous events to test connection persistence."""
        if not self.socketio_client or not self.connected:
            print("❌ Cannot test continuous events - not connected")
            return
        
        print(f"\n🔄 TESTING CONTINUOUS EVENTS for {duration_seconds} seconds")
        print("=" * 60)
        
        start_time = time.time()
        event_counter = 0
        
        while time.time() - start_time < duration_seconds:
            try:
                event_counter += 1
                timestamp = datetime.now().isoformat()
                
                # Alternate between different event types
                if event_counter % 3 == 0:
                    namespace, event = '/hook', 'user_prompt'
                    data = {
                        'prompt': f'Continuous test prompt #{event_counter}',
                        'session_id': 'continuous-test',
                        'timestamp': timestamp
                    }
                elif event_counter % 3 == 1:
                    namespace, event = '/hook', 'pre_tool'
                    data = {
                        'tool_name': f'ContinuousTestTool_{event_counter}',
                        'session_id': 'continuous-test',
                        'timestamp': timestamp
                    }
                else:
                    namespace, event = '/hook', 'post_tool'
                    data = {
                        'tool_name': f'ContinuousTestTool_{event_counter}',
                        'exit_code': event_counter % 2,
                        'session_id': 'continuous-test',
                        'timestamp': timestamp
                    }
                
                self.socketio_client.emit(event, data, namespace=namespace)
                self.events_sent += 1
                
                print(f"📤 Event #{event_counter}: {namespace}/{event} - ✅")
                time.sleep(1)  # 1 second interval
                
            except Exception as e:
                error_msg = f"Continuous event #{event_counter} failed: {e}"
                self.errors.append(error_msg)
                print(f"❌ Event #{event_counter} failed: {error_msg}")
                time.sleep(1)
        
        print(f"🏁 Continuous test completed: {event_counter} events sent")
    
    def disconnect_from_server(self):
        """Disconnect from the Socket.IO server."""
        if self.socketio_client and self.connected:
            try:
                print("🔌 Disconnecting from server...")
                self.socketio_client.disconnect()
                print("✅ Disconnected successfully")
            except Exception as e:
                error_msg = f"Disconnect error: {e}"
                self.errors.append(error_msg)
                print(f"❌ DISCONNECT ERROR: {error_msg}")
    
    def print_diagnostic_summary(self):
        """Print diagnostic summary."""
        print("\n" + "=" * 80)
        print("📊 DIAGNOSTIC SUMMARY")
        print("=" * 80)
        print(f"🔗 Connection attempts: {self.connection_attempts}")
        print(f"📡 Currently connected: {self.connected}")
        print(f"📤 Events sent: {self.events_sent}")
        print(f"🚨 Errors encountered: {len(self.errors)}")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")
        
        print(f"\n⏰ Test completed at: {datetime.now().isoformat()}")


def main():
    """Main diagnostic function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hook Handler Socket.IO Diagnostic")
    parser.add_argument('--url', default='http://localhost:8765', help='Socket.IO server URL')
    parser.add_argument('--continuous', type=int, default=0, help='Run continuous events for N seconds')
    args = parser.parse_args()
    
    handler = DiagnosticHookHandler(args.url)
    
    try:
        # Test basic connection
        if handler.connect_to_server():
            # Test event emission
            handler.test_event_emission()
            
            # Optional continuous testing
            if args.continuous > 0:
                handler.test_continuous_events(args.continuous)
        
    except KeyboardInterrupt:
        print("\n🛑 Diagnostic interrupted by user")
    except Exception as e:
        print(f"❌ Diagnostic error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        handler.disconnect_from_server()
        handler.print_diagnostic_summary()


if __name__ == "__main__":
    main()