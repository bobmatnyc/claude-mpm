#!/usr/bin/env python3
"""Detailed subprocess test with better error handling."""

import sys
import os
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_direct_claude():
    """Test calling Claude directly."""
    print("Testing direct Claude call...")
    
    try:
        # Simple direct test
        result = subprocess.run(
            ["claude", "--print", "Say hello"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
    except subprocess.TimeoutExpired:
        print("Timeout!")
    except FileNotFoundError:
        print("Claude not found in PATH")
    except Exception as e:
        print(f"Error: {e}")

def test_with_orchestrator():
    """Test with subprocess orchestrator."""
    from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator
    
    print("\n\nTesting with SubprocessOrchestrator...")
    
    # Clean logs
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
    
    # Create orchestrator with detailed logging
    orchestrator = SubprocessOrchestrator(log_level="DEBUG")
    
    # Check if we can detect delegations in a sample response
    sample_response = """I'll help you create a hello world function. Let me delegate this task:

**Engineer**: Create a hello world function in Python that prints "Hello, World!"

This will create a simple function for you."""
    
    delegations = orchestrator.detect_delegations(sample_response)
    print(f"\nDetected {len(delegations)} delegations from sample:")
    for d in delegations:
        print(f"  - {d['agent']}: {d['task']}")
    
    # Now test actual run
    print("\nTesting actual orchestration run...")
    test_input = "Create a simple Python function that returns the string 'test'"
    
    try:
        orchestrator.run_non_interactive(test_input)
    except Exception as e:
        print(f"Orchestration error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_claude()
    test_with_orchestrator()