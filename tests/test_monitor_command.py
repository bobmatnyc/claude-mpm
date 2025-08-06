#!/usr/bin/env python3
"""
Test the --monitor command end-to-end.
"""

import sys
import subprocess
import time
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_monitor_command():
    """Test --monitor flag end-to-end."""
    print("🧪 Testing --monitor command end-to-end")
    
    # Test with a subprocess that we can control
    try:
        from claude_mpm.cli import main
        
        print("✅ CLI imported successfully")
        
        # Use a subprocess to test the full flow
        process = subprocess.Popen([
            sys.executable, "-c", f"""
import sys
sys.path.insert(0, '{Path(__file__).parent.parent / "src"}')
from claude_mpm.cli import main
main(['run', '--monitor', '--non-interactive', '-i', 'test message'])
"""
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print(f"✅ Process started with PID: {process.pid}")
        
        # Give it time to start up and show output
        time.sleep(5)
        
        # Check if server is running
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', 8765))
                if result == 0:
                    print("✅ Socket.IO server is running during --monitor execution")
                else:
                    print(f"❌ Cannot connect to server during execution (result: {result})")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
        
        # Terminate the process
        process.terminate()
        
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        
        print("📝 Process output:")
        print("STDOUT:")
        print(stdout[:1000] + ("..." if len(stdout) > 1000 else ""))
        print("STDERR:")  
        print(stderr[:1000] + ("..." if len(stderr) > 1000 else ""))
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_monitor_command()