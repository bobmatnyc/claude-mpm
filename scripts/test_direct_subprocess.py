#!/usr/bin/env python3
"""Test the subprocess launch method directly."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.core.claude_runner import ClaudeRunner

def test_subprocess():
    """Test subprocess launch method."""
    print("Testing ClaudeRunner with subprocess method...")
    
    runner = ClaudeRunner(
        enable_tickets=False,
        log_level="OFF",
        launch_method="subprocess"
    )
    
    # Test non-interactive mode
    print("\nTesting non-interactive mode:")
    success = runner.run_oneshot("What is 2+2?")
    print(f"Success: {success}")


if __name__ == "__main__":
    test_subprocess()