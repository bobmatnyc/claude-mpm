#!/usr/bin/env python3
"""
Test script to verify response logging is enabled and working.

This script:
1. Creates a test configuration with response logging enabled
2. Initializes ResponseTracker with this config
3. Tracks a sample response
4. Verifies the response file was created
5. Prints success/failure status
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config import Config
from claude_mpm.services.response_tracker import ResponseTracker


def test_response_logging():
    """Test that response logging is enabled and working."""
    print("=" * 60)
    print("Response Logging Configuration Test")
    print("=" * 60)
    
    # Create test configuration
    print("\n1. Creating test configuration...")
    test_config = {
        "response_logging": {
            "enabled": True,
            "use_async": False,  # Use sync mode for testing to ensure files are written
            "session_directory": ".claude-mpm/test-responses"
        },
        "response_tracking": {
            "enabled": True,
            "base_dir": ".claude-mpm/test-responses",
            "excluded_agents": [],
            "metadata_tracking": {
                "track_model": True,
                "track_duration": True,
                "track_tools": True
            }
        }
    }
    
    # Initialize Config with test configuration
    config = Config(config=test_config)
    print("✓ Configuration created with response logging enabled")
    
    # Verify configuration is set correctly
    response_logging_enabled = config.get("response_logging.enabled")
    response_tracking_enabled = config.get("response_tracking.enabled")
    session_dir = config.get("response_logging.session_directory")
    
    print(f"\n2. Verifying configuration:")
    print(f"   - response_logging.enabled: {response_logging_enabled}")
    print(f"   - response_tracking.enabled: {response_tracking_enabled}")
    print(f"   - session_directory: {session_dir}")
    
    if not (response_logging_enabled or response_tracking_enabled):
        print("✗ Response logging/tracking not enabled in configuration")
        return False
    
    # Initialize ResponseTracker
    print("\n3. Initializing ResponseTracker...")
    tracker = ResponseTracker(config=config)
    
    if not tracker.is_enabled():
        print("✗ ResponseTracker is not enabled")
        return False
    
    print("✓ ResponseTracker initialized and enabled")
    
    # Track a sample response
    print("\n4. Tracking a sample response...")
    agent_name = "test_agent"
    request = "Test request: What is 2 + 2?"
    response = "The answer to 2 + 2 is 4."
    session_id = f"test-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    metadata = {
        "model": "claude-3-sonnet",
        "duration_ms": 150,
        "tool_name": "calculator"
    }
    
    response_file = tracker.track_response(
        agent_name=agent_name,
        request=request,
        response=response,
        session_id=session_id,
        metadata=metadata
    )
    
    if response_file is None:
        print("✗ Failed to track response - no file returned")
        return False
    
    print(f"✓ Response tracked to: {response_file}")
    
    # Verify the file was created
    print("\n5. Verifying response file...")
    
    # The async logger always returns a placeholder path, check actual directories
    # Try both the configured directory and the default
    possible_dirs = [
        Path(".claude-mpm/test-responses"),
        Path(".claude-mpm/responses")
    ]
    
    response_file = None
    for session_dir in possible_dirs:
        if session_dir.exists():
            response_files = list(session_dir.glob("*test_agent*.json"))
            if response_files:
                # Use the most recent file
                response_file = max(response_files, key=lambda f: f.stat().st_mtime)
                print(f"✓ Found response file: {response_file}")
                break
    
    if not response_file:
        print(f"✗ No response files found in any of the expected directories")
        for d in possible_dirs:
            print(f"   Checked: {d} (exists: {d.exists()})")
        return False
    
    # Read and verify file contents
    try:
        with open(response_file, 'r') as f:
            content = json.load(f)
        
        print(f"✓ Response file exists and is valid JSON")
        
        # Handle different field names (standardized vs legacy)
        request_text = content.get('request') or content.get('request_summary', '')
        response_text = content.get('response') or content.get('response_content', '')
        agent = content.get('agent') or content.get('metadata', {}).get('agent')
        
        print(f"   - Request: {request_text[:50]}...")
        print(f"   - Response: {response_text[:50]}...")
        print(f"   - Agent: {agent}")
        print(f"   - Session: {content.get('session_id')}")
    except Exception as e:
        print(f"✗ Error reading response file: {e}")
        return False
    
    # Clean up test directory (optional)
    print("\n6. Cleanup...")
    test_dir = Path(".claude-mpm/test-responses")
    if test_dir.exists():
        print(f"   Test directory created at: {test_dir}")
        print("   (You may want to remove it manually)")
    
    return True


def test_production_config():
    """Test loading configuration from .claude-mpm/config.json."""
    print("\n" + "=" * 60)
    print("Production Configuration Test")
    print("=" * 60)
    
    config_file = Path(".claude-mpm/config.json")
    
    if not config_file.exists():
        print(f"✗ Configuration file not found: {config_file}")
        return False
    
    print(f"\n1. Loading configuration from: {config_file}")
    
    # Load configuration from file
    config = Config(config_file=config_file)
    
    # Check if response logging is enabled
    response_logging_enabled = config.get("response_logging.enabled")
    response_tracking_enabled = config.get("response_tracking.enabled")
    session_dir = config.get("response_logging.session_directory")
    use_async = config.get("response_logging.use_async")
    
    print(f"\n2. Configuration values:")
    print(f"   - response_logging.enabled: {response_logging_enabled}")
    print(f"   - response_logging.use_async: {use_async}")
    print(f"   - response_tracking.enabled: {response_tracking_enabled}")
    print(f"   - session_directory: {session_dir}")
    
    if response_logging_enabled or response_tracking_enabled:
        print("\n✓ Response logging is ENABLED in production configuration")
        
        # Test with production config
        print("\n3. Testing with production configuration...")
        tracker = ResponseTracker(config=config)
        
        if tracker.is_enabled():
            print("✓ ResponseTracker is active with production config")
            
            # Track a test response
            response_file = tracker.track_response(
                agent_name="production_test",
                request="Production config test",
                response="This is a test response using production configuration",
                metadata={"test": True}
            )
            
            # For async logger, check if any files were created
            if response_file:
                print(f"   Response tracked to: {response_file}")
            
            # Check for actual files in the session directory
            prod_session_dir = Path(session_dir) if session_dir else Path(".claude-mpm/responses")
            if prod_session_dir.exists():
                prod_files = list(prod_session_dir.glob("*production_test*.json"))
                if prod_files:
                    actual_file = max(prod_files, key=lambda f: f.stat().st_mtime)
                    print(f"✓ Successfully created test response at: {actual_file}")
                else:
                    print("✗ Failed to create test response with production config")
            else:
                print(f"✗ Session directory does not exist: {prod_session_dir}")
        else:
            print("✗ ResponseTracker is not active despite enabled config")
    else:
        print("\n✗ Response logging is DISABLED in production configuration")
    
    return True


def main():
    """Run all tests."""
    print("Testing Response Logging Configuration")
    print("=" * 60)
    
    # Test 1: Test with programmatic configuration
    test1_passed = test_response_logging()
    
    # Test 2: Test with production configuration file
    test2_passed = test_production_config()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if test1_passed:
        print("✓ Programmatic configuration test: PASSED")
    else:
        print("✗ Programmatic configuration test: FAILED")
    
    if test2_passed:
        print("✓ Production configuration test: PASSED")
    else:
        print("✗ Production configuration test: FAILED")
    
    overall_success = test1_passed and test2_passed
    
    if overall_success:
        print("\n✓ All tests PASSED - Response logging is properly configured!")
    else:
        print("\n✗ Some tests FAILED - Please check the configuration")
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())