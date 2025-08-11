#!/usr/bin/env python3
"""
Test Response Tracker Integration

Tests the ResponseTracker service integration with the hook handler
and verifies that configuration settings are properly respected.

WHY: This test ensures that the response tracking system works end-to-end,
respects configuration settings, and properly integrates with the existing
session logging infrastructure.
"""

import os
import sys
import json
import yaml
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.response_tracker import ResponseTracker, get_response_tracker
from claude_mpm.services.claude_session_logger import ClaudeSessionLogger
from claude_mpm.core.config import Config


def create_test_config(tmpdir: str, config_data: dict) -> Config:
    """Create a test configuration with a temporary file to avoid loading defaults."""
    config_file = Path(tmpdir) / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    return Config(config_file=config_file)


def test_response_tracker_disabled():
    """Test that ResponseTracker respects disabled configuration."""
    print("\n" + "="*60)
    print("TEST: Response Tracker with Disabled Configuration")
    print("="*60)
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config with response tracking disabled
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
        
        config = create_test_config(tmpdir, config_data)
        tracker = ResponseTracker(config=config)
        
        # Verify tracker is disabled
        assert not tracker.is_enabled(), "Tracker should be disabled when config is disabled"
        print("✅ Tracker correctly disabled when configuration is disabled")
        
        # Try to track a response - should return None
        result = tracker.track_response(
            agent_name="test-agent",
            request="Test request",
            response="Test response",
            session_id="test-session-123"
        )
        
        assert result is None, "track_response should return None when disabled"
        print("✅ track_response returns None when disabled")
        
        # Verify no files were created
        response_dir = Path(tmpdir) / "responses"
        if response_dir.exists():
            files = list(response_dir.rglob("*"))
            assert len(files) == 0, f"No files should be created when disabled, found: {files}"
        print("✅ No files created when tracking is disabled")


def test_response_tracker_enabled():
    """Test that ResponseTracker works when enabled."""
    print("\n" + "="*60)
    print("TEST: Response Tracker with Enabled Configuration")
    print("="*60)
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config with response tracking enabled
        config_data = {
            'response_tracking': {
                'enabled': True,
                'base_dir': f'{tmpdir}/responses',
                'excluded_agents': ['excluded-agent'],
                'metadata_tracking': {
                    'track_model': True,
                    'track_duration': True,
                    'track_tools': True
                }
            },
            'response_logging': {
                'enabled': True,
                'session_directory': f'{tmpdir}/responses',
                'use_async': False  # Use sync for testing
            }
        }
        
        config = create_test_config(tmpdir, config_data)
        tracker = ResponseTracker(config=config)
        
        # Verify tracker is enabled
        assert tracker.is_enabled(), "Tracker should be enabled when config is enabled"
        print("✅ Tracker correctly enabled when configuration is enabled")
        
        # Track a response
        result = tracker.track_response(
            agent_name="test-agent",
            request="Test request for verification",
            response="Test response with content",
            session_id="test-session-456",
            metadata={
                'duration_ms': 1234,
                'tool_name': 'TestTool',
                'exit_code': 0
            }
        )
        
        assert result is not None, "track_response should return a path when enabled"
        assert result.exists(), f"Response file should exist at {result}"
        print(f"✅ Response tracked successfully to: {result}")
        
        # Verify file contents
        with open(result, 'r') as f:
            data = json.load(f)
            
        assert data['session_id'] == 'test-session-456', "Session ID should match"
        assert data['request'] == "Test request for verification", "Request should match"
        assert data['response'] == "Test response with content", "Response should match"
        assert data['agent'] == "test-agent", "Agent name should match"
        assert 'metadata' in data, "Metadata should be present"
        assert data['metadata']['duration_ms'] == 1234, "Duration should be preserved"
        assert data['metadata']['tools_used'] == ['TestTool'], "Tools should be tracked"
        print("✅ Response file contains correct data")


