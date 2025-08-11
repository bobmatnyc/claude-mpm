#!/usr/bin/env python3
"""
Test Session ID Detection from Environment Variables

Comprehensive test to verify session ID detection from various environment variables
and fallback behavior.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.claude_session_logger import ClaudeSessionLogger


def clear_session_env_vars():
    """Clear all session-related environment variables."""
    env_vars = ['CLAUDE_SESSION_ID', 'ANTHROPIC_SESSION_ID', 'SESSION_ID']
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]


def test_claude_session_id():
    """Test CLAUDE_SESSION_ID detection."""
    print("Testing CLAUDE_SESSION_ID detection")
    print("-" * 50)
    
    clear_session_env_vars()
    test_id = "claude-test-session-123"
    os.environ['CLAUDE_SESSION_ID'] = test_id
    
    # Force new instance by clearing singleton
    from claude_mpm.services.claude_session_logger import _logger_instance
    import claude_mpm.services.claude_session_logger
    claude_mpm.services.claude_session_logger._logger_instance = None
    
    logger = ClaudeSessionLogger()
    
    print(f"Set CLAUDE_SESSION_ID: {test_id}")
    print(f"Logger detected: {logger.session_id}")
    print(f"Match: {'✓' if logger.session_id == test_id else '✗'}")
    
    # Test logging works
    response_path = logger.log_response(
        "Test CLAUDE_SESSION_ID",
        "Testing CLAUDE_SESSION_ID environment variable detection",
        {"test": "claude_session_id"}
    )
    print(f"Logged response: {'✓' if response_path else '✗'}")
    
    clear_session_env_vars()
    print()


def test_anthropic_session_id():
    """Test ANTHROPIC_SESSION_ID detection."""
    print("Testing ANTHROPIC_SESSION_ID detection")
    print("-" * 50)
    
    clear_session_env_vars()
    test_id = "anthropic-test-session-456"
    os.environ['ANTHROPIC_SESSION_ID'] = test_id
    
    # Force new instance
    import claude_mpm.services.claude_session_logger
    claude_mpm.services.claude_session_logger._logger_instance = None
    
    logger = ClaudeSessionLogger()
    
    print(f"Set ANTHROPIC_SESSION_ID: {test_id}")
    print(f"Logger detected: {logger.session_id}")
    print(f"Match: {'✓' if logger.session_id == test_id else '✗'}")
    
    # Test logging works
    response_path = logger.log_response(
        "Test ANTHROPIC_SESSION_ID",
        "Testing ANTHROPIC_SESSION_ID environment variable detection",
        {"test": "anthropic_session_id"}
    )
    print(f"Logged response: {'✓' if response_path else '✗'}")
    
    clear_session_env_vars()
    print()


def test_generic_session_id():
    """Test generic SESSION_ID detection."""
    print("Testing SESSION_ID detection")
    print("-" * 50)
    
    clear_session_env_vars()
    test_id = "generic-test-session-789"
    os.environ['SESSION_ID'] = test_id
    
    # Force new instance
    import claude_mpm.services.claude_session_logger
    claude_mpm.services.claude_session_logger._logger_instance = None
    
    logger = ClaudeSessionLogger()
    
    print(f"Set SESSION_ID: {test_id}")
    print(f"Logger detected: {logger.session_id}")
    print(f"Match: {'✓' if logger.session_id == test_id else '✗'}")
    
    # Test logging works
    response_path = logger.log_response(
        "Test SESSION_ID",
        "Testing SESSION_ID environment variable detection",
        {"test": "session_id"}
    )
    print(f"Logged response: {'✓' if response_path else '✗'}")
    
    clear_session_env_vars()
    print()


def test_priority_order():
    """Test priority order when multiple session IDs are set."""
    print("Testing environment variable priority order")
    print("-" * 50)
    
    clear_session_env_vars()
    
    # Set all three environment variables
    os.environ['SESSION_ID'] = "generic-session"
    os.environ['ANTHROPIC_SESSION_ID'] = "anthropic-session"
    os.environ['CLAUDE_SESSION_ID'] = "claude-session"
    
    # Force new instance
    import claude_mpm.services.claude_session_logger
    claude_mpm.services.claude_session_logger._logger_instance = None
    
    logger = ClaudeSessionLogger()
    
    print(f"Set SESSION_ID: generic-session")
    print(f"Set ANTHROPIC_SESSION_ID: anthropic-session")
    print(f"Set CLAUDE_SESSION_ID: claude-session")
    print(f"Logger chose: {logger.session_id}")
    
    # Should choose CLAUDE_SESSION_ID (highest priority)
    expected = "claude-session"
    print(f"Priority correct: {'✓' if logger.session_id == expected else '✗'}")
    
    clear_session_env_vars()
    print()


def test_fallback_timestamp():
    """Test fallback to timestamp-based session ID."""
    print("Testing timestamp fallback when no env vars set")
    print("-" * 50)
    
    clear_session_env_vars()
    
    # Capture time before logger creation
    before_time = datetime.now().strftime('session_%Y%m%d_%H%M%S')
    
    # Force new instance
    import claude_mpm.services.claude_session_logger
    claude_mpm.services.claude_session_logger._logger_instance = None
    
    logger = ClaudeSessionLogger()
    
    # Capture time after
    after_time = datetime.now().strftime('session_%Y%m%d_%H%M%S')
    
    print(f"No environment variables set")
    print(f"Generated session ID: {logger.session_id}")
    print(f"Expected pattern: session_YYYYMMDD_HHMMSS")
    
    # Check if it follows the expected pattern
    import re
    pattern = r'session_\d{8}_\d{6}'
    matches_pattern = re.match(pattern, logger.session_id) is not None
    print(f"Matches pattern: {'✓' if matches_pattern else '✗'}")
    
    # Test logging works with generated ID
    response_path = logger.log_response(
        "Test timestamp fallback",
        "Testing timestamp-based session ID generation",
        {"test": "timestamp_fallback"}
    )
    print(f"Logged response: {'✓' if response_path else '✗'}")
    
    print()


def test_session_id_persistence():
    """Test that session ID persists across multiple calls."""
    print("Testing session ID persistence")
    print("-" * 50)
    
    clear_session_env_vars()
    os.environ['CLAUDE_SESSION_ID'] = "persistence-test-session"
    
    # Force new instance
    import claude_mpm.services.claude_session_logger
    claude_mpm.services.claude_session_logger._logger_instance = None
    
    logger = ClaudeSessionLogger()
    first_id = logger.session_id
    
    # Log multiple responses
    for i in range(3):
        response_path = logger.log_response(
            f"Persistence test {i+1}",
            f"Testing session ID persistence - response {i+1}",
            {"test": "persistence", "response_num": i+1}
        )
        
        # Check session ID hasn't changed
        current_id = logger.session_id
        if current_id != first_id:
            print(f"✗ Session ID changed from {first_id} to {current_id}")
            return
    
    print(f"Session ID: {first_id}")
    print(f"Persistence: ✓ (3 responses logged with same session ID)")
    
    clear_session_env_vars()
    print()


def test_manual_session_override():
    """Test manual session ID override."""
    print("Testing manual session ID override")
    print("-" * 50)
    
    clear_session_env_vars()
    os.environ['CLAUDE_SESSION_ID'] = "original-session"
    
    # Force new instance
    import claude_mpm.services.claude_session_logger
    claude_mpm.services.claude_session_logger._logger_instance = None
    
    logger = ClaudeSessionLogger()
    original_id = logger.session_id
    
    print(f"Original session ID: {original_id}")
    
    # Override manually
    override_id = "manual-override-session"
    logger.set_session_id(override_id)
    
    print(f"Override session ID: {override_id}")
    print(f"Current session ID: {logger.session_id}")
    print(f"Override successful: {'✓' if logger.session_id == override_id else '✗'}")
    
    # Test logging with new ID
    response_path = logger.log_response(
        "Test manual override",
        "Testing manual session ID override functionality",
        {"test": "manual_override"}
    )
    print(f"Logged with new ID: {'✓' if response_path else '✗'}")
    
    # Verify it was logged to the override session directory
    if response_path:
        expected_dir = override_id
        actual_dir = response_path.parent.name
        print(f"Logged to correct directory: {'✓' if actual_dir == expected_dir else '✗'}")
    
    clear_session_env_vars()
    print()


if __name__ == "__main__":
    print("Session ID Detection Comprehensive Test")
    print("=" * 70)
    
    test_claude_session_id()
    test_anthropic_session_id()
    test_generic_session_id()
    test_priority_order()
    test_fallback_timestamp()
    test_session_id_persistence()
    test_manual_session_override()
    
    print("=" * 70)
    print("Session ID detection tests complete!")
    print("\nSummary of session ID priority:")
    print("1. CLAUDE_SESSION_ID (highest priority)")
    print("2. ANTHROPIC_SESSION_ID (medium priority)")
    print("3. SESSION_ID (low priority)")
    print("4. Timestamp-based generation (fallback)")