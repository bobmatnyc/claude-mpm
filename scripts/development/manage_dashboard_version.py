#!/usr/bin/env python3
"""
Dashboard Version Management Script

WHY: Manages version and build numbers for the Claude MPM Dashboard UI.
Provides functionality to increment versions, build numbers, and format
display versions consistently.

DESIGN DECISION: Mirrors the main project's version management approach
with separate VERSION and BUILD_NUMBER files for clean tracking.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Tuple, Optional

# Dashboard paths
DASHBOARD_DIR = Path(__file__).parent.parent / "src" / "claude_mpm" / "dashboard"
VERSION_FILE = DASHBOARD_DIR / "VERSION"
BUILD_FILE = DASHBOARD_DIR / "BUILD_NUMBER"
VERSION_JSON = DASHBOARD_DIR / "version.json"


def read_version() -> str:
    """Read the current semantic version."""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "1.0.0"


def read_build_number() -> int:
    """Read the current build number."""
    if BUILD_FILE.exists():
        try:
            return int(BUILD_FILE.read_text().strip())
        except ValueError:
            return 1
    return 1


def write_version(version: str) -> None:
    """Write the semantic version."""
    VERSION_FILE.write_text(version + "\n")


def write_build_number(build: int) -> None:
    """Write the build number."""
    BUILD_FILE.write_text(str(build) + "\n")


def write_json_version() -> None:
    """Write combined version info to JSON for JavaScript consumption."""
    version = read_version()
    build = read_build_number()
    
    version_data = {
        "version": version,
        "build": build,
        "formatted_build": f"{build:04d}",
        "full_version": f"v{version}-{build:04d}",
        "development": f"{version}+build.{build}",
        "ui": f"v{version}-build.{build}",
        "clean": version
    }
    
    VERSION_JSON.write_text(json.dumps(version_data, indent=2) + "\n")
    return version_data


def increment_version(component: str = "patch") -> Tuple[str, str]:
    """
    Increment the semantic version.
    
    Args:
        component: Which component to increment (major, minor, patch)
    
    Returns:
        Tuple of (old_version, new_version)
    """
    version = read_version()
    parts = version.split(".")
    
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")
    
    major, minor, patch = map(int, parts)
    
    if component == "major":
        major += 1
        minor = 0
        patch = 0
    elif component == "minor":
        minor += 1
        patch = 0
    elif component == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid component: {component}")
    
    new_version = f"{major}.{minor}.{patch}"
    write_version(new_version)
    
    return version, new_version


def increment_build() -> Tuple[int, int]:
    """
    Increment the build number.
    
    Returns:
        Tuple of (old_build, new_build)
    """
    build = read_build_number()
    new_build = build + 1
    write_build_number(new_build)
    return build, new_build


def display_version(format_type: str = "all") -> None:
    """Display the current version in requested format."""
    version = read_version()
    build = read_build_number()
    
    formats = {
        "version": version,
        "build": str(build),
        "development": f"{version}+build.{build}",
        "ui": f"v{version}-build.{build}",
        "clean": version,
        "full": f"v{version}-{build:04d}"
    }
    
    if format_type == "all":
        print(f"Dashboard Version: {version}")
        print(f"Build Number: {build}")
        print(f"Development: {formats['development']}")
        print(f"UI Display: {formats['ui']}")
        print(f"Full Format: {formats['full']}")
    else:
        print(formats.get(format_type, formats['ui']))


def main():
    """Main entry point for dashboard version management."""
    parser = argparse.ArgumentParser(
        description="Manage Claude MPM Dashboard versions"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Show version
    show_parser = subparsers.add_parser("show", help="Show current version")
    show_parser.add_argument(
        "--format",
        choices=["version", "build", "development", "ui", "clean", "full", "all"],
        default="all",
        help="Version format to display"
    )
    
    # Increment version
    inc_ver_parser = subparsers.add_parser("increment-version", help="Increment semantic version")
    inc_ver_parser.add_argument(
        "component",
        choices=["major", "minor", "patch"],
        help="Version component to increment"
    )
    
    # Increment build
    subparsers.add_parser("increment-build", help="Increment build number")
    
    # Update JSON
    subparsers.add_parser("update-json", help="Update version.json file")
    
    # Set version
    set_parser = subparsers.add_parser("set", help="Set version directly")
    set_parser.add_argument("version", help="New version (e.g., 1.2.3)")
    set_parser.add_argument("--build", type=int, help="New build number")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == "show":
            display_version(args.format)
            
        elif args.command == "increment-version":
            old_ver, new_ver = increment_version(args.component)
            print(f"Version updated: {old_ver} → {new_ver}")
            version_data = write_json_version()
            print(f"Full version: {version_data['full_version']}")
            
        elif args.command == "increment-build":
            old_build, new_build = increment_build()
            print(f"Build updated: {old_build} → {new_build}")
            version_data = write_json_version()
            print(f"Full version: {version_data['full_version']}")
            
        elif args.command == "update-json":
            version_data = write_json_version()
            print(f"Updated version.json: {version_data['full_version']}")
            
        elif args.command == "set":
            old_ver = read_version()
            write_version(args.version)
            print(f"Version set: {old_ver} → {args.version}")
            
            if args.build is not None:
                old_build = read_build_number()
                write_build_number(args.build)
                print(f"Build set: {old_build} → {args.build}")
            
            version_data = write_json_version()
            print(f"Full version: {version_data['full_version']}")
            
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())