#!/usr/bin/env python3
"""
Check version consistency across all version files in the project.

This script ensures that all version references are consistent:
- VERSION file (root)
- src/claude_mpm/VERSION
- pyproject.toml
- package.json
- BUILD_NUMBER file

Exit codes:
  0: All versions are consistent
  1: Version mismatch detected
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Optional


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def read_version_file(path: Path) -> Optional[str]:
    """Read version from a plain text file."""
    if path.exists():
        return path.read_text().strip()
    return None


def read_pyproject_version(path: Path) -> Optional[str]:
    """Read version from pyproject.toml."""
    if not path.exists():
        return None

    content = path.read_text()

    # Try to find version in [project] section
    match = re.search(
        r'^\[project\].*?^version\s*=\s*"([^"]+)"', content, re.MULTILINE | re.DOTALL
    )
    if match:
        return match.group(1)

    # Try to find version in [tool.commitizen] section
    match = re.search(
        r'\[tool\.commitizen\].*?version\s*=\s*"([^"]+)"', content, re.DOTALL
    )
    if match:
        return match.group(1)

    return None


def read_package_json_version(path: Path) -> Optional[str]:
    """Read version from package.json."""
    if not path.exists():
        return None

    try:
        with path.open() as f:
            data = json.load(f)
            return data.get("version")
    except (json.JSONDecodeError, KeyError):
        return None


def check_version_consistency() -> bool:
    """Check if all version files have consistent versions."""
    project_root = get_project_root()

    versions: Dict[str, Optional[str]] = {}

    # Read all version sources
    versions["VERSION"] = read_version_file(project_root / "VERSION")
    versions["src/claude_mpm/VERSION"] = read_version_file(
        project_root / "src" / "claude_mpm" / "VERSION"
    )
    versions["pyproject.toml"] = read_pyproject_version(project_root / "pyproject.toml")
    versions["package.json"] = read_package_json_version(project_root / "package.json")

    # Check BUILD_NUMBER file exists
    build_number_file = project_root / "BUILD_NUMBER"
    if build_number_file.exists():
        build_number = build_number_file.read_text().strip()
        print(f"✓ BUILD_NUMBER: {build_number}")
    else:
        print("⚠ BUILD_NUMBER file not found")

    # Filter out None values and report missing files
    found_versions = {}
    for source, version in versions.items():
        if version is not None:
            found_versions[source] = version
            print(f"✓ {source}: {version}")
        else:
            print(f"⚠ {source}: not found or unable to parse")

    if not found_versions:
        print("\n❌ No version files found!")
        return False

    # Check if all versions match
    unique_versions = set(found_versions.values())

    if len(unique_versions) == 1:
        version = unique_versions.pop()
        print(f"\n✅ All version files are consistent: {version}")
        return True
    print("\n❌ Version mismatch detected!")
    print("Found versions:")
    for source, version in found_versions.items():
        print(f"  - {source}: {version}")

    # Suggest fix
    if "VERSION" in found_versions:
        print("\n💡 To fix, run: make sync-versions")
        print(f"   This will sync all files to VERSION: {found_versions['VERSION']}")

    return False


def main():
    """Main entry point."""
    print("Checking version consistency...")
    print("-" * 40)

    is_consistent = check_version_consistency()

    sys.exit(0 if is_consistent else 1)


if __name__ == "__main__":
    main()
