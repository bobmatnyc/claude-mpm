#!/usr/bin/env python3
"""Test Claude directly to debug interaction."""

import subprocess
import threading
import sys
import time

def test_claude_modes():
    """Test different Claude invocation modes."""
    
    print("=== Test 1: Claude with no arguments ===")
    try:
        # Just run claude with no args
        process = subprocess.Popen(
            ["claude"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment
        time.sleep(1)
        
        # Send a test message
        process.stdin.write("Say hello\n")
        process.stdin.flush()
        
        # Read some output
        for _ in range(10):
            line = process.stdout.readline()
            if line:
                print(f"OUT: {line.rstrip()}")
        
        process.terminate()
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test 2: Claude with model flag ===")
    try:
        process = subprocess.Popen(
            ["claude", "--model", "opus"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Read initial output
        def reader():
            while True:
                line = process.stdout.readline()
                if line:
                    print(f"OUT: {line.rstrip()}")
                else:
                    break
        
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        
        time.sleep(1)
        
        # Send test
        print("\nSending: 'Say hello'")
        process.stdin.write("Say hello\n")
        process.stdin.flush()
        
        time.sleep(3)
        
        process.terminate()
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test 3: Check if Claude expects TTY ===")
    import os
    if os.isatty(sys.stdin.fileno()):
        print("Script running in TTY")
    else:
        print("Script NOT running in TTY")
    
    # Check what Claude sees
    result = subprocess.run(
        ["claude", "--help"],
        capture_output=True,
        text=True
    )
    
    if "interactive" in result.stdout.lower():
        print("\nClaude mentions 'interactive' in help:")
        for line in result.stdout.split('\n'):
            if 'interactive' in line.lower():
                print(f"  {line}")

if __name__ == "__main__":
    test_claude_modes()