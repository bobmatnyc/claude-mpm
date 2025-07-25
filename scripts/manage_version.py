#!/usr/bin/env python3
"""
Version management script for Claude MPM.

This script:
1. Uses setuptools-scm for version detection from git tags
2. Updates VERSION file
3. Generates/updates CHANGELOG.md from git commits
4. Supports semantic versioning with conventional commits
"""

import subprocess
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
import argparse


# Conventional commit types and their changelog sections
COMMIT_TYPES = {
    "feat": "Features",
    "fix": "Bug Fixes", 
    "docs": "Documentation",
    "style": "Code Style",
    "refactor": "Code Refactoring",
    "perf": "Performance Improvements",
    "test": "Tests",
    "build": "Build System",
    "ci": "Continuous Integration",
    "chore": "Chores",
    "revert": "Reverts"
}

# Types that trigger version bumps
MAJOR_TYPES = ["breaking", "major"]  # in commit message
MINOR_TYPES = ["feat"]
PATCH_TYPES = ["fix", "perf"]


def run_command(cmd: List[str]) -> str:
    """Run a command and return its output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(cmd)}: {e}")
        return ""


def get_current_version() -> str:
    """Get current version from git tags or VERSION file."""
    # Try setuptools-scm first
    try:
        from setuptools_scm import get_version
        return get_version(root="..")
    except:
        pass
    
    # Try git describe
    version = run_command(["git", "describe", "--tags", "--always"])
    if version and not version.startswith("fatal"):
        # Clean up version (remove 'v' prefix if present)
        version = version.lstrip("v")
        # Handle versions like 0.5.0-2-g1234567
        parts = version.split("-")
        if len(parts) >= 3:
            base_version = parts[0]
            commits_since = parts[1]
            return f"{base_version}.post{commits_since}"
        return version
    
    # Fallback to VERSION file
    version_file = Path("VERSION")
    if version_file.exists():
        return version_file.read_text().strip()
    
    return "0.0.0"


def parse_conventional_commit(message: str) -> Tuple[Optional[str], Optional[str], str, bool]:
    """Parse a conventional commit message.
    
    Returns:
        Tuple of (type, scope, description, is_breaking)
    """
    # Check for breaking change
    is_breaking = "BREAKING CHANGE:" in message or "BREAKING:" in message
    
    # Parse conventional commit format: type(scope): description
    pattern = r"^(\w+)(?:\(([^)]+)\))?: (.+)"
    match = re.match(pattern, message.split("\n")[0])
    
    if match:
        commit_type, scope, description = match.groups()
        return commit_type, scope, description, is_breaking
    
    return None, None, message.split("\n")[0], is_breaking


def get_commits_since_tag(tag: Optional[str] = None) -> List[dict]:
    """Get all commits since the last tag."""
    if tag:
        cmd = ["git", "log", f"{tag}..HEAD", "--pretty=format:%H|%ai|%s|%b|%an"]
    else:
        cmd = ["git", "log", "--pretty=format:%H|%ai|%s|%b|%an"]
    
    output = run_command(cmd)
    if not output:
        return []
    
    commits = []
    for line in output.split("\n"):
        if line:
            parts = line.split("|", 4)
            if len(parts) >= 5:
                hash, date, subject, body, author = parts
                commit_type, scope, description, is_breaking = parse_conventional_commit(subject)
                commits.append({
                    "hash": hash[:7],
                    "date": date,
                    "type": commit_type,
                    "scope": scope,
                    "description": description,
                    "breaking": is_breaking,
                    "author": author,
                    "body": body
                })
    
    return commits


def determine_version_bump(commits: List[dict]) -> str:
    """Determine version bump type based on commits."""
    has_breaking = any(c["breaking"] for c in commits)
    has_minor = any(c["type"] in MINOR_TYPES for c in commits)
    has_patch = any(c["type"] in PATCH_TYPES for c in commits)
    
    if has_breaking:
        return "major"
    elif has_minor:
        return "minor"
    elif has_patch:
        return "patch"
    return "patch"  # Default to patch


def bump_version(current_version: str, bump_type: str) -> str:
    """Bump version according to semver."""
    # Clean version (remove .postN suffix)
    base_version = re.match(r"(\d+\.\d+\.\d+)", current_version)
    if base_version:
        current_version = base_version.group(1)
    
    major, minor, patch = map(int, current_version.split("."))
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def generate_changelog_entry(version: str, commits: List[dict], date: str) -> str:
    """Generate a changelog entry for a version."""
    lines = [f"## [{version}] - {date}\n"]
    
    # Group commits by type
    grouped = {}
    for commit in commits:
        commit_type = commit["type"] or "other"
        if commit_type not in grouped:
            grouped[commit_type] = []
        grouped[commit_type].append(commit)
    
    # Add sections
    for commit_type, section_name in COMMIT_TYPES.items():
        if commit_type in grouped:
            lines.append(f"\n### {section_name}\n")
            for commit in grouped[commit_type]:
                scope = f"**{commit['scope']}**: " if commit["scope"] else ""
                lines.append(f"- {scope}{commit['description']} ([{commit['hash']}])")
                if commit["breaking"]:
                    lines.append(f"  - **BREAKING CHANGE**")
    
    # Add uncategorized commits
    if "other" in grouped:
        lines.append(f"\n### Other Changes\n")
        for commit in grouped["other"]:
            lines.append(f"- {commit['description']} ([{commit['hash']}])")
    
    return "\n".join(lines)


def update_changelog(new_entry: str):
    """Update CHANGELOG.md with new entry."""
    changelog_path = Path("CHANGELOG.md")
    
    if changelog_path.exists():
        content = changelog_path.read_text()
        # Insert after the header
        parts = content.split("\n## ", 1)
        if len(parts) == 2:
            new_content = parts[0] + "\n" + new_entry + "\n## " + parts[1]
        else:
            new_content = content + "\n" + new_entry
    else:
        # Create new changelog
        new_content = f"""# Changelog

