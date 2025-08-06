#!/usr/bin/env python3
"""Test direct Socket.IO emission from hook handler logic"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.core.socketio_pool import get_connection_pool
from datetime import datetime
import time

# Enable debug
os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'

# Initialize connection pool
pool = get_connection_pool()

print("Connection pool stats:", pool.get_stats())

# Test emitting events in the corrected format
test_data = {
    'event_type': 'user_prompt',
    'prompt_text': 'Test prompt from direct emit - this should appear in dashboard!',
    'prompt_preview': 'Test prompt from direct emit',
    'prompt_length': 50,
    'session_id': 'test-123',
    'timestamp': datetime.now().isoformat(),
    'working_directory': os.getcwd(),
    'is_command': False,
    'contains_code': False,
    'urgency': 'normal'
}

print("\nEmitting test event in corrected format...")
claude_event_data = {
    'type': 'hook.user_prompt',
    'timestamp': datetime.now().isoformat(),
    'data': test_data
}
pool.emit_event('', 'claude_event', claude_event_data)

# Give time for batch processing
time.sleep(0.5)

print("\nConnection pool stats after emit:", pool.get_stats())

# Test another event type
print("\nEmitting pre_tool event...")
tool_data = {
    'event_type': 'pre_tool',
    'tool_name': 'Bash',
    'operation_type': 'execute',
    'tool_parameters': {
        'command': 'echo "Hello from test"',
        'command_length': 20
    },
    'session_id': 'test-123',
    'timestamp': datetime.now().isoformat(),
    'is_execution': True,
    'security_risk': 'low'
}

claude_event_data2 = {
    'type': 'hook.pre_tool',
    'timestamp': datetime.now().isoformat(),
    'data': tool_data
}
pool.emit_event('', 'claude_event', claude_event_data2)

time.sleep(0.5)

print("\nFinal connection pool stats:", pool.get_stats())

# Cleanup
pool.stop()