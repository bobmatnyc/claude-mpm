#!/usr/bin/env python3
"""Debug script to test memory add command"""

import os
import subprocess
import tempfile
from pathlib import Path

# Create a temporary test directory
test_dir = tempfile.mkdtemp(prefix="debug_memory_add_")
print(f"Test directory: {test_dir}")

# Change to test directory
original_cwd = os.getcwd()
os.chdir(test_dir)
print(f"Current working directory: {os.getcwd()}")

try:
    # Get the mpm command path
    project_root = Path(__file__).parent.parent
    mpm_cmd = str(project_root / "claude-mpm")
    print(f"MPM command: {mpm_cmd}")

    # Run memory init first
    print("\n=== Running memory init ===")
    init_cmd = [mpm_cmd, "memory", "init"]
    init_result = subprocess.run(
        init_cmd, capture_output=True, text=True, timeout=60, check=False
    )
    print(f"Init return code: {init_result.returncode}")
    if init_result.stderr:
        print(f"Init STDERR: {init_result.stderr}")

    # Run memory add
    print("\n=== Running memory add ===")
    test_content = "This is a test memory entry"
    add_cmd = [mpm_cmd, "memory", "add", test_content]
    add_result = subprocess.run(
        add_cmd, capture_output=True, text=True, timeout=60, check=False
    )
    print(f"Add return code: {add_result.returncode}")
    print(f"Add STDOUT: {add_result.stdout}")
    if add_result.stderr:
        print(f"Add STDERR: {add_result.stderr}")

    # Run memory status to see what happened
    print("\n=== Running memory status ===")
    status_cmd = [mpm_cmd, "memory", "status"]
    status_result = subprocess.run(
        status_cmd, capture_output=True, text=True, timeout=60, check=False
    )
    print(f"Status return code: {status_result.returncode}")
    print(f"Status STDOUT: {status_result.stdout}")
    if status_result.stderr:
        print(f"Status STDERR: {status_result.stderr}")

    # Check directory contents
    print(f"\nContents of test directory {test_dir}:")
    for item in Path(test_dir).iterdir():
        print(f"  {item}")
        if item.is_dir():
            for subitem in item.iterdir():
                print(f"    {subitem}")
                if subitem.is_dir():
                    for subsubitem in subitem.iterdir():
                        print(f"      {subsubitem}")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()

finally:
    os.chdir(original_cwd)
    import shutil

    shutil.rmtree(test_dir, ignore_errors=True)
