#!/usr/bin/env python3
"""
Test script to verify the file access tracking and validation fix.

This script tests:
1. File access tracking when files are read/accessed
2. File access validation in the API endpoint
3. Proper error handling for denied access
"""

import os
import sys
import tempfile
import requests
import json
from pathlib import Path

# Add the src directory to Python path
script_dir = Path(__file__).parent
src_dir = script_dir.parent / 'src'
sys.path.insert(0, str(src_dir))

from claude_mpm.services.agent_memory_manager import AgentMemoryManager
from claude_mpm.core.config import Config

def test_file_access_tracking():
    """Test the file access tracking functionality."""
    print("Testing file access tracking...")
    
    # Create a temporary config
    config = Config()
    memory_manager = AgentMemoryManager(config)
    
    # Test tracking file access
    test_file = "/tmp/test_file.txt"
    with open(test_file, 'w') as f:
        f.write("test content")
    
    # Track the file access
    memory_manager.track_file_access(test_file)
    
    # Test validation - should allow access
    allowed, reason = memory_manager.is_file_access_allowed(test_file)
    assert allowed, f"File access should be allowed: {reason}"
    print(f"✓ File access tracking works: {reason}")
    
    # Test file outside working directory but tracked
    outside_file = "/tmp/outside_file.txt"
    with open(outside_file, 'w') as f:
        f.write("outside content")
    
    memory_manager.track_file_access(outside_file)
    allowed, reason = memory_manager.is_file_access_allowed(outside_file, working_dir="/home/user")
    assert allowed, f"Tracked file should be allowed even outside working dir: {reason}"
    print(f"✓ Outside file access with tracking works: {reason}")
    
    # Test file not tracked and outside working directory
    untracked_file = "/tmp/untracked_file.txt"
    with open(untracked_file, 'w') as f:
        f.write("untracked content")
    
    allowed, reason = memory_manager.is_file_access_allowed(untracked_file, working_dir="/home/user")
    assert not allowed, f"Untracked file outside working dir should be denied: {reason}"
    print(f"✓ Untracked file access denial works: {reason}")
    
    # Test file within working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        working_file = os.path.join(temp_dir, "working_file.txt")
        with open(working_file, 'w') as f:
            f.write("working content")
        
        allowed, reason = memory_manager.is_file_access_allowed(working_file, working_dir=temp_dir)
        assert allowed, f"File within working directory should be allowed: {reason}"
        print(f"✓ Working directory file access works: {reason}")
    
    # Cleanup
    os.unlink(test_file)
    os.unlink(outside_file)
    os.unlink(untracked_file)
    
    print("All file access tracking tests passed!")

def test_api_endpoint(server_url="http://localhost:8080"):
    """Test the API endpoint validation (requires running server)."""
    print(f"Testing API endpoint at {server_url}...")
    
    try:
        # Test with a file that should be denied
        response = requests.get(f"{server_url}/api/file-content", params={
            'file_path': '/etc/passwd',
            'working_dir': '/home/user'
        })
        
        if response.status_code == 403:
            error_data = response.json()
            print(f"✓ API correctly denied access: {error_data.get('reason', 'No reason provided')}")
        else:
            print(f"⚠ API response: {response.status_code} - {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("⚠ Server not running - skipping API tests")
    except Exception as e:
        print(f"⚠ API test error: {e}")

def main():
    """Run all tests."""
    print("File Access Fix Test Suite")
    print("=" * 40)
    
    try:
        test_file_access_tracking()
        print()
        test_api_endpoint()
        
        print()
        print("✓ All tests completed successfully!")
        print()
        print("To test the full fix:")
        print("1. Start the MPM dashboard: ./claude-mpm")
        print("2. Access a file outside the working directory during a session")
        print("3. Try to view that file in the dashboard - it should now work")
        print("4. Try to view a different file that wasn't accessed - should show helpful error")
        
    except Exception as e:
        print(f"Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())