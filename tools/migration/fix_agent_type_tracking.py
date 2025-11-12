#!/usr/bin/env python3
"""Fix agent type tracking between Task invocation and SubagentStop events."""


def analyze_current_implementation():
    """Analyze the current implementation to understand the gap."""
    print("🔍 Analyzing Agent Type Tracking Issue")
    print("=" * 60)

    print("\n1. Current State:")
    print("   ✅ PreToolUse captures subagent_type from Task tool")
    print("   ❌ SubagentStop shows agent_type as 'unknown'")
    print("   🔄 No correlation between the two events")

    print("\n2. Root Cause:")
    print("   - Claude Code doesn't pass agent_type in SubagentStop events")
    print("   - We need to track Task invocations and correlate them")
    print("   - Session-based correlation is possible")

    print("\n3. Solution Approach:")
    print("   - Create a simple in-memory cache for active delegations")
    print("   - Store agent_type when Task is invoked")
    print("   - Retrieve it when SubagentStop occurs")
    print("   - Use session_id + timestamp for correlation")


def create_fixed_hook_handler():
    """Create an updated hook handler with agent type tracking."""

    fixed_handler = '''#!/usr/bin/env python3
"""Optimized Claude Code hook handler with Socket.IO connection pooling and agent tracking.

This handler now tracks agent delegations to properly identify agent types in SubagentStop events.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from collections import deque

# Quick environment check
DEBUG = os.environ.get('CLAUDE_MPM_HOOK_DEBUG', '').lower() == 'true'

# Socket.IO import
try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None

# Fallback imports
try:
    from ...services.websocket_server import get_server_instance
    SERVER_AVAILABLE = True
except ImportError:
    SERVER_AVAILABLE = False
    get_server_instance = None


class ClaudeHookHandler:
    """Optimized hook handler with direct Socket.IO client and agent tracking."""

    def __init__(self):
        self.sio_client = None
        self.sio_connected = False
        self.last_connect_attempt = 0

        # Agent delegation tracking
        # Store recent Task delegations: (session_id, timestamp) -> agent_type
        self.active_delegations = {}
        # Use deque to limit memory usage (keep last 100 delegations)
        self.delegation_history = deque(maxlen=100)

    def _track_delegation(self, session_id: str, agent_type: str):
        """Track a new agent delegation."""
        key = f"{session_id}:{datetime.now().timestamp()}"
        self.active_delegations[session_id] = agent_type
        self.delegation_history.append((key, agent_type))

        # Clean up old delegations (older than 5 minutes)
        cutoff_time = datetime.now().timestamp() - 300
        keys_to_remove = []
        for key in list(self.active_delegations.keys()):
            if ':' in key:
                _, timestamp = key.split(':', 1)
                if float(timestamp) < cutoff_time:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.active_delegations[key]

    def _get_delegation_agent_type(self, session_id: str) -> str:
        """Get the agent type for a session's active delegation."""
        # First try exact session match
        if session_id in self.active_delegations:
            return self.active_delegations[session_id]

        # Then try to find in recent history
        for key, agent_type in reversed(self.delegation_history):
            if key.startswith(session_id):
                return agent_type

        return 'unknown'
'''

    # Add the tracking to pre_tool handler
    pre_tool_addition = '''
    def _handle_pre_tool_fast(self, event):
        """Handle pre-tool use with comprehensive data capture and delegation tracking."""
        tool_name = event.get('tool_name', '')
        tool_input = event.get('tool_input', {})

        # Track Task delegations for SubagentStop correlation
        if tool_name == 'Task' and isinstance(tool_input, dict):
            agent_type = tool_input.get('subagent_type', 'unknown')
            session_id = event.get('session_id', '')
            if session_id and agent_type != 'unknown':
                self._track_delegation(session_id, agent_type)

        # Continue with existing implementation...
'''

    # Update subagent_stop handler
    subagent_stop_fix = '''
    def _handle_subagent_stop_fast(self, event):
        """Handle subagent stop events with proper agent type tracking."""
        # Try to get agent type from our tracking
        session_id = event.get('session_id', '')
        agent_type = self._get_delegation_agent_type(session_id) if session_id else 'unknown'

        # Fall back to event data if available
        if agent_type == 'unknown':
            agent_type = event.get('agent_type', event.get('subagent_type', 'unknown'))

        # Continue with existing logic but use tracked agent_type...
'''

    print("\n4. Implementation Details:")
    print("   📝 Add delegation tracking to ClaudeHookHandler.__init__")
    print("   📝 Track delegations in _handle_pre_tool_fast")
    print("   📝 Retrieve agent type in _handle_subagent_stop_fast")
    print("   📝 Use session-based correlation with timestamp")
    print("   📝 Implement memory cleanup for old delegations")

    return fixed_handler, pre_tool_addition, subagent_stop_fix


def show_implementation_plan():
    """Show the implementation plan for fixing agent type tracking."""
    print("\n📋 Implementation Plan")
    print("=" * 60)

    print("\n1. Update hook_handler.py:")
    print("   - Add active_delegations dictionary to __init__")
    print("   - Add delegation_history deque for recent tracking")
    print("   - Implement _track_delegation() method")
    print("   - Implement _get_delegation_agent_type() method")

    print("\n2. Modify _handle_pre_tool_fast:")
    print("   - Check if tool_name == 'Task'")
    print("   - Extract subagent_type from tool_input")
    print("   - Call _track_delegation(session_id, agent_type)")

    print("\n3. Modify _handle_subagent_stop_fast:")
    print("   - Call _get_delegation_agent_type(session_id)")
    print("   - Use tracked agent_type instead of 'unknown'")
    print("   - Keep existing fallback logic")

    print("\n4. Benefits:")
    print("   ✅ Accurate agent_type in SubagentStop events")
    print("   ✅ Better monitoring and analysis capabilities")
    print("   ✅ Maintains backward compatibility")
    print("   ✅ Low memory overhead with cleanup")

    print("\n5. Testing:")
    print("   - Run debug_subagent_stop.py to verify")
    print("   - Check dashboard shows correct agent types")
    print("   - Monitor memory usage for long sessions")


def main():
    """Main function."""
    print("🛠️ Agent Type Tracking Fix")
    print(
        "This script analyzes and provides a solution for the unknown agent_type issue\n"
    )

    # Analyze current state
    analyze_current_implementation()

    # Create fixed implementation
    _fixed_handler, _pre_tool_addition, _subagent_stop_fix = create_fixed_hook_handler()

    # Show implementation plan
    show_implementation_plan()

    print("\n\n✅ Solution Summary")
    print("=" * 60)
    print("The fix involves adding a simple tracking mechanism that:")
    print("1. Stores agent_type when Task tool is invoked")
    print("2. Retrieves it when SubagentStop event occurs")
    print("3. Uses session_id for correlation")
    print("4. Includes memory cleanup for long-running sessions")
    print("\nThis ensures SubagentStop events have the correct agent_type!")


if __name__ == "__main__":
    main()
