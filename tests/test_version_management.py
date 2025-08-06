#!/usr/bin/env python3
"""Test script to verify single source version management is working correctly."""

import sys
import json
from pathlib import Path

def test_version_consistency():
    """Test that all version sources report the same version."""
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Read VERSION file
    version_file = project_root / "VERSION"
    if not version_file.exists():
        print("❌ VERSION file not found!")
        return False
    
    version_from_file = version_file.read_text().strip()
    print(f"✓ VERSION file: {version_from_file}")
    
    # Check package version
    sys.path.insert(0, str(project_root / "src"))
    try:
        from claude_mpm import __version__
        print(f"✓ Package version: {__version__}")
        if __version__ != version_from_file:
            print(f"❌ Package version mismatch: {__version__} != {version_from_file}")
            return False
    except ImportError as e:
        print(f"❌ Failed to import package: {e}")
        return False
    
    # Check CLI version
    try:
        from claude_mpm.cli import __version__ as cli_version
        print(f"✓ CLI version: {cli_version}")
        if cli_version != version_from_file:
            print(f"❌ CLI version mismatch: {cli_version} != {version_from_file}")
            return False
    except ImportError as e:
        print(f"❌ Failed to import CLI: {e}")
        return False
    
    # Check package.json version
    package_json = project_root / "package.json"
    if package_json.exists():
        with open(package_json) as f:
            package_data = json.load(f)
            npm_version = package_data.get("version", "unknown")
            print(f"✓ package.json version: {npm_version}")
            if npm_version != version_from_file:
                print(f"❌ package.json version mismatch: {npm_version} != {version_from_file}")
                return False
    else:
        print("⚠️  package.json not found (optional)")
    
    # Check that _version.py doesn't exist
    version_py = project_root / "src" / "claude_mpm" / "_version.py"
    if version_py.exists():
        print("❌ _version.py still exists - should be removed!")
        return False
    else:
        print("✓ _version.py correctly removed")
    
    print("\n✅ All version sources are consistent!")
    print(f"   Single source of truth: VERSION file = {version_from_file}")
    return True

if __name__ == "__main__":
    success = test_version_consistency()
    sys.exit(0 if success else 1)