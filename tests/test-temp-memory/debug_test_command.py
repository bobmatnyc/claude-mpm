#!/usr/bin/env python3
"""Debug script to see what's happening with the test command"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Create a temporary test directory
test_dir = tempfile.mkdtemp(prefix="debug_test_cmd_")
print(f"Test directory: {test_dir}")

# Change to test directory
original_cwd = os.getcwd()
os.chdir(test_dir)
print(f"Current working directory: {os.getcwd()}")

try:
    # Get the mpm command path like the test does
    project_root = Path(__file__).parent.parent  # Go up to claude-mpm directory
    mpm_cmd = str(project_root / "claude-mpm")
    print(f"MPM command: {mpm_cmd}")
    print(f"Command exists: {os.path.exists(mpm_cmd)}")
    
    # Run memory init
    cmd = [mpm_cmd, "memory", "init"]
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print(f"Return code: {result.returncode}")
    print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")
    
    # Check what was created
    print(f"\nContents of test directory {test_dir}:")
    for item in Path(test_dir).iterdir():
        print(f"  {item}")
        if item.is_dir():
            for subitem in item.iterdir():
                print(f"    {subitem}")
                if subitem.is_dir():
                    for subsubitem in subitem.iterdir():
                        print(f"      {subsubitem}")
    
    # Check expected memory directory
    expected_memory_dir = Path(test_dir) / ".claude-mpm" / "memories"
    print(f"\nExpected memory dir: {expected_memory_dir}")
    print(f"Expected memory dir exists: {expected_memory_dir.exists()}")
    
    # Check project memory directory
    project_memory_dir = project_root / ".claude-mpm" / "memories"
    print(f"Project memory dir: {project_memory_dir}")
    print(f"Project memory dir exists: {project_memory_dir.exists()}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    os.chdir(original_cwd)
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)