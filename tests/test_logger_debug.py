#!/usr/bin/env python3
"""Debug script to test AsyncSessionLogger issue."""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.async_session_logger import AsyncSessionLogger

def test_logger():
    """Test the AsyncSessionLogger with different parameter combinations."""
    
    try:
        logger = AsyncSessionLogger()
        print("✓ Logger created successfully")
        
        # Test 1: Original call pattern
        print("\nTest 1: Basic call with request_summary and response_content")
        success = logger.log_response(
            request_summary="Test request",
            response_content="Test response",
            metadata={"agent": "test_agent"}
        )
        print(f"Result: {success}")
        
        # Test 2: With explicit agent parameter
        print("\nTest 2: Call with explicit agent parameter")
        success = logger.log_response(
            request_summary="Test request 2",
            response_content="Test response 2",
            metadata={"test": "value"},
            agent="test_agent_2"
        )
        print(f"Result: {success}")
        
        # Test 3: Problematic call from test
        print("\nTest 3: Call matching test scenario")
        success = logger.log_response(
            request_summary="Deploy engineer agent for code development",
            response_content="Engineer agent deployed successfully with capabilities: [coding, debugging, testing]",
            metadata={"agent": "engineer", "model": "claude-3", "timestamp": "2025-01-10T12:00:00Z"}
        )
        print(f"Result: {success}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_logger()