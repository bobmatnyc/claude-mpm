#!/usr/bin/env python3
"""
Test Session Logger

Test script for the Claude session response logging system.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.claude_session_logger import ClaudeSessionLogger, get_session_logger


def test_basic_logging():
    """Test basic logging functionality."""
    print("Testing Claude Session Logger")
    print("=" * 50)
    
    # Create logger instance
    logger = ClaudeSessionLogger()
    
    # Check session ID
    print(f"Session ID: {logger.session_id}")
    print(f"Session Path: {logger.get_session_path()}")
    print(f"Logging Enabled: {logger.is_enabled()}")
    print()
    
    # Test logging a response
    if logger.is_enabled():
        # Log test responses
        for i in range(3):
            response_path = logger.log_response(
                request_summary=f"Test request {i+1}: Testing the logging system",
                response_content=f"This is test response {i+1}. The logging system is working correctly. " * 10,
                metadata={
                    "agent": "test_agent",
                    "model": "claude-3",
                    "test_number": i + 1
                }
            )
            
            if response_path:
                print(f"✓ Logged response {i+1}: {response_path}")
            else:
                print(f"✗ Failed to log response {i+1}")
        
        print()
        print(f"Check session directory: {logger.get_session_path()}")
    else:
        print("Logging is disabled (no session ID available)")


def test_with_env_session():
    """Test with environment variable session ID."""
    print("\nTesting with environment session ID")
    print("-" * 50)
    
    # Set a test session ID
    test_session_id = "test-session-123"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    # Create new logger (should pick up env var)
    logger = ClaudeSessionLogger()
    
    print(f"Session ID from env: {logger.session_id}")
    
    # Log a test response
    response_path = logger.log_response(
        request_summary="Environment session test",
        response_content="This response uses session ID from environment variable.",
        metadata={"source": "env_test"}
    )
    
    if response_path:
        print(f"✓ Logged to: {response_path}")
    
    # Clean up
    del os.environ['CLAUDE_SESSION_ID']


def test_singleton():
    """Test singleton pattern."""
    print("\nTesting singleton pattern")
    print("-" * 50)
    
    logger1 = get_session_logger()
    logger2 = get_session_logger()
    
    print(f"Same instance: {logger1 is logger2}")
    print(f"Session ID: {logger1.session_id}")


def list_sessions():
    """List all existing sessions."""
    print("\nExisting Sessions")
    print("-" * 50)
    
    responses_dir = Path.cwd() / "docs" / "responses"
    
    if not responses_dir.exists():
        print("No responses directory found")
        return
    
    sessions = [d for d in responses_dir.iterdir() if d.is_dir()]
    
    if not sessions:
        print("No sessions found")
        return
    
    for session_dir in sorted(sessions):
        response_files = list(session_dir.glob("response_*.json"))
        print(f"  {session_dir.name}: {len(response_files)} responses")


if __name__ == "__main__":
    print("Claude Session Logger Test")
    print("=" * 70)
    
    # Run tests
    test_basic_logging()
    test_with_env_session()
    test_singleton()
    list_sessions()
    
    print("\n" + "=" * 70)
    print("Tests complete!")