All notable changes to Claude MPM will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

{new_entry}"""
    
    changelog_path.write_text(new_content)
    print(f"Updated CHANGELOG.md")


def update_version_file(version: str):
    """Update VERSION file."""
    version_file = Path("VERSION")
    version_file.write_text(version + "\n")
    print(f"Updated VERSION file to {version}")


def create_git_tag(version: str, message: str):
    """Create a git tag for the version."""
    tag = f"v{version}"
    run_command(["git", "tag", "-a", tag, "-m", message])
    print(f"Created git tag: {tag}")


def main():
    parser = argparse.ArgumentParser(description="Manage Claude MPM versioning")
    parser.add_argument("command", choices=["check", "bump", "changelog", "tag", "auto"],
                       help="Command to run")
    parser.add_argument("--bump-type", choices=["major", "minor", "patch", "auto"],
                       default="auto", help="Version bump type")
    parser.add_argument("--dry-run", action="store_true",
                       help="Don't make any changes")
    parser.add_argument("--no-commit", action="store_true",
                       help="Don't commit changes")
    
    args = parser.parse_args()
    
    # Get current version
    current_version = get_current_version()
    print(f"Current version: {current_version}")
    
    if args.command == "check":
        # Just display current version
        return
    
    # Get latest tag
    latest_tag = run_command(["git", "describe", "--tags", "--abbrev=0"])
    if not latest_tag or latest_tag.startswith("fatal"):
        latest_tag = None
    
    # Get commits since last tag
    commits = get_commits_since_tag(latest_tag)
    print(f"Found {len(commits)} commits since {latest_tag or 'beginning'}")
    
    if args.command in ["bump", "auto"]:
        # Determine version bump
        if args.bump_type == "auto":
            bump_type = determine_version_bump(commits)
        else:
            bump_type = args.bump_type
        
        new_version = bump_version(current_version, bump_type)
        print(f"New version: {new_version} ({bump_type} bump)")
        
        if not args.dry_run:
            # Update VERSION file
            update_version_file(new_version)
            
            # Generate changelog entry
            changelog_entry = generate_changelog_entry(
                new_version, commits, datetime.now().strftime("%Y-%m-%d")
            )
            update_changelog(changelog_entry)
            
            if not args.no_commit:
                # Commit changes
                run_command(["git", "add", "VERSION", "CHANGELOG.md"])
                run_command(["git", "commit", "-m", f"chore: bump version to {new_version}"])
                
                # Create tag
                create_git_tag(new_version, f"Release {new_version}")
                print(f"\nVersion bumped to {new_version}")
                print("Run 'git push && git push --tags' to publish")
    
    elif args.command == "changelog":
        # Just generate changelog
        if commits:
            changelog_entry = generate_changelog_entry(
                current_version, commits, datetime.now().strftime("%Y-%m-%d")
            )
            if args.dry_run:
                print("\nChangelog entry:")
                print(changelog_entry)
            else:
                update_changelog(changelog_entry)
    
    elif args.command == "tag":
        # Just create a tag for current version
        if not args.dry_run:
            create_git_tag(current_version, f"Release {current_version}")


if __name__ == "__main__":
    main()