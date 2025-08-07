#!/usr/bin/env python3
"""Run the test suite for claude-mpm."""

import sys
import subprocess
from pathlib import Path

def main():
    """Run tests with coverage."""
    # Ensure we're in the right directory
    project_root = Path(__file__).parent
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--cov=claude_mpm",
        "--cov-report=term-missing",
        "--cov-report=html",
    ]
    
    print("Running claude-mpm test suite...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, cwd=project_root)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        print("\nCoverage report available at: htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())