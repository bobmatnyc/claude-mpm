#!/usr/bin/env python3
"""Debug file access issue"""

import os
import subprocess
import tempfile
from pathlib import Path


def debug_file_access():
    """Debug why file access might be failing."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_project"
        test_dir.mkdir()
        
        # Create test file
        readme = test_dir / "README.md"
        readme.write_text("# Test Project\nThis is a test.")
        
        claude_mpm = Path(__file__).parent.parent / "claude-mpm"
        
        print(f"Test directory: {test_dir}")
        print(f"README exists: {readme.exists()}")
        print(f"README content: {readme.read_text()}")
        
        # Try different commands
        test_commands = [
            "cat README.md",
            "ls -la README.md",
            "head -n 1 README.md",
            "echo 'File content:' && cat README.md"
        ]
        
        for cmd_str in test_commands:
            print(f"\nTesting: {cmd_str}")
            print("-" * 40)
            
            cmd = [
                str(claude_mpm),
                "run",
                "-i",
                cmd_str,
                "--non-interactive"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(test_dir),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Show full output
                print("STDOUT:")
                print(result.stdout)
                print("\nExtracted content:")
                # Extract non-INFO lines
                for line in result.stdout.split('\n'):
                    if not line.startswith('[INFO]') and not line.startswith('INFO:') and line.strip():
                        print(f"  > {line}")
            else:
                print(f"Failed with code {result.returncode}")
                print(f"STDERR: {result.stderr}")


if __name__ == "__main__":
    debug_file_access()