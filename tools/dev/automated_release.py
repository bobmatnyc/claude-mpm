#!/usr/bin/env python3
"""
Automated release script for claude-mpm.

This script automates the entire release process:
1. Syncs version files
2. Increments build number if needed
3. Commits changes
4. Creates version tag
5. Syncs agent and skills repositories
6. Builds package
7. Publishes to PyPI
8. Pushes to GitHub

Usage:
    python tools/dev/automated_release.py --patch           # Patch version bump (X.Y.Z+1)
    python tools/dev/automated_release.py --minor           # Minor version bump (X.Y+1.0)
    python tools/dev/automated_release.py --major           # Major version bump (X+1.0.0)
    python tools/dev/automated_release.py --build           # Build-only release (no version bump)
    python tools/dev/automated_release.py --patch --yes     # Auto-confirm all prompts
    python tools/dev/automated_release.py --patch --skip-agent-sync  # Skip agent repo sync
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


def run_command(
    cmd: str, cwd: Optional[Path] = None, check: bool = True
) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    print(f"Running: {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True, check=False
    )

    if check and result.returncode != 0:
        print(f"Command failed with return code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        sys.exit(1)

    return result.returncode, result.stdout, result.stderr


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def sync_version_files(project_root: Path) -> None:
    """Sync version between root VERSION and src/claude_mpm/VERSION files."""
    root_version_file = project_root / "VERSION"
    package_version_file = project_root / "src" / "claude_mpm" / "VERSION"

    if not root_version_file.exists():
        print("ERROR: Root VERSION file not found")
        sys.exit(1)

    version = root_version_file.read_text().strip()
    print(f"Syncing version files to: {version}")

    # Update package VERSION file
    package_version_file.write_text(version + "\n")
    print(f"Updated {package_version_file}")


def get_current_version(project_root: Path) -> str:
    """Get current version from VERSION file."""
    version_file = project_root / "VERSION"
    if not version_file.exists():
        return "0.0.0"
    return version_file.read_text().strip()


def bump_version(current_version: str, bump_type: str) -> str:
    """Bump version according to semantic versioning."""
    parts = current_version.split(".")
    if len(parts) != 3:
        print(f"ERROR: Invalid version format: {current_version}")
        sys.exit(1)

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
        print(f"ERROR: Invalid bump type: {bump_type}")
        sys.exit(1)

    return f"{major}.{minor}.{patch}"


def update_version_files(project_root: Path, new_version: str) -> None:
    """Update all version files (VERSION, package.json, pyproject.toml)."""
    import json
    import re

    # Update VERSION files
    root_version_file = project_root / "VERSION"
    package_version_file = project_root / "src" / "claude_mpm" / "VERSION"

    root_version_file.write_text(new_version + "\n")
    print(f"Updated {root_version_file} to {new_version}")

    package_version_file.write_text(new_version + "\n")
    print(f"Updated {package_version_file} to {new_version}")

    # Update package.json
    package_json_path = project_root / "package.json"
    if package_json_path.exists():
        with open(package_json_path) as f:
            package_data = json.load(f)
        package_data["version"] = new_version
        with open(package_json_path, "w") as f:
            json.dump(package_data, f, indent=2)
            f.write("\n")
        print(f"Updated {package_json_path} to {new_version}")

    # Update pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        # Update [project] version
        content = re.sub(
            r'^version = "[^"]*"',
            f'version = "{new_version}"',
            content,
            flags=re.MULTILINE,
            count=1
        )
        # Update [tool.commitizen] version
        content = re.sub(
            r'\[tool\.commitizen\]\s+name = "[^"]*"\s+version = "[^"]*"',
            f'[tool.commitizen]\nname = "cz_conventional_commits"\nversion = "{new_version}"',
            content,
            flags=re.DOTALL
        )
        pyproject_path.write_text(content)
        print(f"Updated {pyproject_path} to {new_version}")

    # Update CHANGELOG.md - add new version entry if not present
    changelog_path = project_root / "CHANGELOG.md"
    if changelog_path.exists():
        from datetime import date
        changelog_content = changelog_path.read_text()
        version_header = f"## [{new_version}]"

        if version_header not in changelog_content:
            # Find the Unreleased section and add new version after it
            unreleased_pattern = r'(## \[Unreleased\].*?)(\n## \[)'
            today = date.today().strftime("%Y-%m-%d")
            new_entry = f"\n\n{version_header} - {today}\n\n### Fixed\n- Automated release improvements\n"

            updated_content = re.sub(
                unreleased_pattern,
                r'\1' + new_entry + r'\2',
                changelog_content,
                flags=re.DOTALL
            )

            if updated_content != changelog_content:
                changelog_path.write_text(updated_content)
                print(f"Updated {changelog_path} with version {new_version}")


def run_quality_checks(project_root: Path, skip_checks: bool = False) -> None:
    """Run quality checks before release."""
    if skip_checks:
        print("⚠️  Skipping quality checks (--skip-checks flag used)")
        return

    print("\n🔍 Running quality checks...")
    print("=" * 50)

    # Run pre-publish checks via make
    returncode, _stdout, _stderr = run_command(
        "make pre-publish", cwd=project_root, check=False
    )

    if returncode != 0:
        print("\n❌ Quality checks failed!")
        print("Please fix the issues above before releasing.")
        print("\nTips:")
        print("  - Run 'make lint-fix' to auto-fix formatting issues")
        print("  - Run 'make lint-all' to see all issues")
        print("  - Run 'make quality' to run all checks")
        sys.exit(1)

    print("✅ Quality checks passed")


def increment_build_number(project_root: Path) -> None:
    """Increment build number if code changes are detected."""
    print("Checking for build number increment...")
    returncode, _stdout, _stderr = run_command(
        "python scripts/increment_build.py --all-changes", cwd=project_root, check=False
    )

    if returncode == 0:
        print("Build number incremented")
    else:
        print("No build number increment needed")


def commit_and_tag(project_root: Path, version: str, is_version_bump: bool) -> None:
    """Commit changes and create version tag."""
    # Stage all changes
    run_command("git add .", cwd=project_root)

    # Check if there are changes to commit
    returncode, _stdout, _stderr = run_command(
        "git diff --cached --quiet", cwd=project_root, check=False
    )

    if returncode == 0:
        print("No changes to commit")
        return

    # Commit changes
    if is_version_bump:
        commit_msg = f"bump: version {get_current_version(project_root)} → {version}"
    else:
        commit_msg = f"build: automated build for version {version}"

    run_command(f'git commit -m "{commit_msg}"', cwd=project_root)

    # Create tag
    tag_name = f"v{version}"
    run_command(f"git tag {tag_name}", cwd=project_root)
    print(f"Created tag: {tag_name}")


def build_package(project_root: Path) -> None:
    """Build the package."""
    print("Building package...")
    run_command("python -m build", cwd=project_root)
    print("Package built successfully")


def publish_package(project_root: Path, version: str) -> None:
    """Publish package to PyPI."""
    print("Publishing to PyPI...")
    run_command(f"python -m twine upload dist/claude_mpm-{version}*", cwd=project_root)
    print("Package published successfully")


def sync_agent_repositories(
    project_root: Path, version: str, skip_sync: bool = False, yes_to_all: bool = False
) -> None:
    """Sync agent and skills repositories before release.

    This function checks for uncommitted changes in the agent repositories and
    commits/pushes them before building the release package.

    Args:
        project_root: The project root directory
        version: The version being released
        skip_sync: If True, skip agent repository sync
        yes_to_all: If True, auto-confirm all prompts
    """
    if skip_sync:
        print("⚠️  Skipping agent repository sync (--skip-agent-sync flag used)")
        return

    print("\n🔄 Syncing agent repositories...")
    print("=" * 50)

    agents_repo = Path.home() / ".claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents"
    skills_repo = Path.home() / ".claude-mpm/cache/skills/system"

    repos_to_sync = [
        (agents_repo, "claude-mpm-agents"),
        (skills_repo, "claude-mpm-skills"),
    ]

    sync_success = True

    for repo_path, repo_name in repos_to_sync:
        if not repo_path.exists():
            print(f"⚠️  Repository not found: {repo_path}")
            print(f"   Skipping {repo_name} sync")
            continue

        if not (repo_path / ".git").exists():
            print(f"⚠️  Not a git repository: {repo_path}")
            print(f"   Skipping {repo_name} sync")
            continue

        print(f"\n📦 Checking {repo_name}...")

        # Check for uncommitted changes
        returncode, stdout, _stderr = run_command(
            "git status --porcelain", cwd=repo_path, check=False
        )

        # Filter out .etag_cache.json files
        changes = [
            line for line in stdout.strip().split("\n")
            if line and ".etag_cache.json" not in line
        ]

        if not changes:
            print(f"   ✓ No changes to sync in {repo_name}")
            continue

        print(f"   Found changes in {repo_name}:")
        for change in changes[:10]:  # Show first 10 changes
            print(f"     {change}")
        if len(changes) > 10:
            print(f"     ... and {len(changes) - 10} more")

        # Get current branch
        returncode, branch_stdout, _stderr = run_command(
            "git branch --show-current", cwd=repo_path, check=False
        )
        current_branch = branch_stdout.strip()

        # Confirm sync
        if not yes_to_all:
            response = input(f"\n   Commit and push changes to {repo_name}? [y/N]: ")
            if response.lower() not in ["y", "yes"]:
                print(f"   Skipping {repo_name} sync")
                sync_success = False
                continue

        # Add all changes except .etag_cache.json
        run_command("git add -A", cwd=repo_path)
        run_command("git reset -- '**/.etag_cache.json'", cwd=repo_path, check=False)
        run_command("git reset -- '.etag_cache.json'", cwd=repo_path, check=False)

        # Create commit message
        commit_msg = f"""chore: sync {repo_name} for v{version} release

