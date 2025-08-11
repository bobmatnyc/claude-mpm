#!/usr/bin/env python3
"""Test script to verify flat directory structure for response logging."""

import os
import sys
import time
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.claude_session_logger import ClaudeSessionLogger
from claude_mpm.services.async_session_logger import AsyncSessionLogger, LogFormat


def test_sync_logger():
    """Test synchronous logger with flat structure."""
    print("\n=== Testing Synchronous Logger ===")
    
    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "responses"
        
        # Create logger
        logger = ClaudeSessionLogger(base_dir=base_dir, use_async=False)
        logger.set_session_id("test_session_001")
        
        # Log some responses with different agents
        agents = ["pm", "engineer", "qa", "researcher"]
        for i, agent in enumerate(agents):
            result = logger.log_response(
                request_summary=f"Test request {i+1} from {agent}",
                response_content=f"This is a test response from {agent} agent",
                metadata={"test": True, "index": i},
                agent=agent
            )
            print(f"  Logged response for {agent}: {result}")
            
            # Small delay to ensure different timestamps
            time.sleep(0.01)
        
        # Check the files created
        print("\n  Files created in flat structure:")
        files = sorted(base_dir.glob("*.json"))
        for f in files:
            print(f"    {f.name}")
            # Verify filename format: session_id-agent-timestamp.json
            parts = f.name.split("-")
            assert len(parts) >= 3, f"Filename {f.name} doesn't match expected format"
            assert parts[0] == "test_session_001", f"Session ID not in filename: {f.name}"
            assert parts[1] in agents, f"Agent name not recognized in filename: {f.name}"
        
        print(f"\n  ✓ Created {len(files)} files in flat structure")
        assert len(files) == len(agents), f"Expected {len(agents)} files, got {len(files)}"


def test_async_logger():
    """Test asynchronous logger with flat structure."""
    print("\n=== Testing Asynchronous Logger ===")
    
    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "async_responses"
        
        # Create async logger
        logger = AsyncSessionLogger(
            base_dir=base_dir,
            log_format=LogFormat.JSON,
            enable_async=True
        )
        logger.set_session_id("async_test_002")
        
        # Log some responses with different agents
        agents = ["pm", "engineer", "qa", "researcher", "architect"]
        for i, agent in enumerate(agents):
            success = logger.log_response(
                request_summary=f"Async test request {i+1} from {agent}",
                response_content=f"This is an async test response from {agent} agent with more content",
                metadata={"async": True, "index": i},
                agent=agent
            )
            print(f"  Queued response for {agent}: {success}")
            
            # Small delay to ensure different timestamps
            time.sleep(0.01)
        
        # Flush the queue to ensure all files are written
        print("  Flushing async queue...")
        logger.flush(timeout=5.0)
        
        # Check the files created
        print("\n  Files created in flat structure:")
        files = sorted(base_dir.glob("*.json"))
        for f in files:
            print(f"    {f.name}")
            # Verify filename format: session_id-agent-timestamp.json
            parts = f.name.split("-")
            assert len(parts) >= 3, f"Filename {f.name} doesn't match expected format"
            assert parts[0] == "async_test_002", f"Session ID not in filename: {f.name}"
            assert parts[1] in agents, f"Agent name not recognized in filename: {f.name}"
        
        print(f"\n  ✓ Created {len(files)} files in flat structure")
        assert len(files) == len(agents), f"Expected {len(agents)} files, got {len(files)}"
        
        # Show stats
        stats = logger.get_stats()
        print(f"  Logger stats: {stats}")
        
        # Cleanup
        logger.shutdown()


def test_mixed_session_ids():
    """Test that multiple session IDs work correctly in flat structure."""
    print("\n=== Testing Multiple Session IDs ===")
    
    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "mixed_responses"
        
        # Create multiple loggers with different sessions
        sessions = ["session_a", "session_b", "session_c"]
        
        for session_id in sessions:
            logger = ClaudeSessionLogger(base_dir=base_dir, use_async=False)
            logger.set_session_id(session_id)
            
            # Log a response for each session
            result = logger.log_response(
                request_summary=f"Request from {session_id}",
                response_content=f"Response for {session_id}",
                agent="test_agent"
            )
            print(f"  Logged for {session_id}: {result}")
            time.sleep(0.01)
        
        # Check all files are in the same flat directory
        print("\n  Files in flat directory:")
        files = sorted(base_dir.glob("*.json"))
        for f in files:
            print(f"    {f.name}")
            # Verify each file starts with a session ID
            session_prefix = f.name.split("-")[0]
            assert session_prefix in sessions, f"Unknown session ID in filename: {f.name}"
        
        print(f"\n  ✓ All {len(files)} files in flat structure with proper naming")
        assert len(files) == len(sessions), f"Expected {len(sessions)} files, got {len(files)}"


def main():
    """Run all tests."""
    print("Testing Flat Directory Structure for Response Logging")
    print("=" * 60)
    
    try:
        test_sync_logger()
        test_async_logger()
        test_mixed_session_ids()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! Flat directory structure working correctly.")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()