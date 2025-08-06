#!/usr/bin/env python3
"""Test emitting events to Socket.IO server."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.websocket_server import get_socketio_server
import time

def test_emit_events():
    """Test emitting various events."""
    print("📡 Getting Socket.IO server instance...")
    server = get_socketio_server()
    
    if not server.running:
        print("🚀 Starting server...")
        server.start()
        time.sleep(2)  # Give server time to start
    
    print("📤 Emitting test events...")
    
    # Test system events
    server.emit_event('/system', 'test_event', {"message": "Test system event"})
    
    # Test session events  
    server.emit_event('/session', 'start', {
        "session_id": "test-session-123",
        "start_time": "2024-01-01T12:00:00Z",
        "launch_method": "interactive",
        "working_directory": "/Users/masa/Projects/claude-mpm"
    })
    
    # Test Claude events
    server.emit_event('/claude', 'status_changed', {
        "status": "running",
        "pid": 12345,
        "message": "Claude is running"
    })
    
    server.emit_event('/claude', 'output', {
        "content": "Hello from Claude!",
        "stream": "stdout"
    })
    
    # Test hook events
    server.emit_event('/hook', 'user_prompt', {
        "prompt": "Test user prompt",
        "session_id": "test-session-123"
    })
    
    server.emit_event('/hook', 'pre_tool', {
        "tool_name": "Bash",
        "session_id": "test-session-123"
    })
    
    server.emit_event('/hook', 'post_tool', {
        "tool_name": "Bash",
        "exit_code": 0,
        "session_id": "test-session-123"
    })
    
    # Test todo events
    server.emit_event('/todo', 'updated', {
        "todos": [
            {"id": "1", "content": "Test todo item", "status": "pending", "priority": "high"},
            {"id": "2", "content": "Another todo", "status": "completed", "priority": "medium"}
        ],
        "stats": {
            "total": 2,
            "completed": 1,
            "in_progress": 0,
            "pending": 1
        }
    })
    
    # Test memory events
    server.emit_event('/memory', 'loaded', {
        "agent_id": "test-agent",
        "memory_size": 1024,
        "sections_count": 5
    })
    
    server.emit_event('/memory', 'created', {
        "agent_id": "test-agent",
        "template_type": "general_purpose"
    })
    
    server.emit_event('/memory', 'updated', {
        "agent_id": "test-agent",
        "learning_type": "pattern",
        "content": "New learning content",
        "section": "experiences"
    })
    
    server.emit_event('/memory', 'injected', {
        "agent_id": "test-agent",
        "context_size": 512
    })
    
    # Test log events
    server.emit_event('/log', 'message', {
        "level": "info",
        "message": "Test log message",
        "module": "test_module"
    })
    
    server.emit_event('/log', 'message', {
        "level": "warning", 
        "message": "Test warning message",
        "module": "test_module"
    })
    
    server.emit_event('/log', 'message', {
        "level": "error",
        "message": "Test error message", 
        "module": "test_module"
    })
    
    print("✅ Events emitted! Check dashboard to see if they appear.")
    print("🌐 Dashboard should be available at: http://localhost:8765/dashboard")
    
    time.sleep(2)

if __name__ == "__main__":
    test_emit_events()