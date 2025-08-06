#!/usr/bin/env python3
"""Test logging levels functionality."""

import subprocess
import sys
import os
from pathlib import Path

def test_logging_level(level, message):
    """Test claude-mpm with different logging levels."""
    print(f"\n=== Testing with --logging {level} ===")
    
    test_dir = Path.home() / "Tests" / "claude-mpm-test"
    os.chdir(test_dir)
    
    cmd = [
        sys.executable,
        str(Path(__file__).parent.parent / "run_mpm.py"),
        "--logging", level,
        "run", "--non-interactive",
        "-i", message
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    # Run with short timeout
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"Exit code: {process.returncode}")
        if process.stdout:
            print("STDOUT (first 500 chars):")
            print(process.stdout[:500])
        if process.stderr:
            print("STDERR (first 500 chars):")
            print(process.stderr[:500])
            
    except subprocess.TimeoutExpired:
        print("Command timed out (expected for Claude interaction)")
    
    # Check what was created
    if level == "DEBUG":
        session_dir = Path.home() / ".claude-mpm" / "session"
        if session_dir.exists():
            print(f"\nSession directory contents:")
            for f in sorted(session_dir.glob("*"))[-5:]:
                print(f"  {f.name} ({f.stat().st_size} bytes)")
    
    if level in ["INFO", "DEBUG"]:
        log_dir = Path.home() / ".claude-mpm" / "logs"
        if log_dir.exists():
            print(f"\nLog directory contents:")
            for f in sorted(log_dir.glob("*.log"))[-3:]:
                print(f"  {f.name} ({f.stat().st_size} bytes)")

def main():
    """Run logging tests."""
    print("=== Claude MPM Logging Tests ===")
    
    # Test each logging level
    test_logging_level("OFF", "Test with logging OFF")
    test_logging_level("INFO", "Test with logging INFO") 
    test_logging_level("DEBUG", "Test with logging DEBUG")
    
    print("\n=== Tests complete ===")

if __name__ == "__main__":
    main()