#!/usr/bin/env python3
"""Test script to verify hook handler Socket.IO connection and event flow."""

import sys
import os
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_hook_handler_connection():
    """Test that hook handler can connect to Socket.IO server and send events."""
    print("🧪 Testing hook handler Socket.IO connection...")
    
    try:
        # Import hook handler
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
        
        # Create handler
        print("  ✓ Creating hook handler...")
        handler = ClaudeHookHandler()
        
        # Check if Socket.IO client is created
        if handler.socketio_client:
            print(f"  ✓ Socket.IO client created (URL: {handler.server_url})")
            
            # Check connection status
            if handler.socketio_client.connected:
                print("  ✓ Socket.IO client connected")
            else:
                print("  ⚠️  Socket.IO client not connected (server may not be running)")
                
            # Test sending a hook event
            print("  🔄 Testing hook event emission...")
            test_event = {
                'hook_event_name': 'UserPromptSubmit',
                'prompt': 'test prompt for hook verification',
                'session_id': 'test-session',
                'timestamp': time.time()
            }
            
            handler._handle_user_prompt_fast(test_event)
            print("  ✓ Hook event emitted successfully")
            
        else:
            print("  ❌ Socket.IO client not created")
            print("     - Check if python-socketio is installed")
            print("     - Check if Socket.IO server is running")
            
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_websocket_handler_connection():
    """Test that WebSocket logging handler can connect and send log events."""
    print("\n🧪 Testing WebSocket logging handler connection...")
    
    try:
        from claude_mpm.core.websocket_handler import WebSocketHandler
        import logging
        
        # Create handler
        print("  ✓ Creating WebSocket logging handler...")
        handler = WebSocketHandler(level=logging.INFO)
        
        # Check if Socket.IO client is created
        if handler._socketio_client:
            print(f"  ✓ Socket.IO client created (URL: {handler._server_url})")
            
            # Check connection status
            if handler._socketio_client.connected:
                print("  ✓ Socket.IO client connected")
            else:
                print("  ⚠️  Socket.IO client not connected (server may not be running)")
                
            # Test sending a log event
            print("  🔄 Testing log event emission...")
            log_record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test log message for WebSocket verification",
                args=(),
                exc_info=None
            )
            
            handler.emit(log_record)
            print("  ✓ Log event emitted successfully")
            
        else:
            print("  ❌ Socket.IO client not created")
            
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_server_availability():
    """Test if Socket.IO server is running and accessible."""
    print("\n🧪 Testing Socket.IO server availability...")
    
    try:
        import socket
        
        # Check common ports
        ports_to_check = [8765, 8080, 8081, 8082]
        running_servers = []
        
        for port in ports_to_check:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    result = s.connect_ex(('localhost', port))
                    if result == 0:
                        running_servers.append(port)
                        print(f"  ✓ Server detected on port {port}")
            except:
                continue
                
        if running_servers:
            print(f"  ✓ Found {len(running_servers)} running server(s) on ports: {running_servers}")
            
            # Test HTTP accessibility
            try:
                import urllib.request
                for port in running_servers:
                    try:
                        response = urllib.request.urlopen(f'http://localhost:{port}/socket.io/', timeout=2)
                        if response.getcode() in [200, 400]:  # 400 is OK for Socket.IO endpoint
                            print(f"  ✓ Socket.IO endpoint accessible on port {port}")
                        break
                    except:
                        continue
            except Exception as e:
                print(f"  ⚠️  HTTP test failed: {e}")
                
        else:
            print("  ❌ No Socket.IO servers detected")
            print("     To start a server, run: claude-mpm run --monitor")
            
        return len(running_servers) > 0
        
    except Exception as e:
        print(f"  ❌ Error checking server availability: {e}")
        return False

def main():
    """Run all tests."""
    print("🔍 Testing Socket.IO Integration")
    print("=" * 50)
    
    # Set debug mode for more verbose output
    os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    
    results = []
    
    # Test server availability first
    results.append(test_server_availability())
    
    # Test hook handler
    results.append(test_hook_handler_connection())
    
    # Test websocket handler  
    results.append(test_websocket_handler_connection())
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ All tests passed! Socket.IO integration should be working.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        
    print("\n💡 To test with a live server:")
    print("   1. Run: claude-mpm run --monitor")
    print("   2. In another terminal, run this test again")
    print("   3. Check the dashboard for real-time events")

if __name__ == "__main__":
    main()