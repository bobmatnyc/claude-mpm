#!/usr/bin/env python3
"""
Test exec mode persistence - verify that the Socket.IO server continues running
after the parent process exits (simulating what happens in exec mode).
"""

import sys
import subprocess
import time
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_exec_mode_persistence():
    """Test that Socket.IO server persists after parent process exits."""
    print("🧪 Testing exec mode persistence")
    
    # Kill any existing servers first
    try:
        subprocess.run(["pkill", "-f", "websocket_server_8765.py"], capture_output=True)
        time.sleep(1)
    except:
        pass
    
    try:
        from claude_mpm.core.claude_runner import ClaudeRunner
        
        print("✅ ClaudeRunner imported successfully")
        
        # Create runner with exec mode + websocket (same as --monitor)
        runner = ClaudeRunner(
            enable_websocket=True,
            websocket_port=8765,
            launch_method="exec"
        )
        runner._should_open_monitor_browser = False  # Don't open browser for test
        
        print("🚀 Starting persistent Socket.IO server...")
        runner._start_persistent_socketio_server()
        
        print("⏱️  Waiting 3 seconds for server to fully initialize...")
        time.sleep(3)
        
        # Test connection
        import socket
        server_running = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex(('localhost', 8765))
                if result == 0:
                    print("✅ Socket.IO server is running")
                    server_running = True
                else:
                    print(f"❌ Cannot connect to server (result: {result})")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
        
        if server_running:
            # Check if server process is detached and running independently
            try:
                # Find the websocket server process
                result = subprocess.run(
                    ["ps", "aux"], 
                    capture_output=True, 
                    text=True
                )
                
                for line in result.stdout.split('\n'):
                    if "websocket_server_8765.py" in line:
                        print(f"✅ Found persistent server process: {line.strip()}")
                        
                        # Extract PID (second column in ps output)
                        parts = line.split()
                        if len(parts) > 1:
                            server_pid = parts[1]
                            print(f"📝 Server PID: {server_pid}")
                            
                            # Verify it's running independently (not a child of this process)
                            parent_pid = os.getppid()  # Our parent PID
                            our_pid = os.getpid()      # Our PID
                            
                            # Check if server's parent is NOT us
                            try:
                                ppid_result = subprocess.run(
                                    ["ps", "-o", "ppid=", "-p", server_pid],
                                    capture_output=True,
                                    text=True
                                )
                                server_parent_pid = ppid_result.stdout.strip()
                                print(f"📝 Server parent PID: {server_parent_pid}, Our PID: {our_pid}")
                                
                                if server_parent_pid != str(our_pid):
                                    print("✅ Server is running independently (not a child of this process)")
                                else:
                                    print("⚠️  Server is a child of this process")
                                    
                            except Exception as e:
                                print(f"⚠️  Could not check parent PID: {e}")
                        break
                else:
                    print("❌ Could not find websocket server process")
                    
            except Exception as e:
                print(f"❌ Process check failed: {e}")
        
        print("🎯 Exec mode persistence test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_exec_mode_persistence()