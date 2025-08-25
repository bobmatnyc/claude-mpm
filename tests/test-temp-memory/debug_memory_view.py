#!/usr/bin/env python3
"""Debug script to test memory view command"""

import os
import subprocess
import tempfile
from pathlib import Path

# Create a temporary test directory
test_dir = tempfile.mkdtemp(prefix="debug_memory_view_")
print(f"Test directory: {test_dir}")

# Change to test directory
original_cwd = os.getcwd()
os.chdir(test_dir)

try:
    # Get the mpm command path
    project_root = Path(__file__).parent.parent
    mpm_cmd = str(project_root / "claude-mpm")

    # Run memory init
    init_cmd = [mpm_cmd, "memory", "init"]
    subprocess.run(init_cmd, capture_output=True, text=True, timeout=60, check=False)

    # Run memory add
    add_cmd = [mpm_cmd, "memory", "add", "qa", "pattern", "This is a test memory entry"]
    subprocess.run(add_cmd, capture_output=True, text=True, timeout=60, check=False)

    # Run memory view
    print("=== Running memory view ===")
    view_cmd = [mpm_cmd, "memory", "view", "qa"]
    view_result = subprocess.run(view_cmd, capture_output=True, text=True, timeout=60, check=False)
    print(f"View return code: {view_result.returncode}")
    print(f"View STDOUT: {view_result.stdout}")
    if view_result.stderr:
        print(f"View STDERR: {view_result.stderr}")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()

finally:
    os.chdir(original_cwd)
    import shutil

    shutil.rmtree(test_dir, ignore_errors=True)
