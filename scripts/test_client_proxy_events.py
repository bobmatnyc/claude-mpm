#!/usr/bin/env python3
"""Test if SocketIOClientProxy can successfully emit events."""

import sys
import os
import asyncio
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.websocket_server import SocketIOClientProxy

def test_client_proxy():
    """Test the client proxy directly."""
    print("🔄 Testing SocketIOClientProxy...")
    
    proxy = SocketIOClientProxy(port=8765)
    proxy.start()
    
    # Give client time to connect
    time.sleep(2)
    
    print("📤 Emitting test events...")
    
    # Try emitting some events
    proxy.emit_event('/system', 'test_event', {"message": "Test from client proxy", "timestamp": time.time()})
    proxy.emit_event('/session', 'start', {"session_id": "test-123", "message": "Test session start"})
    proxy.emit_event('/claude', 'output', {"content": "Test Claude output", "stream": "stdout"})
    
    print("✅ Events emitted!")
    print("🌐 Check http://localhost:8765 in browser to see if events appear")
    
    # Keep proxy running for a bit
    time.sleep(5)
    
    proxy.stop()
    print("🛑 Client proxy stopped")

if __name__ == "__main__":
    test_client_proxy()