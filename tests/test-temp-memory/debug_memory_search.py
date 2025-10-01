#!/usr/bin/env python3
"""Debug script to test memory search command"""

import os
import subprocess
import tempfile
from pathlib import Path

# Create a temporary test directory
test_dir = tempfile.mkdtemp(prefix="debug_memory_search_")
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

    # Run memory init
    print("\n=== Running memory init ===")
    init_cmd = [mpm_cmd, "memory", "init"]
    init_result = subprocess.run(
        init_cmd, capture_output=True, text=True, timeout=60, check=False
    )
    print(f"Init return code: {init_result.returncode}")

    # Run memory add
    print("\n=== Running memory add ===")
    add_cmd = [mpm_cmd, "memory", "add", "qa", "pattern", "This is a test memory entry"]
    add_result = subprocess.run(
        add_cmd, capture_output=True, text=True, timeout=60, check=False
    )
    print(f"Add return code: {add_result.returncode}")
    print(f"Add STDOUT: {add_result.stdout}")
    if add_result.stderr:
        print(f"Add STDERR: {add_result.stderr}")

    # Run memory status to verify it was added
    print("\n=== Running memory status ===")
    status_cmd = [mpm_cmd, "memory", "status"]
    status_result = subprocess.run(
        status_cmd, capture_output=True, text=True, timeout=60, check=False
    )
    print(f"Status return code: {status_result.returncode}")
    print(f"Status STDOUT: {status_result.stdout}")

    # Run memory search
    print("\n=== Running memory search ===")
    search_cmd = [mpm_cmd, "memory", "search", "test"]
    search_result = subprocess.run(
        search_cmd, capture_output=True, text=True, timeout=60, check=False
    )
    print(f"Search return code: {search_result.returncode}")
    print(f"Search STDOUT: {search_result.stdout}")
    if search_result.stderr:
        print(f"Search STDERR: {search_result.stderr}")

    # Check memory files
    memory_dir = Path(test_dir) / ".claude-mpm" / "memories"
    print("\nMemory directory contents:")
    for file in memory_dir.iterdir():
        print(f"  {file}")
        if file.suffix == ".md":
            with file.open() as f:
                content = f.read()
                print(f"    Content preview: {content[:200]}...")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()

finally:
    os.chdir(original_cwd)
    import shutil

    shutil.rmtree(test_dir, ignore_errors=True)
