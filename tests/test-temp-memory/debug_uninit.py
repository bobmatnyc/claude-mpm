#!/usr/bin/env python3
"""Debug script to test uninitialized memory behavior"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Create a temporary test directory
test_dir = tempfile.mkdtemp(prefix="debug_uninit_")
print(f"Test directory: {test_dir}")

# Change to test directory
original_cwd = os.getcwd()
os.chdir(test_dir)

try:
    # Get the mpm command path
    project_root = Path(__file__).parent.parent
    mpm_cmd = str(project_root / "claude-mpm")
    
    # Run memory status without initialization
    print("=== Running memory status without init ===")
    status_cmd = [mpm_cmd, "memory", "status"]
    status_result = subprocess.run(status_cmd, capture_output=True, text=True, timeout=60)
    print(f"Status return code: {status_result.returncode}")
    print(f"Status STDOUT: {status_result.stdout}")
    if status_result.stderr:
        print(f"Status STDERR: {status_result.stderr}")
    
    # Run memory add without initialization
    print("\n=== Running memory add without init ===")
    add_cmd = [mpm_cmd, "memory", "add", "qa", "pattern", "test"]
    add_result = subprocess.run(add_cmd, capture_output=True, text=True, timeout=60)
    print(f"Add return code: {add_result.returncode}")
    print(f"Add STDOUT: {add_result.stdout}")
    if add_result.stderr:
        print(f"Add STDERR: {add_result.stderr}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    os.chdir(original_cwd)
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)