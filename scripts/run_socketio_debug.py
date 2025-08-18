#!/usr/bin/env python3
"""
Run the SocketIO server in debug mode to see all logs.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import and run server
from claude_mpm.services.socketio.server.main import SocketIOServer

if __name__ == "__main__":
    print("Starting SocketIO server in debug mode...")
    server = SocketIOServer(host="localhost", port=8765)
    
    # Enable debug logging for all loggers
    for logger_name in logging.Logger.manager.loggerDict:
        if 'claude_mpm' in logger_name or 'socketio' in logger_name:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
    
    try:
        print("Server starting on localhost:8765...")
        server.start_sync()
        print("Server started. Press Ctrl+C to stop.")
        
        # Keep running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop_sync()
        print("Server stopped.")