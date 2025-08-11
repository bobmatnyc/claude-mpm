#!/usr/bin/env python3
"""
Test Hook Handler Response Tracking Integration

Tests that the hook handler properly integrates with the ResponseTracker
to capture agent responses during Task delegations.

WHY: This test verifies the complete integration between hook_handler.py
and the ResponseTracker service, ensuring agent responses are properly
captured during real delegation scenarios.
"""

import os
import sys
import json
import yaml
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set debug mode for visibility
os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'


def test_hook_handler_integration():
    """Test that hook handler can initialize and use ResponseTracker."""
    print("\n" + "="*60)
    print("TEST: Hook Handler Response Tracking Integration")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test configuration file
        config_file = Path(tmpdir) / "test_config.yaml"
        config_data = {
            'response_tracking': {
                'enabled': True,
                'base_dir': f'{tmpdir}/responses',
                'metadata_tracking': {
                    'track_model': True,
                    'track_duration': True,
                    'track_tools': True
                }
            },
            'response_logging': {
                'enabled': True,
                'session_directory': f'{tmpdir}/responses',
                'use_async': False
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Set config file environment variable for hook handler
        os.environ['CLAUDE_PM_CONFIG_FILE'] = str(config_file)
        
        try:
            # Import hook handler components
            from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
            
            # Create handler instance
            handler = ClaudeHookHandler()
            
            # Verify response tracking was initialized
            assert handler.response_tracking_enabled, "Response tracking should be enabled"
            assert handler.response_tracker is not None, "Response tracker should be initialized"
            print("✅ Hook handler initialized response tracking successfully")
            
            # Simulate a Task delegation
            session_id = "test-session-hook-123"
            agent_type = "research"
            
            # Track delegation
            request_data = {
                'prompt': 'Research the latest trends in AI',
                'description': 'Conduct research on AI advancements',
                'agent_type': agent_type
            }
            handler._track_delegation(session_id, agent_type, request_data)
            
            # Verify delegation was tracked
            assert session_id in handler.delegation_requests, "Delegation request should be tracked"
            print("✅ Delegation request tracked successfully")
            
            # Simulate Task completion event
            completion_event = {
                'tool_name': 'Task',
                'session_id': session_id,
                'exit_code': 0,
                'output': 'Research completed: AI trends include LLMs, multimodal models, and edge computing.',
                'duration_ms': 5000,
                'cwd': tmpdir
            }
            
            # Track agent response
            handler._track_agent_response(session_id, agent_type, completion_event)
            
            # Verify response was tracked to file system
            response_dir = Path(tmpdir) / "responses" / session_id
            assert response_dir.exists(), f"Session directory should exist at {response_dir}"
            
            response_files = list(response_dir.glob("*.json"))
            assert len(response_files) > 0, "Response file should be created"
            print(f"✅ Response tracked to file: {response_files[0]}")
            
            # Verify file contents
            with open(response_files[0], 'r') as f:
                data = json.load(f)
            
            assert data['session_id'] == session_id, "Session ID should match"
            assert data['agent'] == agent_type, "Agent type should match"
            assert 'Research the latest trends in AI' in data['request'], "Request should be captured"
            assert 'AI trends include LLMs' in data['response'], "Response should be captured"
            assert data['metadata']['exit_code'] == 0, "Exit code should be captured"
            assert data['metadata']['duration_ms'] == 5000, "Duration should be captured"
            print("✅ Response file contains correct data")
            
            # Test excluded agents
            handler.response_tracker = None  # Reset tracker
            config_data['response_tracking']['excluded_agents'] = ['research']
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            # Reinitialize handler with updated config
            handler = ClaudeHookHandler()
            
            # Try to track excluded agent
            session_id2 = "test-session-excluded"
            handler._track_delegation(session_id2, "research", request_data)
            handler._track_agent_response(session_id2, "research", completion_event)
            
            # Verify no file was created for excluded agent
            excluded_dir = Path(tmpdir) / "responses" / session_id2
            if excluded_dir.exists():
                excluded_files = list(excluded_dir.glob("*.json"))
                assert len(excluded_files) == 0, "No files should be created for excluded agents"
            print("✅ Excluded agents are not tracked")
            
        finally:
            # Clean up environment
            if 'CLAUDE_PM_CONFIG_FILE' in os.environ:
                del os.environ['CLAUDE_PM_CONFIG_FILE']


def test_disabled_response_tracking():
    """Test that response tracking can be properly disabled."""
    print("\n" + "="*60)
    print("TEST: Disabled Response Tracking in Hook Handler")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config with response tracking disabled
        config_file = Path(tmpdir) / "disabled_config.yaml"
        config_data = {
            'response_tracking': {
                'enabled': False,
                'base_dir': f'{tmpdir}/responses'
            },
            'response_logging': {
                'enabled': False,
                'session_directory': f'{tmpdir}/responses'
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        os.environ['CLAUDE_PM_CONFIG_FILE'] = str(config_file)
        
        try:
            from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
            
            # Create handler with disabled tracking
            handler = ClaudeHookHandler()
            
            # Verify tracking is disabled
            assert not handler.response_tracking_enabled, "Response tracking should be disabled"
            assert handler.response_tracker is None, "Response tracker should not be initialized"
            print("✅ Response tracking properly disabled when configured")
            
            # Try to track - should not create any files
            session_id = "disabled-session"
            handler._track_agent_response(session_id, "test-agent", {
                'output': 'This should not be tracked',
                'exit_code': 0
            })
            
            # Verify no files were created
            response_dir = Path(tmpdir) / "responses"
            if response_dir.exists():
                files = list(response_dir.rglob("*.json"))
                assert len(files) == 0, "No files should be created when disabled"
            print("✅ No tracking occurs when disabled")
            
        finally:
            if 'CLAUDE_PM_CONFIG_FILE' in os.environ:
                del os.environ['CLAUDE_PM_CONFIG_FILE']


def main():
    """Run all hook integration tests."""
    print("\n" + "="*60)
    print("HOOK HANDLER RESPONSE TRACKING INTEGRATION TESTS")
    print("="*60)
    
    try:
        test_hook_handler_integration()
        test_disabled_response_tracking()
        
        print("\n" + "="*60)
        print("✅ ALL HOOK INTEGRATION TESTS PASSED")
        print("="*60)
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())