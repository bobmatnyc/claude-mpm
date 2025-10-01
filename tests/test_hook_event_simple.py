#!/usr/bin/env python3
"""Simple test of hook event flow."""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.core.socketio_pool import get_connection_pool
from claude_mpm.services.socketio.server.main import SocketIOServer

# Start server
print("Starting Socket.IO server...")
server = SocketIOServer(port=8765)
server.start_sync()
time.sleep(2)

print("Server running. Open http://localhost:8765 in your browser.")
print("Waiting 5 seconds for you to open the dashboard...")
time.sleep(5)

# Test connection pool
print("\nTesting connection pool emission...")
pool = get_connection_pool()

# Send test events with CORRECT format
for i in range(3):
    test_event = {
        "hook_event_name": "TestEvent",  # CORRECT: Use hook_event_name
        "hook_event_type": "TestEvent",
        "subtype": f"test_{i}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hook_input_data": {
            "message": f"Test event {i} from connection pool",
            "index": i,
        },
    }

    print(f"Sending event {i}...")
    result = pool.emit("claude_event", test_event)
    print(f"  Result: {result}")
    time.sleep(1)

print("\nTest complete. Check the dashboard for events.")
print("Press Ctrl+C to stop...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping...")
    server.stop_sync()
