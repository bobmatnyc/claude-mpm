#!/usr/bin/env python3
"""Test the full server lifecycle with enhanced PID validation."""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

def test_server_lifecycle():
    """Test starting and stopping the server with enhanced validation."""
    print("Testing server lifecycle...")
    
    server_script = Path(__file__).parent.parent / "src" / "claude_mpm" / "services" / "standalone_socketio_server.py"
    test_port = 18999
    
    # Start server in background
    print(f"Starting server on port {test_port}...")
    proc = subprocess.Popen([
        sys.executable, str(server_script), 
        "--host", "localhost", 
        "--port", str(test_port)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait a moment for startup
    time.sleep(3)
    
    # Check if server is running
    check_proc = subprocess.run([
        sys.executable, str(server_script),
        "--check-running", "--port", str(test_port)
    ], capture_output=True, text=True)
    
    if check_proc.returncode == 0:
        print("✓ Server is running")
        print(check_proc.stdout.strip())
    else:
        print("✗ Server check failed")
        print(check_proc.stderr)
        proc.terminate()
        return False
    
    # Stop the server
    print("Stopping server...")
    stop_proc = subprocess.run([
        sys.executable, str(server_script),
        "--stop", "--port", str(test_port)
    ], capture_output=True, text=True)
    
    print("Stop command output:")
    if stop_proc.stdout:
        print(stop_proc.stdout)
    if stop_proc.stderr:
        print(stop_proc.stderr)
    
    # Clean up process
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    except:
        pass
    
    return True

if __name__ == "__main__":
    try:
        success = test_server_lifecycle()
        print("✓ Server lifecycle test completed" if success else "✗ Server lifecycle test failed")
    except KeyboardInterrupt:
        print("\\nTest interrupted")
    except Exception as e:
        print(f"✗ Test failed with error: {e}")