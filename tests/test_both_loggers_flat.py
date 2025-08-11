#!/usr/bin/env python3
"""Test both sync and async loggers with flat directory structure."""

import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.claude_session_logger import ClaudeSessionLogger
from claude_mpm.services.async_session_logger import AsyncSessionLogger
from claude_mpm.core.config import Config


def test_sync_logger_with_config():
    """Test sync logger using configuration."""
    print("\n=== Testing Sync Logger with Config ===")
    
    config = Config()
    logger = ClaudeSessionLogger(use_async=False, config=config)
    logger.set_session_id("sync_config_test")
    
    # Log a few responses
    for i in range(3):
        agent = ["pm", "engineer", "qa"][i]
        result = logger.log_response(
            request_summary=f"Sync test {i+1}",
            response_content=f"Response from {agent} using sync logger",
            metadata={"sync": True},
            agent=agent
        )
        print(f"  Logged: {result.name if result else 'Failed'}")
        time.sleep(0.01)
    
    # Check files
    files = list(Path(".claude-mpm/responses").glob("sync_config_test-*.json"))
    print(f"  Created {len(files)} files with sync logger")
    return len(files) == 3


def test_async_logger_with_config():
    """Test async logger using configuration."""
    print("\n=== Testing Async Logger with Config ===")
    
    config = Config()
    logger = AsyncSessionLogger(enable_async=True, config=config)
    logger.set_session_id("async_config_test")
    
    # Log a few responses
    for i in range(3):
        agent = ["pm", "engineer", "qa"][i]
        success = logger.log_response(
            request_summary=f"Async test {i+1}",
            response_content=f"Response from {agent} using async logger",
            metadata={"async": True},
            agent=agent
        )
        print(f"  Queued: {success}")
        time.sleep(0.01)
    
    # Flush and wait
    logger.flush(timeout=2.0)
    time.sleep(0.1)  # Give a bit more time for files to be written
    
    # Check files
    files = list(Path(".claude-mpm/responses").glob("async_config_test-*.json"))
    print(f"  Created {len(files)} files with async logger")
    
    # Cleanup
    logger.shutdown()
    return len(files) == 3


def test_mixed_sessions():
    """Test that different sessions coexist in flat structure."""
    print("\n=== Testing Mixed Sessions in Flat Structure ===")
    
    config = Config()
    
    # Create multiple loggers with different sessions
    sessions = ["session_a", "session_b", "session_c"]
    file_count = 0
    
    for session_id in sessions:
        logger = ClaudeSessionLogger(use_async=False, config=config)
        logger.set_session_id(session_id)
        
        result = logger.log_response(
            request_summary=f"Request from {session_id}",
            response_content=f"Response for {session_id}",
            agent="test"
        )
        
        if result:
            print(f"  Created: {result.name}")
            file_count += 1
        
        time.sleep(0.01)
    
    # Verify all files are in the same directory
    response_dir = Path(".claude-mpm/responses")
    all_files = list(response_dir.glob("*.json"))
    
    # Check for any subdirectories (should be none)
    subdirs = [d for d in response_dir.iterdir() if d.is_dir()]
    
    print(f"  Total files in flat directory: {len(all_files)}")
    print(f"  Subdirectories found: {len(subdirs)}")
    
    return file_count == 3 and len(subdirs) == 0


def main():
    """Run all tests."""
    print("Testing Both Loggers with Flat Directory Structure")
    print("=" * 60)
    
    try:
        # Run tests
        sync_ok = test_sync_logger_with_config()
        async_ok = test_async_logger_with_config()
        mixed_ok = test_mixed_sessions()
        
        print("\n" + "=" * 60)
        print("Test Results:")
        print(f"  Sync Logger:  {'✅ PASS' if sync_ok else '❌ FAIL'}")
        print(f"  Async Logger: {'✅ PASS' if async_ok else '❌ FAIL'}")
        print(f"  Mixed Sessions: {'✅ PASS' if mixed_ok else '❌ FAIL'}")
        
        if sync_ok and async_ok and mixed_ok:
            print("\n✅ All tests passed! Flat directory structure is working correctly.")
            
            # Show final directory listing
            print("\nFinal directory contents:")
            response_dir = Path(".claude-mpm/responses")
            files = sorted(response_dir.glob("*.json"))
            
            # Group by session for clarity
            sessions = {}
            for f in files:
                session = f.name.split("-")[0]
                if session not in sessions:
                    sessions[session] = []
                sessions[session].append(f.name)
            
            for session, filenames in sorted(sessions.items()):
                print(f"\n  {session}:")
                for fname in filenames[:3]:  # Show first 3 per session
                    print(f"    {fname}")
                if len(filenames) > 3:
                    print(f"    ... and {len(filenames) - 3} more")
            
            return 0
        else:
            print("\n❌ Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())