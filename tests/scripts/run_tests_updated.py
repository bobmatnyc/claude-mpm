#!/usr/bin/env python3
"""Run the test suite for claude-mpm with updated imports."""

import subprocess
import sys
from pathlib import Path


def main():
    """Run tests with coverage."""
    # Ensure we're in the right directory
    project_root = Path(__file__).parent

    # Set PYTHONPATH to include src directory
    env = subprocess.os.environ.copy()
    src_path = str(project_root / "src")
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{src_path}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = src_path

    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html",
    ]

    print("Running claude-mpm test suite...")
    print(f"PYTHONPATH: {env['PYTHONPATH']}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd, cwd=project_root, env=env, check=False)

    if result.returncode == 0:
        print("\n✅ All tests passed!")
        print("\nCoverage report available at: htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
