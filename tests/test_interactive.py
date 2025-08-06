#!/usr/bin/env python3
"""Test interactive mode functionality."""

import subprocess
import sys
import time
import threading
from pathlib import Path

def test_claude_direct():
    """Test Claude directly to verify it works."""
    print("=== Testing Claude directly ===")
    
    cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions", "chat"]
    print(f"Command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Read initial output
        def read_output():
            while True:
                line = process.stdout.readline()
                if line:
                    print(f"CLAUDE: {line.rstrip()}")
                    
        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()
        
        # Send a test message
        test_msg = "Please respond with exactly: Hello from direct test"
        print(f"\nSending: {test_msg}")
        process.stdin.write(test_msg + "\n")
        process.stdin.flush()
        
        # Wait a bit for response
        time.sleep(3)
        
        # Terminate
        process.terminate()
        
    except Exception as e:
        print(f"Error: {e}")

def test_claude_mpm():
    """Test claude-mpm subprocess handling."""
    print("\n\n=== Testing claude-mpm subprocess ===")
    
    test_dir = Path.home() / "Tests" / "claude-mpm-test"
    cmd = [
        sys.executable,
        str(Path(__file__).parent.parent / "run_mpm.py"),
        "--logging", "DEBUG"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print("Check logs at: ~/.claude-mpm/logs/latest.log")
    
    # Just show the command - user needs to run interactively
    print("\nTo test interactively, run in your terminal:")
    print(f"cd {test_dir}")
    print("./claude-mpm --logging DEBUG")

if __name__ == "__main__":
    test_claude_direct()
    test_claude_mpm()