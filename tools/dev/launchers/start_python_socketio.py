#!/usr/bin/env python3
"""Start Python Socket.IO server directly for testing."""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from claude_mpm.services.socketio_server import SocketIOServer

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Start Python Socket.IO server")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    args = parser.parse_args()

    print(f"Starting Python Socket.IO server on {args.host}:{args.port}")

    server = SocketIOServer(host=args.host, port=args.port)

    try:
        server.start()

        # Keep server running
        import time

        while server.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
        print("Server stopped.")
