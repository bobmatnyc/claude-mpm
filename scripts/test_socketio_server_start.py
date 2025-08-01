#!/usr/bin/env python3
"""Test Socket.IO server startup"""

import sys
import time
import logging

logging.basicConfig(level=logging.DEBUG)

try:
    from claude_mpm.services.socketio_server import SocketIOServer
    
    print("Creating Socket.IO server...")
    server = SocketIOServer(host="localhost", port=8765)
    
    print("Starting server...")
    server.start()
    
    print("Server thread started, waiting...")
    time.sleep(5)
    
    if server.thread and server.thread.is_alive():
        print(f"✅ Server is running! Thread alive: {server.thread.is_alive()}")
        print("Keeping server running for 60 seconds...")
        time.sleep(60)
    else:
        print("❌ Server thread is not alive!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()