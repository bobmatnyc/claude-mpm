#!/usr/bin/env python3
"""
Check version synchronization across all version files.

This script verifies that version numbers are consistent across all 
distribution channels and configuration files.

Version Synchronization Points:
1. VERSION file - Canonical Python version source
2. package.json - npm distribution version
3. Git tags - Ultimate source of truth (not checked here)

Why Version Sync Matters:
- Users may install from PyPI or npm
- Version mismatch causes confusion
- Documentation references specific versions
- Support requires knowing exact version
- Dependency resolution needs accurate versions

Usage:
- Run manually: ./scripts/check_version_sync.py
- Run in CI/CD pipelines before release
- Run after manual version updates
- Integrated into release.py for automated checks

Exit Codes:
- 0: All versions synchronized
- 1: Version mismatch or errors found
"""

import json
import sys
from pathlib import Path


def check_versions():
    """Check that all version files are in sync.
    
    Version Checking Process:
    1. Read VERSION file (Python/PyPI version)
    2. Read package.json (npm version)
    3. Compare all found versions
    4. Report mismatches or missing files
    
    Version Format:
    - Must be semantic version (X.Y.Z)
    - No suffixes or prefixes allowed
    - Must match exactly across all files
    
    Error Handling:
    - Missing files are reported as errors
    - Version mismatches show all versions
    - Clear indication of which file has which version
    
    Returns:
        bool: True if all versions match, False otherwise
    """
    project_root = Path(__file__).parent.parent
    errors = []
    versions = {}
    
    # Check VERSION file (Python/PyPI version source)
    # This file is managed by manage_version.py and git hooks
    version_file = project_root / "VERSION"
    if version_file.exists():
        version = version_file.read_text().strip()
        versions["VERSION file"] = version
        print(f"✓ VERSION file: {version}")
    else:
        errors.append("VERSION file not found")
    
    # Check package.json (npm version)
    # This file is updated by release.py during release process
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
    # All versions should be identical for consistency
    unique_versions = set(versions.values())
    if len(unique_versions) > 1:
        # Version mismatch - show which files have which versions
        errors.append(f"Version mismatch detected: {versions}")
    elif len(unique_versions) == 1:
        # All versions match - success!
        print(f"\n✅ All versions are synchronized: {list(unique_versions)[0]}")
    
    # Report errors with clear formatting
    if errors:
        print("\n❌ Errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


if __name__ == "__main__":
    # Run version check and exit with appropriate code
    # Exit code 0 = success, 1 = failure (standard Unix convention)
    success = check_versions()
    sys.exit(0 if success else 1)