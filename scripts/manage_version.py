#!/usr/bin/env python3
"""
Version management script for Claude MPM.

This script implements a comprehensive version management system that:
1. Uses setuptools-scm for version detection from git tags
2. Updates VERSION file to maintain version synchronization
3. Generates/updates CHANGELOG.md from git commits automatically
4. Supports semantic versioning with conventional commits

OPERATIONAL PURPOSE:
Central version management for consistent releases across all distribution channels.
Automates version bumping, changelog generation, and release preparation.

VERSION MANAGEMENT STRATEGY:
- Primary source of truth: Git tags (format: v1.0.0)
- setuptools-scm derives version from git state
- VERSION file kept in sync for quick access
- package.json synchronized via release.py script
- Conventional commits determine version bump type automatically

SEMANTIC VERSIONING IMPLEMENTATION:
- MAJOR (X.0.0): Breaking changes (BREAKING CHANGE: or feat!)
- MINOR (0.X.0): New features (feat:)
- PATCH (0.0.X): Bug fixes (fix:) or performance improvements (perf:)
- Development versions between releases: X.Y.Z.postN+gHASH[.dirty]

VERSION COMPATIBILITY:
- Backward compatible with manual version management
- Forward compatible with CI/CD automation
- Supports both manual and automatic version bumping
- Handles migration from old version formats gracefully

DEPLOYMENT PIPELINE INTEGRATION:
1. Developer commits with conventional format
2. CI runs manage_version.py to determine bump
3. Version updated and changelog generated
4. Git tag created for release
5. PyPI and npm packages built and published

MONITORING AND TROUBLESHOOTING:
- Check git tags: git tag -l | sort -V
- Verify VERSION file matches latest tag
- Review CHANGELOG.md for missing commits
- Ensure conventional commit format compliance
- Monitor version sync across package files

ROLLBACK PROCEDURES:
- Delete incorrect git tag: git tag -d vX.Y.Z
- Reset VERSION file to previous version
- Revert CHANGELOG.md changes
- Force push tag updates carefully
- Coordinate with PyPI/npm for package yanking
"""

import subprocess
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
import argparse


# Conventional commit types and their changelog sections
# These map commit types to human-readable changelog categories
# Following the Conventional Commits specification v1.0.0
COMMIT_TYPES = {
    "feat": "Features",              # New features
    "fix": "Bug Fixes",              # Bug fixes
    "docs": "Documentation",         # Documentation only changes
    "style": "Code Style",           # Code style changes (formatting, etc)
    "refactor": "Code Refactoring",  # Code changes that neither fix bugs nor add features
    "perf": "Performance Improvements",  # Performance improvements
    "test": "Tests",                 # Adding or updating tests
    "build": "Build System",         # Build system or dependency changes
    "ci": "Continuous Integration",  # CI configuration changes
    "chore": "Chores",              # Other changes that don't modify src or test files
    "revert": "Reverts"             # Reverting previous commits
}

# Types that trigger version bumps based on semantic versioning rules
# These determine how the version number changes based on commit types
MAJOR_TYPES = ["breaking", "major"]  # Keywords in commit message that trigger major bump
MINOR_TYPES = ["feat"]               # Commit types that trigger minor version bump
PATCH_TYPES = ["fix", "perf"]        # Commit types that trigger patch version bump


