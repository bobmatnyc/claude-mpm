#!/usr/bin/env python3
"""
Version Management Script for claude-mpm

Provides functionality to increment versions and manage build numbers.
"""

import argparse
import sys
from pathlib import Path
from typing import Tuple


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_current_version(project_root: Path) -> str:
    """Get current version from VERSION file."""
    version_file = project_root / "VERSION"
    if not version_file.exists():
        return "0.0.0"
    return version_file.read_text().strip()


def get_current_build_number(project_root: Path) -> int:
    """Get current build number from BUILD_NUMBER file."""
    build_file = project_root / "BUILD_NUMBER"
    if not build_file.exists():
        return 1
    try:
        return int(build_file.read_text().strip())
    except ValueError:
        return 1


def bump_version(current_version: str, bump_type: str) -> str:
    """Bump version according to semantic versioning."""
    parts = current_version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current_version}")
    
    major, minor, patch = map(int, parts)
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")
    
    return f"{major}.{minor}.{patch}"


def increment_build_number(project_root: Path) -> Tuple[int, int]:
    """Increment build number and return old and new values."""
    current_build = get_current_build_number(project_root)
    new_build = current_build + 1
    
    build_file = project_root / "BUILD_NUMBER"
    build_file.write_text(str(new_build) + "\n")
    
    return current_build, new_build


def update_version_files(project_root: Path, new_version: str) -> None:
    """Update both VERSION files with new version."""
    root_version_file = project_root / "VERSION"
    package_version_file = project_root / "src" / "claude_mpm" / "VERSION"
    
    # Update root VERSION file
    root_version_file.write_text(new_version + "\n")
    print(f"Updated {root_version_file} to {new_version}")
    
    # Update package VERSION file  
    if package_version_file.parent.exists():
        package_version_file.write_text(new_version + "\n")
        print(f"Updated {package_version_file} to {new_version}")


def display_current_info(project_root: Path) -> None:
    """Display current version and build information."""
    current_version = get_current_version(project_root)
    current_build = get_current_build_number(project_root)
    
    print(f"Current Version: {current_version}")
    print(f"Current Build Number: {current_build}")
    print(f"Full Version: v{current_version}-build.{current_build}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Version management for claude-mpm")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Show current version
    subparsers.add_parser("show", help="Show current version and build info")
    
    # Increment version
    inc_parser = subparsers.add_parser("increment", help="Increment version")
    inc_parser.add_argument(
        "type", 
        choices=["major", "minor", "patch"], 
        help="Version component to increment"
    )
    
    # Increment build only
    subparsers.add_parser("build", help="Increment build number only")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    project_root = get_project_root()
    
    try:
        if args.command == "show":
            display_current_info(project_root)
            
        elif args.command == "increment":
            current_version = get_current_version(project_root)
            new_version = bump_version(current_version, args.type)
            
            print(f"Version bump ({args.type}): {current_version} → {new_version}")
            update_version_files(project_root, new_version)
            
            # Also increment build number
            old_build, new_build = increment_build_number(project_root)
            print(f"Build number incremented: {old_build} → {new_build}")
            
            print(f"✅ Version updated to {new_version} (build {new_build})")
            
        elif args.command == "build":
            old_build, new_build = increment_build_number(project_root)
            current_version = get_current_version(project_root)
            print(f"Build number incremented: {old_build} → {new_build}")
            print(f"Current version: v{current_version}-build.{new_build}")
            
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())