#!/usr/bin/env python3
"""Test Socket.IO event emission directly"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.websocket_server import get_socketio_server

def test_event_emission():
    """Test sending events to Socket.IO server"""
    print("Testing Socket.IO event emission...")
    
    # Get the server instance
    server = get_socketio_server()
    if not server:
        print("❌ No Socket.IO server instance found")
        return
        
    print(f"✓ Got server instance: {type(server).__name__}")
    
    # Try to emit test events
    test_events = [
        ('hook', {'type': 'user_prompt', 'data': {'prompt': 'Test prompt'}}),
        ('hook', {'type': 'pre_tool', 'data': {'tool': 'Task', 'args': {'test': 'data'}}}),
        ('system', {'type': 'status', 'data': {'status': 'active', 'message': 'Test status'}}),
        ('session', {'type': 'start', 'data': {'session_id': 'test-123'}}),
    ]
    
    for namespace, event_data in test_events:
        try:
            # The emit_event method handles namespace routing
            server.emit_event(namespace, event_data['type'], event_data['data'])
            print(f"✓ Emitted to {namespace}: {event_data['type']}")
        except Exception as e:
            print(f"❌ Failed to emit to {namespace}: {e}")
    
    print("\nCheck your dashboard - you should see these test events!")

if __name__ == "__main__":
    test_event_emission()