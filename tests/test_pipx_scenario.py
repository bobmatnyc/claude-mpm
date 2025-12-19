#!/usr/bin/env python3
"""
Test script to simulate and verify the pipx installation scenario.
This tests what happens when the pipx-installed claude-mpm is invoked
from within the development directory.
"""

import os
import subprocess
import sys
from pathlib import Path


def test_pipx_scenario():
    """Test the pipx installation scenario."""

    print("=" * 70)
    print("PIPX SCENARIO TEST")
    print("=" * 70)

    # Show current environment
    print("\n1. Current Environment:")
    print("-" * 40)
    print(f"Working directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")

    # Check if pipx claude-mpm exists
    pipx_python = Path("/Users/masa/.local/pipx/venvs/claude-mpm/bin/python")
    if not pipx_python.exists():
        print("⚠️  pipx installation not found")
        return

    print(f"pipx Python found: {pipx_python}")

    # Test 1: Run from development directory WITHOUT env var
    print("\n2. Test from dev directory WITHOUT CLAUDE_MPM_DEV_MODE:")
    print("-" * 40)

    test_script = """
import sys
sys.path.insert(0, 'src')  # Add src to path to use development code
from claude_mpm.core.unified_paths import get_path_manager, PathContext

# Clear cache
PathContext.detect_deployment_context.cache_clear()

context = PathContext.detect_deployment_context()
pm = get_path_manager()
pm.clear_cache()

print(f"Deployment context: {context.value}")
print(f"Framework root: {pm.framework_root}")
print(f"Is development paths: {'/Users/masa/Projects/claude-mpm' in str(pm.framework_root)}")
"""

    result = subprocess.run(
        [str(pipx_python), "-c", test_script],
        cwd="/Users/masa/Projects/claude-mpm",
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Error: {result.stderr}")

    # Test 2: Run from development directory WITH env var
    print("\n3. Test from dev directory WITH CLAUDE_MPM_DEV_MODE=1:")
    print("-" * 40)

    env = os.environ.copy()
    env["CLAUDE_MPM_DEV_MODE"] = "1"

    result = subprocess.run(
        [str(pipx_python), "-c", test_script],
        cwd="/Users/masa/Projects/claude-mpm",
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Error: {result.stderr}")

    # Test 3: Run from a different directory
    print("\n4. Test from /tmp directory (outside development):")
    print("-" * 40)

    test_script_outside = """
from claude_mpm.core.unified_paths import get_path_manager, PathContext

context = PathContext.detect_deployment_context()
pm = get_path_manager()

print(f"Deployment context: {context.value}")
print(f"Framework root: {pm.framework_root}")
print(f"Is pipx paths: {'pipx' in str(pm.framework_root)}")
"""

    result = subprocess.run(
        [str(pipx_python), "-c", test_script_outside],
        cwd="/tmp",
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Error: {result.stderr}")

    # Test 4: Check if uv run works for development
    print("\n5. Test uv run development mode:")
    print("-" * 40)

    # Check if uv is available
    uv_check = subprocess.run(
        ["which", "uv"], capture_output=True, text=True, check=False
    )
    if uv_check.returncode == 0:
        result = subprocess.run(
            ["uv", "run", "claude-mpm", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print(f"uv run version: {result.stdout.strip()}")
        else:
            print(f"Error: {result.stderr}")
    else:
        print(
            "uv not found - install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        )

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_pipx_scenario()