- Synchronized changes for release v{version}
- Auto-committed by automated_release.py

🤖 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>"""

        # Commit changes
        returncode, _stdout, _stderr = run_command(
            f'git commit -m "{commit_msg}"', cwd=repo_path, check=False
        )

        if returncode != 0:
            print(f"   ⚠️  Failed to commit changes in {repo_name}")
            sync_success = False
            continue

        print(f"   ✓ Committed changes in {repo_name}")

        # Push to remote
        returncode, _stdout, _stderr = run_command(
            f"git push origin {current_branch}", cwd=repo_path, check=False
        )

        if returncode != 0:
            print(f"   ⚠️  Failed to push {repo_name} to remote")
            print("      You may need to push manually later")
            sync_success = False
        else:
            print(f"   ✓ Pushed {repo_name} to origin/{current_branch}")

    if sync_success:
        print("\n✅ Agent repository sync complete")
    else:
        print("\n⚠️  Agent repository sync completed with warnings")
        print("   Some repositories may need manual intervention")


def push_to_github(project_root: Path) -> None:
    """Push changes and tags to GitHub."""
    print("Pushing to GitHub...")
    run_command("git push origin main --tags", cwd=project_root)
    print("Pushed to GitHub successfully")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated release script for claude-mpm"
    )

    # Version bump options (mutually exclusive)
    bump_group = parser.add_mutually_exclusive_group(required=True)
    bump_group.add_argument("--patch", action="store_true", help="Patch version bump")
    bump_group.add_argument("--minor", action="store_true", help="Minor version bump")
    bump_group.add_argument("--major", action="store_true", help="Major version bump")
    bump_group.add_argument(
        "--build", action="store_true", help="Build-only release (no version bump)"
    )

    # Options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    parser.add_argument(
        "--skip-publish", action="store_true", help="Skip PyPI publishing"
    )
    parser.add_argument("--skip-push", action="store_true", help="Skip GitHub push")
    parser.add_argument(
        "--skip-agent-sync",
        action="store_true",
        help="Skip agent repository sync before build",
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip quality checks (NOT RECOMMENDED)",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Auto-confirm all prompts (useful for CI/CD)",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        return

    project_root = get_project_root()

    # Run quality checks first (unless explicitly skipped)
    run_quality_checks(project_root, args.skip_checks)

    current_version = get_current_version(project_root)

    print(f"Current version: {current_version}")

    # Determine new version
    if args.build:
        new_version = current_version
        is_version_bump = False
        print("Build-only release, keeping current version")
    else:
        bump_type = "patch" if args.patch else "minor" if args.minor else "major"
        new_version = bump_version(current_version, bump_type)
        is_version_bump = True
        print(f"Version bump ({bump_type}): {current_version} → {new_version}")

        # Update version files
        update_version_files(project_root, new_version)

    # Sync version files (ensure consistency)
    sync_version_files(project_root)

    # Increment build number if needed
    increment_build_number(project_root)

    # Commit and tag
    commit_and_tag(project_root, new_version, is_version_bump)

    # Sync agent repositories before building
    sync_agent_repositories(
        project_root,
        new_version,
        skip_sync=args.skip_agent_sync,
        yes_to_all=args.yes,
    )

    # Build package
    build_package(project_root)

    # Publish to PyPI
    if not args.skip_publish:
        publish_package(project_root, new_version)
    else:
        print("Skipping PyPI publishing")

    # Push to GitHub
    if not args.skip_push:
        push_to_github(project_root)
    else:
        print("Skipping GitHub push")

    print(f"✅ Release {new_version} completed successfully!")
    print(
        f"📦 Package available at: https://pypi.org/project/claude-mpm/{new_version}/"
    )


if __name__ == "__main__":
    main()
