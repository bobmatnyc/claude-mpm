#!/usr/bin/env python3
"""Simple working directory test"""

import subprocess
import tempfile
from pathlib import Path


# Create test directory
with tempfile.TemporaryDirectory() as tmpdir:
    test_dir = Path(tmpdir) / "myproject"
    test_dir.mkdir()
    
    # Create a test file
    (test_dir / "hello.txt").write_text("Hello from my project!")
    
    # Run claude-mpm from that directory
    claude_mpm = Path(__file__).parent.parent / "claude-mpm"
    
    print(f"Running from: {test_dir}")
    print(f"Test file exists: {(test_dir / 'hello.txt').exists()}")
    
    # Simple pwd test
    result = subprocess.run(
        [str(claude_mpm), "run", "-i", "pwd", "--non-interactive"],
        cwd=str(test_dir),
        capture_output=True,
        text=True
    )
    
    print("\n=== PWD Test ===")
    if str(test_dir) in result.stdout:
        print("✓ Working directory is correct!")
    else:
        print("✗ Working directory is wrong")
    
    # Show filtered output
    for line in result.stdout.split('\n'):
        if not line.startswith('[INFO]') and not line.startswith('INFO:') and line.strip():
            if 'directory' in line.lower() or str(test_dir) in line:
                print(f"Output: {line.strip()}")