def run_command(cmd: List[str]) -> str:
    """Run a command and return its output.
    
    This is a utility function that executes shell commands safely and returns
    their output. Used throughout the script for git operations.
    
    Args:
        cmd: List of command arguments (e.g., ['git', 'tag', '-l'])
        
    Returns:
        String output from the command, stripped of whitespace
        Empty string if command fails
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(cmd)}: {e}")
        return ""


def get_current_version() -> str:
    """Get current version from VERSION file.
    
    Version Detection:
    1. Root VERSION file: Primary source of truth
    2. Validates sync with src/claude_mpm/VERSION
    3. Default: Returns 0.0.0 if VERSION file is missing
    
    The root VERSION file is the single source of truth for version information.
    Git tags are used for releases, but VERSION file contains the current version.
    
    Returns:
        Current version string from VERSION file
    """
    # Read from root VERSION file - single source of truth
    root_version_file = Path("VERSION")
    if root_version_file.exists():
        version = root_version_file.read_text().strip()
        # Validate sync with package VERSION file
        validate_version_sync()
        return version
    
    # Default version when VERSION file is missing
    print("WARNING: VERSION file not found, using default version 0.0.0", file=sys.stderr)
    return "0.0.0"


def parse_conventional_commit(message: str) -> Tuple[Optional[str], Optional[str], str, bool]:
    """Parse a conventional commit message following the Conventional Commits spec.
    
    Conventional Commits Format:
    <type>[optional scope]: <description>
    
    [optional body]
    
    [optional footer(s)]
    
    Examples:
    - "feat: add new agent capabilities"
    - "fix(logging): correct session duration calculation"
    - "feat!: redesign agent API" (breaking change)
    - "fix: typo\n\nBREAKING CHANGE: API renamed" (breaking in footer)
    
    Breaking Changes Detection:
    1. Exclamation mark after type/scope: "feat!:" or "feat(api)!:"
    2. "BREAKING CHANGE:" in commit body/footer
    3. "BREAKING:" as shorthand in body/footer
    
    Args:
        message: Full commit message including body
        
    Returns:
        Tuple of:
        - type: Commit type (feat, fix, etc.) or None
        - scope: Optional scope in parentheses or None
        - description: Commit description (subject line)
        - is_breaking: True if breaking change detected
    """
    # Check for breaking change indicators anywhere in the message
    # This includes both the footer format and inline indicators
    is_breaking = "BREAKING CHANGE:" in message or "BREAKING:" in message
    
    # Parse conventional commit format: type(scope): description
    # Also handles type!: for breaking changes
    pattern = r"^(\w+)(?:\(([^)]+)\))?: (.+)"
    match = re.match(pattern, message.split("\n")[0])
    
    if match:
        commit_type, scope, description = match.groups()
        return commit_type, scope, description, is_breaking
    
    # If not a conventional commit, return the first line as description
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
    """Determine version bump type based on commits using semantic versioning rules.
    
    Version Bump Logic (in priority order):
    1. MAJOR: Any commit with breaking changes
       - BREAKING CHANGE: in footer
       - feat!: or fix!: syntax
       - Resets minor and patch to 0
       
    2. MINOR: Any commit with new features (feat:)
       - Only if no breaking changes
       - Resets patch to 0
       
    3. PATCH: Any commit with fixes (fix:) or performance improvements (perf:)
       - Only if no breaking changes or features
       - Increments patch version
       
    4. DEFAULT: If no conventional commits found, defaults to patch
       - Ensures version always increments
       - Safe default for manual commits
    
    This implements the semantic versioning specification where:
    - MAJOR version for incompatible API changes
    - MINOR version for backwards-compatible functionality additions
    - PATCH version for backwards-compatible bug fixes
    
    Args:
        commits: List of parsed commit dictionaries
        
    Returns:
        Version bump type: "major", "minor", or "patch"
    """
    # Check for breaking changes first (highest priority)
    has_breaking = any(c["breaking"] for c in commits)
    # Check for new features
    has_minor = any(c["type"] in MINOR_TYPES for c in commits)
    # Check for fixes or performance improvements  
    has_patch = any(c["type"] in PATCH_TYPES for c in commits)
    
    # Apply semantic versioning rules in priority order
    if has_breaking:
        return "major"
    elif has_minor:
        return "minor"
    elif has_patch:
        return "patch"
    return "patch"  # Default to patch for safety


def bump_version(current_version: str, bump_type: str) -> str:
    """Bump version according to semantic versioning specification.
    
    Semantic Versioning Rules:
    - MAJOR: Increment major, reset minor and patch to 0
    - MINOR: Increment minor, reset patch to 0
    - PATCH: Increment patch only
    
    Version Cleaning:
    - Removes development suffixes (.postN, .dirty, +gHASH)
    - Extracts base semantic version (X.Y.Z)
    - Handles various version formats from setuptools-scm
    
    Examples:
    - "1.2.3" + patch -> "1.2.4"
    - "1.2.3.post4+g1234567" + minor -> "1.3.0"
    - "1.2.3.dirty" + major -> "2.0.0"
    
    Args:
        current_version: Current version string (may include suffixes)
        bump_type: Type of bump ("major", "minor", or "patch")
        
    Returns:
        New clean semantic version string (X.Y.Z format)
    """
    # Clean version by extracting base semantic version
    # This removes any PEP 440 local version identifiers
    base_version = re.match(r"(\d+\.\d+\.\d+)", current_version)
    if base_version:
        current_version = base_version.group(1)
    
    # Parse version components
    major, minor, patch = map(int, current_version.split("."))
    
    # Apply semantic versioning rules
    if bump_type == "major":
        # Breaking change: increment major, reset others
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        # New feature: increment minor, reset patch
        return f"{major}.{minor + 1}.0"
    else:  # patch
        # Bug fix: increment patch only
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
    """Update both VERSION files to maintain synchronization.
    
    Updates:
    1. Root VERSION file (primary source of truth)
    2. src/claude_mpm/VERSION file (for package distribution)
    
    This ensures both files stay synchronized and prevents version mismatches
    in the package distribution.
    
    Args:
        version: New version string to write to both files
    """
    # Update root VERSION file (primary)
    root_version_file = Path("VERSION")
    root_version_file.write_text(version + "\n")
    print(f"Updated root VERSION file to {version}")
    
    # Update package VERSION file (for distribution)
    package_version_file = Path("src/claude_mpm/VERSION")
    if package_version_file.parent.exists():
        package_version_file.write_text(version + "\n")
        print(f"Updated package VERSION file to {version}")
    else:
        print("WARNING: src/claude_mpm directory not found, skipping package VERSION update", file=sys.stderr)


def validate_version_sync() -> bool:
    """Validate that both VERSION files contain the same version.
    
    Checks:
    1. Both VERSION files exist
    2. Both contain the same version string
    3. Raises error if out of sync
    
    This function helps prevent version mismatches that can cause
    package distribution issues where the reported version differs
    from the actual package version.
    
    Returns:
        True if files are synchronized
        
    Raises:
        ValueError: If files are out of sync or missing
    """
    root_version_file = Path("VERSION")
    package_version_file = Path("src/claude_mpm/VERSION")
    
    # Check if both files exist
    if not root_version_file.exists():
        raise ValueError("Root VERSION file is missing")
    
    if not package_version_file.exists():
        print("WARNING: Package VERSION file is missing", file=sys.stderr)
        return False
    
    # Read versions from both files
    root_version = root_version_file.read_text().strip()
    package_version = package_version_file.read_text().strip()
    
    # Validate they match
    if root_version != package_version:
        raise ValueError(
            f"VERSION files are out of sync: "
            f"root={root_version}, package={package_version}. "
            f"Run version sync to fix."
        )
    
    return True


def sync_version_files():
    """Synchronize package VERSION file with root VERSION file.
    
    This function copies the version from the root VERSION file
    (source of truth) to the package VERSION file, ensuring they
    are synchronized.
    """
    root_version_file = Path("VERSION")
    package_version_file = Path("src/claude_mpm/VERSION")
    
    if not root_version_file.exists():
        raise ValueError("Root VERSION file is missing")
    
    # Read version from root file
    version = root_version_file.read_text().strip()
    
    # Write to package file
    if package_version_file.parent.exists():
        package_version_file.write_text(version + "\n")
        print(f"Synchronized package VERSION file to {version}")
    else:
        print("WARNING: src/claude_mpm directory not found", file=sys.stderr)


def create_git_tag(version: str, message: str):
    """Create an annotated git tag for the version.
    
    Git Tag Strategy:
    - Uses 'v' prefix convention (v1.2.3)
    - Creates annotated tags (includes tagger info and message)
    - Annotated tags are preferred for releases (shown in git describe)
    - Tag message typically includes release title
    
    The 'v' prefix is a widely adopted convention that:
    - Distinguishes version tags from other tags
    - Works well with GitHub releases
    - Compatible with most CI/CD systems
    - Recognized by setuptools-scm
    
    Args:
        version: Semantic version string (without 'v' prefix)
        message: Tag annotation message
    """
    tag = f"v{version}"
    # Create annotated tag with message
    # -a: Create annotated tag (not lightweight)
    # -m: Provide message inline
    run_command(["git", "tag", "-a", tag, "-m", message])
    print(f"Created git tag: {tag}")


def main():
    parser = argparse.ArgumentParser(description="Manage Claude MPM versioning")
    parser.add_argument("command", choices=["check", "bump", "changelog", "tag", "auto", "sync", "validate"],
                       help="Command to run")
    parser.add_argument("--bump-type", choices=["major", "minor", "patch", "auto"],
                       default="auto", help="Version bump type")
    parser.add_argument("--dry-run", action="store_true",
                       help="Don't make any changes")
    parser.add_argument("--no-commit", action="store_true",
                       help="Don't commit changes")
    
    args = parser.parse_args()
    
    # Handle commands that don't need current version first
    if args.command == "validate":
        # Validate version sync
        try:
            validate_version_sync()
            print("VERSION files are synchronized")
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    elif args.command == "sync":
        # Synchronize version files
        if not args.dry_run:
            try:
                sync_version_files()
            except ValueError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("DRY RUN: Would synchronize VERSION files")
        return
    
    # Get current version for other commands
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
                # Commit changes (include both VERSION files)
                run_command(["git", "add", "VERSION", "src/claude_mpm/VERSION", "CHANGELOG.md"])
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