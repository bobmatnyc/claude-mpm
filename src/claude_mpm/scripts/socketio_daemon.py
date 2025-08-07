#!/usr/bin/env python3
"""
Pure Python daemon management for Socket.IO server.
No external dependencies required.
"""

import os
import sys
import time
import signal
import subprocess
import psutil
import json
from pathlib import Path

# Handle imports for both development and installed scenarios
script_dir = Path(__file__).parent
try:
    # When installed as package, this should work directly
    from claude_mpm.services.socketio_server import SocketIOServer
except ImportError:
    # When in development, add src to path
    project_root = script_dir.parent.parent.parent  # from scripts -> claude_mpm -> src -> project_root
    src_path = project_root / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))
    from claude_mpm.services.socketio_server import SocketIOServer

PID_FILE = Path.home() / ".claude-mpm" / "socketio-server.pid"
LOG_FILE = Path.home() / ".claude-mpm" / "socketio-server.log"

def ensure_dirs():
    """Ensure required directories exist."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)

def is_running():
    """Check if server is already running."""
    if not PID_FILE.exists():
        return False
    
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        
        # Check if process exists
        process = psutil.Process(pid)
        return process.is_running()
    except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
        # Clean up stale PID file
        PID_FILE.unlink(missing_ok=True)
        return False

def start_server():
    """Start the Socket.IO server as a daemon with conflict detection."""
    if is_running():
        print("Socket.IO daemon server is already running.")
        print(f"Use '{__file__} status' for details")
        return
    
    # Check for HTTP-managed server conflict
    try:
        import requests
        response = requests.get("http://localhost:8765/health", timeout=1.0)
        if response.status_code == 200:
            data = response.json()
            if 'server_id' in data:
                print(f"⚠️  HTTP-managed server already running: {data.get('server_id')}")
                print(f"   Stop it first: socketio_server_manager.py stop --port 8765")
                print(f"   Or diagnose: socketio_server_manager.py diagnose")
                return
    except:
        pass  # No HTTP server, continue
    
    ensure_dirs()
    
    # Fork to create daemon
    pid = os.fork()
    if pid > 0:
        # Parent process
        print(f"Starting Socket.IO server (PID: {pid})...")
        with open(PID_FILE, 'w') as f:
            f.write(str(pid))
        print("Socket.IO server started successfully.")
        print(f"PID file: {PID_FILE}")
        print(f"Log file: {LOG_FILE}")
        sys.exit(0)
    
    # Child process - become daemon
    os.setsid()
    os.umask(0)
    
    # Redirect stdout/stderr to log file
    with open(LOG_FILE, 'a') as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())
    
    # Start server
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Socket.IO server...")
    server = SocketIOServer(host="localhost", port=8765)
    
    # Handle signals
    def signal_handler(signum, frame):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received signal {signum}, shutting down...")
        server.stop()
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start server
    server.start()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

def stop_server():
    """Stop the Socket.IO daemon server."""
    if not is_running():
        print("Socket.IO daemon server is not running.")
        print(f"Check for other servers: socketio_server_manager.py status")
        return
    
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        
        print(f"Stopping Socket.IO server (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)
        
        # Wait for process to stop
        for _ in range(10):
            if not is_running():
                print("Socket.IO server stopped successfully.")
                PID_FILE.unlink(missing_ok=True)
                return
            time.sleep(0.5)
        
        # Force kill if still running
        print("Server didn't stop gracefully, forcing...")
        os.kill(pid, signal.SIGKILL)
        PID_FILE.unlink(missing_ok=True)
        
    except Exception as e:
        print(f"Error stopping server: {e}")

def status_server():
    """Check server status with manager integration info."""
    if is_running():
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        print(f"Socket.IO daemon server is running (PID: {pid})")
        print(f"PID file: {PID_FILE}")
        
        # Check if port is listening
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 8765))
            sock.close()
            if result == 0:
                print("✅ Server is listening on port 8765")
                print("🔧 Management style: daemon")
            else:
                print("⚠️ WARNING: Server process exists but port 8765 is not accessible")
        except:
            pass
            
        # Show management commands
        print("\n🔧 Management Commands:")
        print(f"   • Stop: {__file__} stop")
        print(f"   • Restart: {__file__} restart")
        
        # Check for manager conflicts
        try:
            import requests
            response = requests.get("http://localhost:8765/health", timeout=1.0)
            if response.status_code == 200:
                data = response.json()
                if 'server_id' in data and data.get('server_id') != 'daemon-socketio':
                    print(f"\n⚠️  POTENTIAL CONFLICT: HTTP-managed server also detected")
                    print(f"   Server ID: {data.get('server_id')}")
                    print(f"   Use 'socketio_server_manager.py diagnose' to resolve")
        except:
            pass
            
    else:
        print("Socket.IO daemon server is not running")
        print(f"\n🔧 Start Commands:")
        print(f"   • Daemon: {__file__} start")
        print(f"   • HTTP-managed: socketio_server_manager.py start")

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: socketio-daemon.py {start|stop|restart|status}")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "start":
        start_server()
    elif command == "stop":
        stop_server()
    elif command == "restart":
        stop_server()
        time.sleep(1)
        start_server()
    elif command == "status":
        status_server()
    else:
        print(f"Unknown command: {command}")
        print("Usage: socketio-daemon.py {start|stop|restart|status}")
        sys.exit(1)

if __name__ == "__main__":
    # Install psutil if not available
    try:
        import psutil
    except ImportError:
        print("Installing psutil...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
    
    main()