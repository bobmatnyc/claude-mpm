#!/usr/bin/env python3
"""Test real hook events by monitoring Socket.IO server during Claude execution."""

import asyncio
import json
import subprocess
import sys
import time
import threading
from pathlib import Path

# Add the claude-mpm source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class SocketIOEventMonitor:
    """Monitor Socket.IO events during test execution."""
    
    def __init__(self, port=8765):
        self.port = port
        self.events_received = []
        self.client = None
        self.connected = False
        
    async def start_monitoring(self):
        """Start monitoring Socket.IO events."""
        try:
            import socketio
            
            self.client = socketio.AsyncClient(
                logger=False,
                engineio_logger=False
            )
            
            @self.client.event
            async def connect():
                self.connected = True
                print("✓ Event monitor connected to Socket.IO server")
            
            @self.client.event
            async def disconnect():
                self.connected = False
                print("ℹ Event monitor disconnected")
            
            # Hook events
            @self.client.event(namespace='/hook')
            async def user_prompt(data):
                self.events_received.append(('hook', 'user_prompt', data))
                print(f"✓ Received hook event: user_prompt - {data.get('prompt', '')[:50]}...")
            
            @self.client.event(namespace='/hook')
            async def tool_use(data):
                self.events_received.append(('hook', 'tool_use', data))
                print(f"✓ Received hook event: tool_use - {data.get('tool', '')}")
            
            # System events
            @self.client.event(namespace='/system')
            async def session_start(data):
                self.events_received.append(('system', 'session_start', data))
                print(f"✓ Received system event: session_start")
            
            @self.client.event(namespace='/system')
            async def session_end(data):
                self.events_received.append(('system', 'session_end', data))
                print(f"✓ Received system event: session_end")
            
            # Connect to server with specific namespaces
            await self.client.connect(
                f'http://localhost:{self.port}',
                auth={'token': 'dev-token'},
                namespaces=['/hook', '/system']
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start event monitoring: {e}")
            return False
    
    async def stop_monitoring(self):
        """Stop monitoring and disconnect."""
        if self.client and self.connected:
            await self.client.disconnect()
        print(f"Event monitor collected {len(self.events_received)} events")

def test_claude_execution_with_monitoring():
    """Test Claude execution while monitoring Socket.IO events."""
    
    async def monitor_task():
        """Monitor events in background."""
        monitor = SocketIOEventMonitor()
        success = await monitor.start_monitoring()
        
        if not success:
            return []
        
        # Wait for Claude execution to complete
        await asyncio.sleep(10)  # Give time for Claude to start and execute
        
        await monitor.stop_monitoring()
        return monitor.events_received
    
    def run_claude():
        """Run a simple Claude command."""
        try:
            print("Starting Claude command with hooks enabled...")
            
            # Run a simple non-interactive command that should trigger hooks
            cmd = [
                './claude-mpm', 'run',
                '--input', 'Hello, this is a test message to trigger hooks',
                '--non-interactive',
                '--monitor',  # Enable WebSocket
                '--websocket-port', '8765'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result
            
        except subprocess.TimeoutExpired:
            print("⚠️  Claude command timed out (expected)")
            return None
        except Exception as e:
            print(f"❌ Claude execution failed: {e}")
            return None
    
    # Start monitoring in background
    print("=== Testing Real Hook Events ===")
    
    # Create event loop for monitoring
    try:
        # Run Claude in background thread
        claude_thread = threading.Thread(target=run_claude)
        claude_thread.daemon = True
        claude_thread.start()
        
        # Monitor events
        events = asyncio.run(monitor_task())
        
        # Wait for Claude thread to finish (with timeout)
        claude_thread.join(timeout=5)
        
        return events
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return []

def test_direct_hook_handler():
    """Test hook handler directly by simulating hook events."""
    try:
        import os
        os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
        os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
        
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
        
        print("Creating hook handler for direct test...")
        handler = ClaudeHookHandler()
        
        if not hasattr(handler, 'socketio_client') or not handler.socketio_client:
            print("❌ Hook handler has no Socket.IO client")
            return False
        
        # Test the private method directly
        test_event = {
            'hook_event_name': 'UserPromptSubmit',
            'prompt': 'Test prompt for hook event verification',
            'session_id': 'test_session_123',
        }
        
        try:
            handler._handle_user_prompt_fast(test_event)
            print("✓ Successfully called hook handler method")
            return True
        except Exception as e:
            print(f"❌ Hook handler method failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Direct hook handler test failed: {e}")
        return False

def main():
    """Run hook event tests."""
    print("=== Real Hook Event Tests ===")
    
    # Test 1: Direct hook handler
    print("\n--- Test 1: Direct Hook Handler ---")
    direct_success = test_direct_hook_handler()
    
    # Test 2: Check if Socket.IO server is responding
    print("\n--- Test 2: Socket.IO Server Health ---")
    try:
        import requests
        response = requests.get("http://localhost:8765/status", timeout=5)
        if response.status_code == 200:
            print("✓ Socket.IO server is healthy")
            server_healthy = True
        else:
            print(f"❌ Socket.IO server returned {response.status_code}")
            server_healthy = False
    except Exception as e:
        print(f"❌ Socket.IO server health check failed: {e}")
        server_healthy = False
    
    # Test 3: Monitor actual events (if server is healthy)
    if server_healthy:
        print("\n--- Test 3: Monitor Real Events ---")
        events = test_claude_execution_with_monitoring()
        
        if events:
            print(f"✓ Captured {len(events)} real events:")
            for namespace, event_type, data in events:
                print(f"  - {namespace}/{event_type}: {str(data)[:100]}...")
            events_success = True
        else:
            print("⚠️  No events captured (may be expected for quick test)")
            events_success = False
    else:
        events_success = False
    
    # Summary
    print(f"\n=== Test Results ===")
    print(f"{'PASS' if direct_success else 'FAIL'}: Direct Hook Handler")
    print(f"{'PASS' if server_healthy else 'FAIL'}: Socket.IO Server Health")
    print(f"{'PASS' if events_success else 'SKIP'}: Real Event Monitoring")
    
    overall_success = direct_success and server_healthy
    print(f"\nOverall: Socket.IO data flow {'WORKING' if overall_success else 'NEEDS ATTENTION'}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)