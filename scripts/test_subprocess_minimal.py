#!/usr/bin/env python3
"""Minimal test of subprocess.Popen for Claude."""

import subprocess
import sys
import os

def test_subprocess():
    """Test basic subprocess control of Claude."""
    print("Testing subprocess.Popen with Claude...")
    
    # Simple test without PTY first
    try:
        # Test 1: Can we start Claude at all?
        print("\nTest 1: Starting Claude with subprocess.Popen (no PTY)...")
        process = subprocess.Popen(
            ['claude', '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate()
        print(f"Return code: {process.returncode}")
        print(f"Stdout: {stdout}")
        print(f"Stderr: {stderr}")
        
    except Exception as e:
        print(f"Failed to start Claude: {e}")
        return
        
    # Test 2: Interactive mode with pipes
    print("\nTest 2: Starting Claude interactively with pipes...")
    try:
        process = subprocess.Popen(
            ['claude'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0  # Unbuffered
        )
        
        print(f"Claude started with PID: {process.pid}")
        
        # Try to send a simple command
        process.stdin.write("Hello Claude\n")
        process.stdin.flush()
        
        # Give it a moment
        import time
        time.sleep(1)
        
        # Check if still running
        if process.poll() is None:
            print("Process is still running")
            # Terminate gracefully
            process.terminate()
            process.wait()
        else:
            print(f"Process exited with code: {process.returncode}")
            
    except Exception as e:
        print(f"Error in interactive test: {e}")


if __name__ == "__main__":
    test_subprocess()