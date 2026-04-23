#!/usr/bin/env python3
"""Manually start Socket.IO server for testing"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import logging

from claude_mpm.services.socketio_server import SocketIOServer

logging.basicConfig(level=logging.INFO)

print("Starting Socket.IO server on port 8765...")
server = SocketIOServer(host="localhost", port=8765)
server.start_sync()

print("Server started. Press Ctrl+C to stop.")
try:
    import time

    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down...")
    server.stop()