def test_excluded_agents():
    """Test that excluded agents are not tracked."""
    print("\n" + "="*60)
    print("TEST: Excluded Agents")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config with excluded agents
        config_data = {
            'response_tracking': {
                'enabled': True,
                'base_dir': f'{tmpdir}/responses',
                'excluded_agents': ['excluded-agent', 'another_excluded']
            },
            'response_logging': {
                'enabled': True,
                'session_directory': f'{tmpdir}/responses',
                'use_async': False
            }
        }
        
        config = create_test_config(tmpdir, config_data)
        tracker = ResponseTracker(config=config)
        
        # Try to track excluded agent (with hyphen)
        result1 = tracker.track_response(
            agent_name="excluded-agent",
            request="Test",
            response="Test",
            session_id="test-session-789"
        )
        assert result1 is None, "Excluded agent should not be tracked"
        print("✅ Excluded agent 'excluded-agent' not tracked")
        
        # Try to track excluded agent (with underscore - should still match)
        result2 = tracker.track_response(
            agent_name="another_excluded",
            request="Test",
            response="Test",
            session_id="test-session-789"
        )
        assert result2 is None, "Excluded agent with underscore should not be tracked"
        print("✅ Excluded agent 'another_excluded' not tracked")
        
        # Try to track non-excluded agent
        result3 = tracker.track_response(
            agent_name="allowed-agent",
            request="Test",
            response="Test",
            session_id="test-session-789"
        )
        assert result3 is not None, "Non-excluded agent should be tracked"
        print("✅ Non-excluded agent 'allowed-agent' tracked successfully")


def test_session_path_access():
    """Test session path access methods."""
    print("\n" + "="*60)
    print("TEST: Session Path Access")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_data = {
            'response_tracking': {
                'enabled': True,
                'base_dir': f'{tmpdir}/responses'
            },
            'response_logging': {
                'enabled': True,
                'session_directory': f'{tmpdir}/responses',
                'use_async': False
            }
        }
        
        config = create_test_config(tmpdir, config_data)
        tracker = ResponseTracker(config=config)
        
        # Set a session ID
        tracker.set_session_id("my-test-session")
        
        # Get session path
        session_path = tracker.get_session_path()
        assert session_path is not None, "Session path should be available"
        assert "my-test-session" in str(session_path), "Session path should contain session ID"
        print(f"✅ Session path retrieved: {session_path}")


def test_config_fallback():
    """Test configuration fallback from response_tracking to response_logging."""
    print("\n" + "="*60)
    print("TEST: Configuration Fallback")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Only response_logging enabled (no response_tracking section)
        config_data = {
            'response_logging': {
                'enabled': True,
                'session_directory': f'{tmpdir}/responses',
                'use_async': False
            }
        }
        
        config = create_test_config(tmpdir, config_data)
        tracker = ResponseTracker(config=config)
        
        # Should still be enabled via fallback
        assert tracker.is_enabled(), "Tracker should be enabled via response_logging fallback"
        print("✅ Tracker enabled via response_logging configuration fallback")
        
        # Track a response to verify it works
        result = tracker.track_response(
            agent_name="test-agent",
            request="Fallback test",
            response="Fallback response",
            session_id="fallback-session"
        )
        
        assert result is not None, "Tracking should work with fallback config"
        print("✅ Response tracking works with fallback configuration")


def test_response_logging_disabled_override():
    """Test that response_tracking disabled overrides response_logging enabled."""
    print("\n" + "="*60)
    print("TEST: Response Tracking Disabled Override")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # response_logging enabled but response_tracking explicitly disabled
        config_data = {
            'response_tracking': {
                'enabled': False,  # Explicitly disabled
                'base_dir': f'{tmpdir}/responses'
            },
            'response_logging': {
                'enabled': True,  # This should be overridden
                'session_directory': f'{tmpdir}/responses',
                'use_async': False
            }
        }
        
        config = create_test_config(tmpdir, config_data)
        tracker = ResponseTracker(config=config)
        
        # Should be disabled because response_tracking explicitly says so
        assert not tracker.is_enabled(), "Tracker should be disabled when response_tracking.enabled is False"
        print("✅ response_tracking.enabled=False correctly overrides response_logging.enabled=True")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("RESPONSE TRACKER INTEGRATION TESTS")
    print("="*60)
    
    # Clear any singleton instance from previous runs
    import claude_mpm.services.response_tracker as rt_module
    rt_module._tracker_instance = None
    
    try:
        # Run all tests
        test_response_tracker_disabled()
        test_response_tracker_enabled()
        test_excluded_agents()
        test_session_path_access()
        test_config_fallback()
        test_response_logging_disabled_override()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
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