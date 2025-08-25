#!/usr/bin/env python3
"""
Test individual packages to see which ones require cryptography.

WHY: Need to accurately identify which packages have cryptography
as a transitive dependency to properly separate them.
"""

import subprocess
import sys
from pathlib import Path


def test_package_crypto_dep(package_name):
    """Test if a package requires cryptography as a dependency."""
    with tmp_path as tmpdir:
        venv_path = Path(tmpdir) / "test_venv"

        # Create venv
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)], capture_output=True, check=False
        )

        # Get pip path
        if sys.platform == "win32":
            pip_path = venv_path / "Scripts" / "pip"
            python_path = venv_path / "Scripts" / "python"
        else:
            pip_path = venv_path / "bin" / "pip"
            python_path = venv_path / "bin" / "python"

        # Upgrade pip
        subprocess.run(
            [str(pip_path), "install", "--upgrade", "pip"], capture_output=True, check=False
        )

        # Try to install the package
        result = subprocess.run(
            [str(pip_path), "install", "--dry-run", package_name],
            capture_output=True,
            text=True, check=False,
        )

        # Check if cryptography is in the output
        has_crypto = "cryptography" in result.stdout.lower()

        return has_crypto


# Test suspicious packages
suspicious_packages = [
    "ydata-profiling",
    "great-expectations",
    "safety",
    "pip-audit",
    "detect-secrets",
    "sqlalchemy",
]

print("Testing packages for cryptography dependency...")
print("=" * 60)

for pkg in suspicious_packages:
    print(f"Testing {pkg}...", end=" ")
    try:
        has_crypto = test_package_crypto_dep(pkg)
        if has_crypto:
            print("⚠️  Requires cryptography")
        else:
            print("✅ No cryptography needed")
    except Exception as e:
        print(f"❌ Error: {e}")

print("=" * 60)
