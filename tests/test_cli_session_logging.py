#!/usr/bin/env python3
"""
Test CLI Session Logging Integration

Test that session logging works when integrated with the CLI.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def test_cli_integration():
    """Test session logging integration with CLI components."""
    print("Testing CLI Integration with Session Logging")
    print("=" * 60)
    
    # Set a test session ID
    test_session_id = f"cli_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    print(f"Test Session ID: {test_session_id}")
    
    try:
        # Import after setting environment
        from claude_mpm.utils.session_logging import (
            is_session_logging_enabled,
            log_agent_response,
            get_current_session_id,
            get_session_directory
        )
        
        # Check if enabled
        print(f"Logging Enabled: {is_session_logging_enabled()}")
        print(f"Current Session: {get_current_session_id()}")
        print(f"Session Directory: {get_session_directory()}")
        print()
        
        # Simulate agent responses
        agents = ["research", "engineer", "qa", "pm"]
        
        for i, agent in enumerate(agents, 1):
            print(f"Simulating {agent} agent response...")
            
            request = f"Task {i}: Perform {agent} analysis on the codebase"
            response = f"""
## {agent.upper()} Agent Response

This is a simulated response from the {agent} agent.

### Analysis Results
- Found {i * 10} relevant files
- Identified {i * 5} key patterns
- Generated {i * 3} recommendations

### Summary
The {agent} agent has completed the requested task successfully.
This response demonstrates the session logging capability.
            """.strip()
            
            # Log the response
            log_path = log_agent_response(
                agent_name=agent,
                request=request,
                response=response,
                metadata={
                    "model": "claude-3",
                    "tokens": len(response.split()),
                    "task_number": i,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            if log_path:
                print(f"  ✓ Logged to: {log_path.name}")
            else:
                print(f"  ✗ Failed to log {agent} response")
        
        print()
        
        # Verify logged responses
        print("Verifying Logged Responses:")
        print("-" * 40)
        
        session_dir = get_session_directory()
        if session_dir and session_dir.exists():
            response_files = sorted(session_dir.glob("response_*.json"))
            
            for response_file in response_files:
                with open(response_file, 'r') as f:
                    data = json.load(f)
                    agent = data['metadata'].get('agent', 'unknown')
                    summary = data['request_summary'][:50] + "..."
                    print(f"  {response_file.name}: [{agent}] {summary}")
            
            print(f"\nTotal responses logged: {len(response_files)}")
        else:
            print("Session directory not found")
        
    finally:
        # Clean up
        if 'CLAUDE_SESSION_ID' in os.environ:
            del os.environ['CLAUDE_SESSION_ID']
    
    print("\n" + "=" * 60)
    print("CLI integration test complete!")


def test_hook_integration():
    """Test hook-based logging integration."""
    print("\nTesting Hook Integration")
    print("=" * 60)
    
    # Set session ID
    test_session_id = f"hook_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    try:
        from claude_mpm.hooks.builtin.session_response_logger_hook import SessionResponseLoggerHook
        from claude_mpm.services.claude_session_logger import get_session_logger
        
        # Reset the singleton logger to pick up new session ID
        logger = get_session_logger()
        logger.session_id = test_session_id
        
        # Create hook instance
        hook = SessionResponseLoggerHook({
            'enabled': True,
            'log_all_agents': True,
            'min_response_length': 10
        })
        
        # Simulate agent response event
        event = {
            'agent_name': 'test_hook_agent',
            'request': 'Test the hook-based logging system',
            'response': 'This is a test response from the hook integration test. ' * 5,
            'model': 'claude-3',
            'tokens': 100,
            'tools_used': ['read', 'write']
        }
        
        # Process event through hook
        result = hook.on_agent_response(event)
        
        print(f"Hook processed successfully")
        print(f"Session ID: {test_session_id}")
        
        # Get the session logger to check its state
        from claude_mpm.services.claude_session_logger import get_session_logger
        logger = get_session_logger()
        print(f"Logger Session ID: {logger.session_id}")
        print(f"Logger Enabled: {logger.is_enabled()}")
        
        # Check if response was logged
        session_dir = Path.cwd() / "docs" / "responses" / test_session_id
        if session_dir.exists():
            files = list(session_dir.glob("response_*.json"))
            print(f"✓ Response logged via hook: {len(files)} file(s)")
        else:
            print("✗ No response logged via hook")
        
    finally:
        if 'CLAUDE_SESSION_ID' in os.environ:
            del os.environ['CLAUDE_SESSION_ID']
    
    print("=" * 60)


if __name__ == "__main__":
    print("Claude MPM Session Logging Integration Tests")
    print("=" * 70)
    
    test_cli_integration()
    test_hook_integration()
    
    print("\n" + "=" * 70)
    print("All integration tests complete!")
    print("\nCheck .claude-mpm/responses/ for logged sessions")