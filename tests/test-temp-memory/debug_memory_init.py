#!/usr/bin/env python3
"""Debug script to understand what's happening with memory init"""

import os
import subprocess
import tempfile
from pathlib import Path

# Create a temporary test directory
test_dir = tempfile.mkdtemp(prefix="debug_memory_")
print(f"Test directory: {test_dir}")

# Change to test directory
original_cwd = os.getcwd()
os.chdir(test_dir)
print(f"Changed to: {os.getcwd()}")

# Get the mpm command path
project_root = Path(
    __file__
).parent.parent  # Go up one level to the actual project root
mpm_cmd = str(project_root / "claude-mpm")
print(f"MPM command: {mpm_cmd}")

# Try to run memory init with verbose output
cmd = [mpm_cmd, "memory", "init"]
print(f"Running: {' '.join(cmd)}")

try:
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=60, check=False
    )
    print(f"Return code: {result.returncode}")
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")

    # Check what directories were created
    print(f"\nDirectories in test dir {test_dir}:")
    for item in os.listdir(test_dir):
        item_path = os.path.join(test_dir, item)
        if os.path.isdir(item_path):
            print(f"  DIR: {item}")
            for subitem in os.listdir(item_path):
                subitem_path = os.path.join(item_path, subitem)
                if os.path.isdir(subitem_path):
                    print(f"    SUBDIR: {subitem}")
                else:
                    print(f"    FILE: {subitem}")

    # Check if memory directory was created in project root instead
    project_memory_dir = project_root / ".claude-mpm" / "memories"
    print(f"\nMemory dir in project root exists: {project_memory_dir.exists()}")
    if project_memory_dir.exists():
        print(f"Project memory dir: {project_memory_dir}")

    # Check if memory directory was created in test directory
    test_memory_dir = Path(test_dir) / ".claude-mpm" / "memories"
    print(f"Memory dir in test dir exists: {test_memory_dir.exists()}")
    if test_memory_dir.exists():
        print(f"Test memory dir: {test_memory_dir}")

except Exception as e:
    print(f"Error: {e}")

finally:
    # Cleanup
    os.chdir(original_cwd)
    import shutil

    shutil.rmtree(test_dir, ignore_errors=True)
