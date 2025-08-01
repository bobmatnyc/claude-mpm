#!/usr/bin/env python3
"""
Test subprocess startup to debug why the Socket.IO server isn't starting.
"""

import sys
import subprocess
import time
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_subprocess_startup():
    """Test subprocess startup with better error handling."""
    
    # First, test if the script can run at all
    script_path = Path.home() / ".claude-mpm" / "websocket_server_8765.py"
    
    if not script_path.exists():
        print("❌ Script doesn't exist, creating it...")
        # Create the script manually using the same logic from ClaudeRunner
        script_content = f'''#!/usr/bin/env python3
import sys
import os
import signal
import time
from pathlib import Path

# Add the claude-mpm source to path
sys.path.insert(0, "{Path(__file__).parent.parent.parent / "src"}")

def main():
    try:
        from claude_mpm.services.websocket_server import SocketIOServer
        from claude_mpm.core.logger import get_logger
        from claude_mpm.core.websocket_handler import setup_websocket_logging
        import logging
        
        print("📝 Starting SocketIOServer...", flush=True)
        
        # Create and start server
        server = SocketIOServer(port=8765)
        server.start()
        
        # Set up WebSocket logging for this process
        setup_websocket_logging(None, level=logging.INFO)
        setup_websocket_logging("claude_mpm", level=logging.INFO)
        
        logger = get_logger("websocket_server_persistent")
        logger.info(f"Persistent WebSocket server started on port 8765 with INFO logging")
        
        print("✅ Server started successfully", flush=True)
        
        # Signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            print("🛑 Received shutdown signal", flush=True)
            try:
                server.stop()
            except:
                pass
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Keep server running
        print("🔄 Entering main loop...", flush=True)
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"❌ WebSocket server error: {{e}}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Script starting...", flush=True)
    main()
'''
        
        script_path.parent.mkdir(exist_ok=True)
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        print(f"✅ Created script at {script_path}")
    
    print("🧪 Testing direct script execution...")
    
    # Run the script with proper output handling
    try:
        print(f"📝 Running script: {script_path}")
        
        # Use Popen to capture both stdout and stderr
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        print(f"✅ Process started with PID: {process.pid}")
        
        # Give it time to start
        time.sleep(3)
        
        # Check if process is still running
        returncode = process.poll()
        if returncode is None:
            print("✅ Process is still running")
            
            # Test connection
            import socket
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    result = s.connect_ex(('localhost', 8765))
                    if result == 0:
                        print("✅ Server is accepting connections")
                    else:
                        print(f"❌ Cannot connect (result: {result})")
            except Exception as e:
                print(f"❌ Connection test failed: {e}")
            
            # Kill the process
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=2)
                print(f"📝 STDOUT: {stdout}")
                print(f"📝 STDERR: {stderr}")
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                print(f"📝 STDOUT (after kill): {stdout}")
                print(f"📝 STDERR (after kill): {stderr}")
                
        else:
            print(f"❌ Process exited early with code: {returncode}")
            stdout, stderr = process.communicate()
            print(f"📝 STDOUT: {stdout}")
            print(f"📝 STDERR: {stderr}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_subprocess_startup()