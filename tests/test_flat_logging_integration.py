#!/usr/bin/env python3
"""Test flat directory structure with actual session logging integration."""

import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set session ID for testing
os.environ['CLAUDE_SESSION_ID'] = 'flat_test_session'

from claude_mpm.utils.session_logging import (
    log_agent_response,
    get_current_session_id,
    get_session_directory,
    is_session_logging_enabled
)


def main():
    """Test flat logging with session utilities."""
    print("Testing Flat Directory Structure with Session Integration")
    print("=" * 60)
    
    # Check if logging is enabled
    if not is_session_logging_enabled():
        print("⚠️  Session logging is not enabled")
        return
    
    # Get session info
    session_id = get_current_session_id()
    session_dir = get_session_directory()
    
    print(f"Session ID: {session_id}")
    print(f"Session Directory: {session_dir}")
    print()
    
    # Log responses from different agents
    agents = ["pm", "engineer", "qa", "researcher"]
    
    for i, agent in enumerate(agents):
        result = log_agent_response(
            agent_name=agent,
            request=f"Test request {i+1}: Please help with task X",
            response=f"This is a test response from {agent} agent. The response contains detailed information about how to complete the task.",
            metadata={
                "test": True,
                "index": i,
                "model": "test-model",
                "timestamp": time.time()
            }
        )
        
        if result:
            print(f"✓ Logged response for {agent}: {result.name}")
        else:
            print(f"✗ Failed to log response for {agent}")
        
        # Small delay to ensure different timestamps
        time.sleep(0.01)
    
    # List all files in the session directory
    print(f"\n Files in {session_dir}:")
    if session_dir and session_dir.exists():
        # Should be flat - all files directly in the directory
        json_files = sorted(session_dir.glob("*.json"))
        
        # Group by session ID
        our_files = [f for f in json_files if f.name.startswith(session_id)]
        other_files = [f for f in json_files if not f.name.startswith(session_id)]
        
        if our_files:
            print(f"\n  Our session ({session_id}):")
            for f in our_files:
                print(f"    {f.name}")
        
        if other_files:
            print(f"\n  Other sessions:")
            for f in other_files[:5]:  # Show first 5
                print(f"    {f.name}")
            if len(other_files) > 5:
                print(f"    ... and {len(other_files) - 5} more")
        
        # Verify flat structure
        subdirs = [d for d in session_dir.iterdir() if d.is_dir()]
        if subdirs:
            print(f"\n⚠️  Found subdirectories (should be flat):")
            for d in subdirs[:5]:
                print(f"    {d.name}")
        else:
            print(f"\n✅ Confirmed flat directory structure (no subdirectories)")
    else:
        print("  Directory does not exist")
    
    print("\n" + "=" * 60)
    print("Test completed")


if __name__ == "__main__":
    main()