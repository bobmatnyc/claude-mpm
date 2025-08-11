#!/usr/bin/env python3
"""
Simple Response Logging Test

A focused test to verify that logging is actually working in either async or sync mode.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the src directory to the path so we can import claude_mpm
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from claude_mpm.services.claude_session_logger import get_session_logger, ClaudeSessionLogger
    from claude_mpm.services.async_session_logger import get_async_logger
    from claude_mpm.core.config import Config
except ImportError as e:
    print(f"Failed to import: {e}")
    sys.exit(1)


def test_sync_logging():
    """Test synchronous logging."""
    print("🧪 Testing Sync Logging...")
    
    # Create a logger with sync mode
    config = Config()
    logger = ClaudeSessionLogger(config=config, use_async=False)
    
    test_session = f"sync_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger.set_session_id(test_session)
    
    print(f"Session ID: {test_session}")
    print(f"Base dir: {logger.base_dir}")
    
    # Log a test response
    log_path = logger.log_response(
        request_summary="Test sync logging request",
        response_content="This is a test response for synchronous logging verification. " * 10,
        metadata={"test": "sync_verification", "agent": "sync_test_agent"},
        agent="sync_test_agent"
    )
    
    if log_path and log_path.exists():
        print(f"✅ Sync log created: {log_path}")
        
        # Read and validate content
        with open(log_path, 'r') as f:
            data = json.load(f)
        
        print(f"✓ Contains required fields: {list(data.keys())}")
        return True
    else:
        print("❌ Sync log not created")
        return False


def test_async_logging():
    """Test asynchronous logging."""
    print("\n🧪 Testing Async Logging...")
    
    try:
        # Get async logger
        async_logger = get_async_logger()
        test_session = f"async_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        async_logger.set_session_id(test_session)
        
        print(f"Session ID: {test_session}")
        print(f"Base dir: {async_logger.base_dir}")
        print(f"Async enabled: {async_logger.enable_async}")
        print(f"Format: {async_logger.log_format}")
        
        # Log a test response
        success = async_logger.log_response(
            request_summary="Test async logging request",
            response_content="This is a test response for asynchronous logging verification. " * 10,
            metadata={"test": "async_verification", "agent": "async_test_agent"},
            agent="async_test_agent"
        )
        
        if success:
            print("✅ Async log queued successfully")
            
            # Give a moment for async processing
            time.sleep(1)
            
            # Check if files were created in session directory
            session_dir = async_logger.base_dir / test_session
            if session_dir.exists():
                log_files = list(session_dir.glob("*.json"))
                if log_files:
                    print(f"✅ Found {len(log_files)} log files in session directory")
                    
                    # Read one file to validate
                    with open(log_files[0], 'r') as f:
                        data = json.load(f)
                    print(f"✓ Sample file contains fields: {list(data.keys())}")
                    return True
                else:
                    print("❌ No log files found in session directory")
                    return False
            else:
                print(f"❌ Session directory not created: {session_dir}")
                return False
        else:
            print("❌ Async log failed to queue")
            return False
            
    except Exception as e:
        print(f"❌ Async logging test failed: {e}")
        return False


def test_hook_logger():
    """Test the hook system's logger."""
    print("\n🧪 Testing Hook Logger...")
    
    try:
        # Get the session logger used by hooks
        hook_logger = get_session_logger()
        test_session = f"hook_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        hook_logger.set_session_id(test_session)
        
        print(f"Session ID: {test_session}")
        print(f"Enabled: {hook_logger.is_enabled()}")
        print(f"Session path: {hook_logger.get_session_path()}")
        
        # Log a test response
        log_path = hook_logger.log_response(
            request_summary="Test hook logging request",
            response_content="This is a test response for hook logging verification. " * 10,
            metadata={"test": "hook_verification", "agent": "hook_test_agent"},
            agent="hook_test_agent"
        )
        
        if log_path:
            print(f"✅ Hook log created or queued")
            
            # For async mode, check session directory
            session_dir = hook_logger.get_session_path()
            time.sleep(1)  # Allow async processing
            
            if session_dir and session_dir.exists():
                log_files = list(session_dir.glob("*.json"))
                if log_files:
                    print(f"✅ Found {len(log_files)} files in hook session directory")
                    return True
            
            # For sync mode, check specific path
            if hasattr(log_path, 'exists') and log_path.exists():
                print(f"✅ Hook log file exists: {log_path}")
                return True
                
            print("⚠️  Hook log path returned but file not found")
            return False
        else:
            print("❌ Hook log not created")
            return False
            
    except Exception as e:
        print(f"❌ Hook logging test failed: {e}")
        return False


def main():
    """Run all logging tests."""
    print("Simple Response Logging Test")
    print("=" * 40)
    
    # Change to project root if needed
    if os.path.basename(os.getcwd()) == 'scripts':
        os.chdir('..')
        print(f"Changed to project root: {os.getcwd()}")
    
    tests = [
        ("Sync Logging", test_sync_logging),
        ("Async Logging", test_async_logging), 
        ("Hook Logger", test_hook_logger),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All logging tests passed!")
        return True
    else:
        print("⚠️  Some logging tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)