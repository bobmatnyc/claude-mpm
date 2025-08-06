#!/usr/bin/env python3
"""
Test Socket.IO server startup for --monitor mode.

This script tests the exact flow that happens when --monitor is used
to identify any issues with server startup or browser opening.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_monitor_startup():
    """Test the complete --monitor startup flow."""
    print("🧪 Testing Socket.IO server startup for --monitor mode")
    
    try:
        from claude_mpm.core.claude_runner import ClaudeRunner
        
        print("✅ ClaudeRunner imported successfully")
        
        # Create runner with websocket enabled (same as --monitor)
        runner = ClaudeRunner(
            enable_websocket=True,
            websocket_port=8765,
            launch_method="exec"  # Test exec mode like --monitor does
        )
        
        # Set the browser opening flag like --monitor does
        runner._should_open_monitor_browser = True
        
        print("✅ ClaudeRunner created with websocket enabled")
        
        # Test the persistent server startup method directly
        print("🚀 Testing persistent Socket.IO server startup...")
        runner._start_persistent_socketio_server()
        
        print("⏱️  Waiting 2 seconds to let server fully initialize...")
        time.sleep(2)
        
        # Test connection
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex(('localhost', 8765))
                if result == 0:
                    print("✅ Socket.IO server is accepting connections")
                else:
                    print(f"❌ Cannot connect to Socket.IO server (result: {result})")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
        
        # Test HTTP endpoint
        try:
            import urllib.request
            response = urllib.request.urlopen('http://localhost:8765/health', timeout=2)
            data = response.read().decode()
            print(f"✅ Health endpoint response: {data[:100]}...")
        except Exception as e:
            print(f"❌ Health endpoint test failed: {e}")
        
        # Test dashboard endpoint
        try:
            response = urllib.request.urlopen('http://localhost:8765/dashboard', timeout=2)
            dashboard_data = response.read().decode()
            if "Claude MPM Socket.IO Dashboard" in dashboard_data:
                print("✅ Dashboard HTML is being served correctly")
            else:
                print("❌ Dashboard HTML doesn't contain expected content")
        except Exception as e:
            print(f"❌ Dashboard endpoint test failed: {e}")
        
        print("🎯 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_monitor_startup()