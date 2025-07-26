#!/usr/bin/env python3
"""
Check version synchronization across all version files.
"""

import json
import sys
from pathlib import Path


def check_versions():
    """Check that all version files are in sync."""
    project_root = Path(__file__).parent.parent
    errors = []
    versions = {}
    
    # Check VERSION file
    version_file = project_root / "VERSION"
    if version_file.exists():
        version = version_file.read_text().strip()
        versions["VERSION file"] = version
        print(f"✓ VERSION file: {version}")
    else:
        errors.append("VERSION file not found")
    
    # Check package.json
    package_json_file = project_root / "package.json"
    if package_json_file.exists():
        with open(package_json_file) as f:
            package_data = json.load(f)
        version = package_data.get("version", "unknown")
        versions["package.json"] = version
        print(f"✓ package.json: {version}")
    else:
        errors.append("package.json not found")
    
    # Check if all versions match
    unique_versions = set(versions.values())
    if len(unique_versions) > 1:
        errors.append(f"Version mismatch detected: {versions}")
    elif len(unique_versions) == 1:
        print(f"\n✅ All versions are synchronized: {list(unique_versions)[0]}")
    
    # Report errors
    if errors:
        print("\n❌ Errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


if __name__ == "__main__":
    success = check_versions()
    sys.exit(0 if success else 1)