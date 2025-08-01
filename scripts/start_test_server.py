#!/usr/bin/env python3
"""
Start a Socket.IO server for testing multiple browser connections.
"""

import signal
import sys
import time
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.socketio_server import SocketIOServer, SOCKETIO_AVAILABLE

def main():
    if not SOCKETIO_AVAILABLE:
        print("❌ Socket.IO packages not available. Install with:")
        print("   pip install python-socketio aiohttp")
        return 1
    
    print("🚀 Starting Socket.IO test server...")
    print("📱 Test with multiple browser tabs at:")
    print(f"   http://localhost:8765/claude_mpm_socketio_dashboard.html")
    print("   OR")
    print(f"   file://{os.path.abspath('scripts/test_multiple_tabs.html')}")
    print("\n⏹️  Press Ctrl+C to stop the server")
    
    server = SocketIOServer(host="localhost", port=8765)
    
    def signal_handler(sig, frame):
        print("\n🛑 Stopping server...")
        server.stop()
        print("✅ Server stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        server.start()
        
        # Generate some test events to demonstrate functionality
        import threading
        def generate_test_events():
            time.sleep(2)  # Wait for server to start
            event_count = 0
            while server.running:
                event_count += 1
                server.broadcast_event("test.heartbeat", {
                    "message": f"Test heartbeat #{event_count}",
                    "timestamp": time.time()
                })
                time.sleep(10)  # Send heartbeat every 10 seconds
        
        event_thread = threading.Thread(target=generate_test_events, daemon=True)
        event_thread.start()
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
        server.stop()
        print("✅ Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())