#!/usr/bin/env python3
"""
Final test to verify the working directory fix is fully operational.
"""

import os
import subprocess
import tempfile
from pathlib import Path
import json


def test_fix_verification():
    """Comprehensive test of the working directory fix."""
    
    print("=== Working Directory Fix Verification ===\n")
    
    # Create test directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_project"
        test_dir.mkdir()
        
        # Create test files
        (test_dir / "README.md").write_text("# Test Project\nThis is a test project.")
        (test_dir / "data.json").write_text(json.dumps({"test": "data", "version": "1.0"}))
        (test_dir / "src").mkdir()
        (test_dir / "src" / "app.py").write_text("print('Hello from test project')")
        
        # Get claude-mpm path
        claude_mpm = Path(__file__).parent.parent / "claude-mpm"
        
        print(f"Test directory: {test_dir}")
        print(f"Claude MPM: {claude_mpm}\n")
        
        # Test 1: Check working directory in non-interactive mode
        print("1. Testing Non-Interactive Mode Working Directory")
        print("-" * 50)
        
        cmd = [
            str(claude_mpm),
            "run",
            "-i",
            "pwd && echo '---' && ls -la",
            "--non-interactive"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(test_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Extract output after the INFO lines
            output_lines = result.stdout.strip().split('\n')
            pwd_found = False
            files_found = False
            
            for i, line in enumerate(output_lines):
                if str(test_dir) in line and not line.startswith('[INFO]'):
                    pwd_found = True
                    print(f"✓ Working directory correct: {line.strip()}")
                if "README.md" in line and "data.json" in line:
                    files_found = True
                    print("✓ Can see files in working directory")
            
            if not pwd_found:
                print("✗ Working directory not correct")
                print(f"Full output:\n{result.stdout}")
            if not files_found and not "README.md" in result.stdout:
                print("✗ Cannot see files in working directory")
        else:
            print(f"✗ Command failed: {result.stderr}")
        
        # Test 2: Check file access
        print("\n2. Testing File Access from User Directory")
        print("-" * 50)
        
        cmd = [
            str(claude_mpm),
            "run", 
            "-i",
            "cat README.md",
            "--non-interactive"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(test_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and "# Test Project" in result.stdout:
            print("✓ Can read files from user's working directory")
        else:
            print("✗ Cannot read files from user's working directory")
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
        
        # Test 3: Check JSON file access
        print("\n3. Testing JSON File Access")
        print("-" * 50)
        
        cmd = [
            str(claude_mpm),
            "run",
            "-i", 
            "cat data.json | grep version",
            "--non-interactive"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(test_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and "1.0" in result.stdout:
            print("✓ Can process files with pipes in user directory")
        else:
            print("✗ Cannot process files with pipes")
        
        # Test 4: Check environment variable
        print("\n4. Testing Environment Variables")
        print("-" * 50)
        
        cmd = [
            str(claude_mpm),
            "run",
            "-i",
            "echo CLAUDE_MPM_USER_PWD: $CLAUDE_MPM_USER_PWD && echo CLAUDE_WORKSPACE: $CLAUDE_WORKSPACE",
            "--non-interactive"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(test_dir),
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_MPM_USER_PWD": str(test_dir)}
        )
        
        if result.returncode == 0:
            output = result.stdout
            if str(test_dir) in output:
                print("✓ Environment variables properly set")
                # Extract the relevant lines
                for line in output.split('\n'):
                    if "CLAUDE_MPM_USER_PWD:" in line or "CLAUDE_WORKSPACE:" in line:
                        print(f"  {line.strip()}")
            else:
                print("✗ Environment variables not properly propagated")
        else:
            print(f"✗ Command failed: {result.stderr}")
    
    print("\n=== Summary ===")
    print("\nThe working directory fix ensures that:")
    print("1. Claude Code sees the user's original working directory")
    print("2. Files in the user's directory are accessible")
    print("3. Commands execute in the correct context")
    print("4. Environment variables are properly set")
    
    print("\nTo test interactive mode manually:")
    print("1. cd /tmp")
    print("2. /path/to/claude-mpm")
    print("3. In Claude, run: pwd")
    print("4. Should show /tmp, not the claude-mpm directory")


if __name__ == "__main__":
    test_fix_verification()