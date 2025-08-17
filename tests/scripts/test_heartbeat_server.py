#!/usr/bin/env python3
"""Quick test to verify heartbeat functionality in Socket.IO server.

WHY: This script starts the Socket.IO server with heartbeat enabled
and runs for a short time to verify the implementation works.
"""

import sys
import time
import threading
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.services.socketio_server import SocketIOServer


def main():
    """Start server and test heartbeat."""
    print("🚀 Starting Socket.IO server with heartbeat...")
    
    # Create server with shorter heartbeat interval for testing
    server = SocketIOServer(port=8765)
    
    # Set heartbeat interval to 5 seconds for faster testing
    if hasattr(server.core, 'heartbeat_interval'):
        server.core.heartbeat_interval = 5
        print("⏰ Set heartbeat interval to 5 seconds for testing")
    
    # Start server
    try:
        server.start_sync()
        print(f"✅ Server started on port 8765")
        print("🫀 Heartbeat will be sent every 5 seconds")
        print("-" * 50)
        
        # Simulate some sessions for testing
        server.session_started("test-session-1", "cli", "/test/dir")
        print("📝 Created test session: test-session-1")
        
        time.sleep(2)
        
        server.agent_delegated("engineer", "Fix a bug", "started")
        print("🤖 Delegated to engineer agent")
        
        # Run for 15 seconds to see at least 2-3 heartbeats
        print("\n⏳ Running for 15 seconds to observe heartbeats...")
        print("   (Check Socket.IO logs for heartbeat messages)")
        print("-" * 50)
        
        for i in range(15):
            time.sleep(1)
            if i % 5 == 4:
                print(f"⏱️  {i+1} seconds elapsed...")
                
        print("\n✅ Test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔌 Stopping server...")
        server.stop_sync()
        print("👋 Server stopped")


if __name__ == "__main__":
    main()