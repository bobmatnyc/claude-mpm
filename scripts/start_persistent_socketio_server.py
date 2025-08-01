#!/usr/bin/env python3
"""
Start a persistent Socket.IO server for testing.

This server will run until manually stopped.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.websocket_server import SocketIOServer


def main():
    """Start persistent Socket.IO server."""
    
    print("🚀 Starting persistent Socket.IO server...")
    server = SocketIOServer(host="localhost", port=8765)
    
    try:
        server.start()
        print("✅ Socket.IO server started on port 8765")
        print("🌐 Dashboard: http://localhost:8765/dashboard?autoconnect=true")
        print("💡 Press Ctrl+C to stop the server")
        
        # Keep server running
        import signal
        import time
        
        def signal_handler(sig, frame):
            print("\n🛑 Stopping server...")
            server.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
        server.stop()


if __name__ == "__main__":
    main()