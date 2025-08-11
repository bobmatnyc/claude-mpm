#!/usr/bin/env python3
"""
Test Hook Integration Comprehensive

Test the session response logger hook integration with different configurations
and scenarios.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def clear_session_env_vars():
    """Clear all session-related environment variables."""
    env_vars = ['CLAUDE_SESSION_ID', 'ANTHROPIC_SESSION_ID', 'SESSION_ID']
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]


def reset_logger_singleton():
    """Reset the logger singleton to pick up new configuration."""
    import claude_mpm.services.claude_session_logger
    claude_mpm.services.claude_session_logger._logger_instance = None


def test_hook_basic_functionality():
    """Test basic hook functionality."""
    print("Testing Hook Basic Functionality")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"hook_basic_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.hooks.builtin.session_response_logger_hook import SessionResponseLoggerHook
    
    # Create hook with basic config
    config = {
        'enabled': True,
        'log_all_agents': True,
        'min_response_length': 20
    }
    
    hook = SessionResponseLoggerHook(config)
    
    # Create test event
    event = {
        'agent_name': 'test_agent',
        'request': 'Test the basic hook functionality',
        'response': 'This is a test response that should be logged by the hook system. ' * 3,
        'model': 'claude-3',
        'tokens': 150,
        'tools_used': ['read', 'write']
    }
    
    # Process event
    result = hook.on_agent_response(event)
    
    # Verify result is unchanged
    print(f"Event unchanged: {'✓' if result == event else '✗'}")
    
    # Check if response was logged
    session_dir = Path.cwd() / "docs" / "responses" / test_session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Response logged: {'✓' if len(files) > 0 else '✗'}")
        
        if files:
            # Check file content
            with open(files[0], 'r') as f:
                data = json.load(f)
                print(f"Correct agent: {'✓' if data['metadata']['agent'] == 'test_agent' else '✗'}")
                print(f"Has metadata: {'✓' if 'model' in data['metadata'] else '✗'}")
    else:
        print("Response logged: ✗")
    
    clear_session_env_vars()
    print()


def test_agent_filtering():
    """Test agent filtering configuration."""
    print("Testing Agent Filtering")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"hook_filter_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.hooks.builtin.session_response_logger_hook import SessionResponseLoggerHook
    
    # Test 1: Exclude specific agents
    config = {
        'enabled': True,
        'log_all_agents': True,
        'excluded_agents': ['test_excluded'],
        'min_response_length': 10
    }
    
    hook = SessionResponseLoggerHook(config)
    
    # Test excluded agent - should NOT be logged
    excluded_event = {
        'agent_name': 'test_excluded',
        'request': 'This should not be logged',
        'response': 'This response should be excluded from logging.',
        'model': 'claude-3'
    }
    
    hook.on_agent_response(excluded_event)
    
    # Test included agent - should be logged
    included_event = {
        'agent_name': 'test_included',
        'request': 'This should be logged',
        'response': 'This response should be included in logging.',
        'model': 'claude-3'
    }
    
    hook.on_agent_response(included_event)
    
    # Check results
    session_dir = Path.cwd() / "docs" / "responses" / test_session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Total files logged: {len(files)}")
        
        if files:
            with open(files[0], 'r') as f:
                data = json.load(f)
                agent = data['metadata']['agent']
                print(f"Correct agent logged: {'✓' if agent == 'test_included' else '✗'}")
                print(f"Excluded agent filtered: {'✓' if agent != 'test_excluded' else '✗'}")
        else:
            print("No files logged: ✗")
    
    # Test 2: Include only specific agents
    test_session_id2 = f"hook_include_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id2
    reset_logger_singleton()
    
    config2 = {
        'enabled': True,
        'log_all_agents': False,
        'logged_agents': ['allowed_agent'],
        'min_response_length': 10
    }
    
    hook2 = SessionResponseLoggerHook(config2)
    
    # Test allowed agent
    allowed_event = {
        'agent_name': 'allowed_agent',
        'request': 'This should be logged',
        'response': 'This response should be logged for allowed agent.',
        'model': 'claude-3'
    }
    
    hook2.on_agent_response(allowed_event)
    
    # Test not-allowed agent
    not_allowed_event = {
        'agent_name': 'not_allowed_agent',
        'request': 'This should not be logged',
        'response': 'This response should not be logged.',
        'model': 'claude-3'
    }
    
    hook2.on_agent_response(not_allowed_event)
    
    # Check results
    session_dir2 = Path.cwd() / "docs" / "responses" / test_session_id2
    if session_dir2.exists():
        files2 = list(session_dir2.glob("response_*.json"))
        print(f"Include-only files logged: {len(files2)}")
        
        if files2:
            with open(files2[0], 'r') as f:
                data = json.load(f)
                agent = data['metadata']['agent']
                print(f"Only allowed agent logged: {'✓' if agent == 'allowed_agent' else '✗'}")
    
    clear_session_env_vars()
    print()


def test_minimum_response_length():
    """Test minimum response length filtering."""
    print("Testing Minimum Response Length Filtering")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"hook_length_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.hooks.builtin.session_response_logger_hook import SessionResponseLoggerHook
    
    config = {
        'enabled': True,
        'log_all_agents': True,
        'min_response_length': 50
    }
    
    hook = SessionResponseLoggerHook(config)
    
    # Test short response - should NOT be logged
    short_event = {
        'agent_name': 'test_agent',
        'request': 'Short response test',
        'response': 'Short response.',  # Less than 50 characters
        'model': 'claude-3'
    }
    
    hook.on_agent_response(short_event)
    
    # Test long response - should be logged
    long_event = {
        'agent_name': 'test_agent',
        'request': 'Long response test',
        'response': 'This is a long response that exceeds the minimum length requirement and should be logged by the system. It contains enough characters to pass the filter.',  # More than 50 characters
        'model': 'claude-3'
    }
    
    hook.on_agent_response(long_event)
    
    # Check results
    session_dir = Path.cwd() / "docs" / "responses" / test_session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Files logged: {len(files)}")
        print(f"Only long response logged: {'✓' if len(files) == 1 else '✗'}")
        
        if files:
            with open(files[0], 'r') as f:
                data = json.load(f)
                response = data['response']
                print(f"Response length: {len(response)} chars")
                print(f"Above minimum: {'✓' if len(response) >= 50 else '✗'}")
    else:
        print("No files logged")
    
    clear_session_env_vars()
    print()


def test_metadata_handling():
    """Test metadata handling in hook."""
    print("Testing Metadata Handling")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"hook_metadata_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.hooks.builtin.session_response_logger_hook import SessionResponseLoggerHook
    
    config = {
        'enabled': True,
        'log_all_agents': True,
        'min_response_length': 10
    }
    
    hook = SessionResponseLoggerHook(config)
    
    # Create event with comprehensive metadata
    event = {
        'agent_name': 'metadata_test_agent',
        'request': 'Test metadata handling in the hook system',
        'response': 'This response tests comprehensive metadata handling and storage.',
        'model': 'claude-3-haiku',
        'tokens': 250,
        'tools_used': ['read', 'write', 'bash'],
        'extra_field': 'should_be_ignored'  # This should not appear in metadata
    }
    
    hook.on_agent_response(event)
    
    # Check logged metadata
    session_dir = Path.cwd() / "docs" / "responses" / test_session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        if files:
            with open(files[0], 'r') as f:
                data = json.load(f)
                metadata = data['metadata']
                
                print(f"Agent in metadata: {'✓' if metadata.get('agent') == 'metadata_test_agent' else '✗'}")
                print(f"Model in metadata: {'✓' if metadata.get('model') == 'claude-3-haiku' else '✗'}")
                print(f"Tokens in metadata: {'✓' if metadata.get('tokens') == 250 else '✗'}")
                print(f"Tools in metadata: {'✓' if metadata.get('tools_used') == ['read', 'write', 'bash'] else '✗'}")
                print(f"Extra field excluded: {'✓' if 'extra_field' not in metadata else '✗'}")
                print(f"No None values: {'✓' if all(v is not None for v in metadata.values()) else '✗'}")
        else:
            print("No files logged: ✗")
    else:
        print("No session directory: ✗")
    
    clear_session_env_vars()
    print()


def test_hook_disabled():
    """Test hook behavior when disabled."""
    print("Testing Hook Disabled State")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"hook_disabled_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.hooks.builtin.session_response_logger_hook import SessionResponseLoggerHook
    
    # Create disabled hook
    config = {
        'enabled': False,
        'log_all_agents': True,
        'min_response_length': 10
    }
    
    hook = SessionResponseLoggerHook(config)
    
    # Create test event
    event = {
        'agent_name': 'disabled_test_agent',
        'request': 'Test disabled hook behavior',
        'response': 'This response should not be logged because the hook is disabled.',
        'model': 'claude-3'
    }
    
    # Process event
    result = hook.on_agent_response(event)
    
    # Check that event is unchanged
    print(f"Event unchanged: {'✓' if result == event else '✗'}")
    
    # Check that nothing was logged
    session_dir = Path.cwd() / "docs" / "responses" / test_session_id
    files_logged = session_dir.exists() and list(session_dir.glob("response_*.json"))
    print(f"No responses logged: {'✓' if not files_logged else '✗'}")
    
    clear_session_env_vars()
    print()


def test_session_start_event():
    """Test session start event handling."""
    print("Testing Session Start Event Handling")
    print("-" * 50)
    
    clear_session_env_vars()
    reset_logger_singleton()
    
    from claude_mpm.hooks.builtin.session_response_logger_hook import SessionResponseLoggerHook
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    config = {
        'enabled': True,
        'log_all_agents': True,
        'min_response_length': 10
    }
    
    hook = SessionResponseLoggerHook(config)
    
    # Test session start event
    session_id = "session_start_test_12345"
    start_event = {
        'session_id': session_id,
        'user': 'test_user',
        'timestamp': datetime.now().isoformat()
    }
    
    # Process session start event
    result = hook.on_session_start(start_event)
    
    print(f"Event unchanged: {'✓' if result == start_event else '✗'}")
    
    # Check if logger session ID was updated
    logger = get_session_logger()
    print(f"Logger session updated: {'✓' if logger.session_id == session_id else '✗'}")
    
    # Test that subsequent responses use the new session ID
    response_event = {
        'agent_name': 'session_start_agent',
        'request': 'Test after session start',
        'response': 'This response should use the updated session ID from the session start event.',
        'model': 'claude-3'
    }
    
    hook.on_agent_response(response_event)
    
    # Check if response was logged to the correct session directory
    session_dir = Path.cwd() / "docs" / "responses" / session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Response logged to new session: {'✓' if len(files) > 0 else '✗'}")
    else:
        print("Response logged to new session: ✗")
    
    clear_session_env_vars()
    print()


if __name__ == "__main__":
    print("Hook Integration Comprehensive Test")
    print("=" * 70)
    
    test_hook_basic_functionality()
    test_agent_filtering()
    test_minimum_response_length()
    test_metadata_handling()
    test_hook_disabled()
    test_session_start_event()
    
    print("=" * 70)
    print("Hook integration tests complete!")