#!/usr/bin/env python3
"""Test script to measure hook handler performance improvements.

This script tests the hook handler with a mock event to verify that the
performance bottlenecks have been fixed.
"""

import json
import subprocess
import time
import sys
from pathlib import Path

def test_hook_performance():
    """Test hook handler performance with a mock event."""
    # Path to hook handler
    hook_handler_path = Path(__file__).parent.parent / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
    
    # Mock event data
    mock_event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Test prompt for performance measurement",
        "session_id": "test-session",
        "cwd": "/tmp"
    }
    
    # Convert to JSON
    event_json = json.dumps(mock_event)
    
    print("Testing hook handler performance...")
    print(f"Event size: {len(event_json)} bytes")
    
    # Measure execution time
    start_time = time.time()
    
    try:
        # Run hook handler with mock data
        result = subprocess.run(
            [sys.executable, str(hook_handler_path)],
            input=event_json,
            text=True,
            capture_output=True,
            timeout=5  # Should complete much faster than this
        )
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        print(f"Execution time: {duration_ms:.2f}ms")
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout.strip()}")
        
        if result.stderr:
            print(f"Stderr: {result.stderr.strip()}")
        
        # Check if performance is acceptable (Python startup overhead + execution)
        if duration_ms < 200:
            print("✅ PERFORMANCE TEST PASSED - No blocking delays detected")
            return True
        else:
            print("❌ PERFORMANCE TEST FAILED - Execution too slow")
            print(f"   Expected: < 200ms, Actual: {duration_ms:.2f}ms")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ PERFORMANCE TEST FAILED - Hook handler timed out")
        return False
    except Exception as e:
        print(f"❌ PERFORMANCE TEST FAILED - Error: {e}")
        return False

if __name__ == "__main__":
    success = test_hook_performance()
    sys.exit(0 if success else 1)