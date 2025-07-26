#!/usr/bin/env python3
"""
Unified release script for Claude MPM.

This script ensures npm and PyPI versions stay synchronized and handles the
complete release process including:
- Pre-release checks
- Version synchronization
- Building and publishing to PyPI and npm
- Creating GitHub releases
- Post-release verification
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import shutil
import time


class ReleaseManager:
    """Manages the release process for Claude MPM."""
    
    def __init__(self, dry_run: bool = False, skip_tests: bool = False):
        self.dry_run = dry_run
        self.skip_tests = skip_tests
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.manage_version_script = self.scripts_dir / "manage_version.py"
        
        # Track what we've done for cleanup if needed
        self.cleanup_actions = []
        
    def run_command(self, cmd: List[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        if self.dry_run and not any(safe_cmd in cmd[0] for safe_cmd in ["git", "cat", "python3"] if cmd):
            print(f"[DRY-RUN] Would run: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False,
            cwd=self.project_root
        )
        
        if check and result.returncode != 0:
            print(f"Command failed: {' '.join(cmd)}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            sys.exit(1)
            
        return result
    
    def get_current_version(self) -> str:
        """Get the current version from VERSION file."""
        version_file = self.project_root / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return "0.0.0"
    
    def check_working_directory(self) -> bool:
        """Ensure we have a clean working directory."""
        result = self.run_command(["git", "status", "--porcelain"])
        if result.stdout.strip():
            print("ERROR: Working directory is not clean. Please commit or stash changes.")
            print("Uncommitted changes:")
            print(result.stdout)
            return False
        return True
    
    def check_branch(self) -> bool:
        """Ensure we're on the main branch."""
        result = self.run_command(["git", "branch", "--show-current"])
        current_branch = result.stdout.strip()
        if current_branch != "main":
            print(f"ERROR: Not on main branch (current: {current_branch})")
            return False
        return True
    
    def run_tests(self) -> bool:
        """Run the test suite."""
        if self.skip_tests:
            print("Skipping tests (--skip-tests specified)")
            return True
            
        print("\nRunning test suite...")
        test_script = self.scripts_dir / "run_all_tests.sh"
        if test_script.exists():
            result = self.run_command(["bash", str(test_script)], check=False)
            if result.returncode != 0:
                print("ERROR: Tests failed!")
                return False
        else:
            print("WARNING: Test script not found, skipping tests")
        return True
    
    def update_version(self, bump_type: str) -> str:
        """Update version using manage_version.py."""
        print(f"\nBumping version ({bump_type})...")
        
        # Use manage_version.py to bump version
        cmd = ["python3", str(self.manage_version_script), "bump", "--bump-type", bump_type]
        if self.dry_run:
            cmd.append("--dry-run")
        
        result = self.run_command(cmd)
        
        # Get the new version
        new_version = self.get_current_version()
        print(f"New version: {new_version}")
        return new_version
    
    def update_package_json(self, version: str) -> bool:
        """Update package.json with the new version."""
        package_json_path = self.project_root / "package.json"
        if not package_json_path.exists():
            print("WARNING: package.json not found, skipping npm version update")
            return True
            
        print(f"\nUpdating package.json to version {version}...")
        
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
        
        old_version = package_data.get("version", "unknown")
        package_data["version"] = version
        
        if not self.dry_run:
            with open(package_json_path, 'w') as f:
                json.dump(package_data, f, indent=2)
                f.write('\n')  # Add newline at end of file
            print(f"Updated package.json: {old_version} -> {version}")
            
            # Commit the package.json update
            self.run_command(["git", "add", "package.json"])
            self.run_command(["git", "commit", "-m", f"chore: update package.json version to {version}"])
        else:
            print(f"[DRY-RUN] Would update package.json: {old_version} -> {version}")
            
        return True
    
    def build_python_package(self) -> bool:
        """Build Python distribution packages."""
        print("\nBuilding Python package...")
        
        # Clean previous builds
        for dir_name in ["dist", "build"]:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                if not self.dry_run:
                    shutil.rmtree(dir_path)
                    print(f"Cleaned {dir_name}/")
                else:
                    print(f"[DRY-RUN] Would clean {dir_name}/")
        
        # Build the package
        result = self.run_command(["python3", "-m", "build"], check=False)
        if result.returncode != 0:
            print("ERROR: Failed to build Python package")
            return False
            
        # Verify build artifacts
        dist_dir = self.project_root / "dist"
        if dist_dir.exists():
            artifacts = list(dist_dir.glob("*"))
            print(f"Built {len(artifacts)} artifacts:")
            for artifact in artifacts:
                print(f"  - {artifact.name}")
        
        return True
    
    def publish_to_pypi(self, test_pypi: bool = False) -> bool:
        """Publish package to PyPI."""
        repo = "testpypi" if test_pypi else "pypi"
        print(f"\nPublishing to {repo}...")
        
        dist_files = list((self.project_root / "dist").glob("*"))
        if not dist_files:
            print("ERROR: No distribution files found")
            return False
        
        cmd = ["python3", "-m", "twine", "upload"]
        if test_pypi:
            cmd.extend(["--repository", "testpypi"])
        cmd.extend([str(f) for f in dist_files])
        
        result = self.run_command(cmd, check=False)
        if result.returncode != 0:
            print(f"ERROR: Failed to upload to {repo}")
            return False
            
        print(f"Successfully published to {repo}")
        return True
    
    def publish_to_npm(self) -> bool:
        """Publish package to npm."""
        print("\nPublishing to npm...")
        
        # Check if logged in to npm
        result = self.run_command(["npm", "whoami"], check=False)
        if result.returncode != 0:
            print("ERROR: Not logged in to npm. Please run 'npm login' first.")
            return False
        
        # Publish the package
        result = self.run_command(["npm", "publish", "--access", "public"], check=False)
        if result.returncode != 0:
            print("ERROR: Failed to publish to npm")
            return False
            
        print("Successfully published to npm")
        return True
    
    def create_github_release(self, version: str) -> bool:
        """Create a GitHub release."""
        print(f"\nCreating GitHub release for v{version}...")
        
        # Check if gh CLI is available
        result = self.run_command(["which", "gh"], check=False)
        if result.returncode != 0:
            print("WARNING: GitHub CLI (gh) not found. Please create release manually.")
            print(f"Visit: https://github.com/bobmatnyc/claude-mpm/releases/new?tag=v{version}")
            return True
        
        # Get changelog entry for this version
        changelog_path = self.project_root / "CHANGELOG.md"
        if changelog_path.exists():
            changelog_content = changelog_path.read_text()
            # Extract the section for this version
            version_section = ""
            in_section = False
            for line in changelog_content.split('\n'):
                if line.startswith(f"## [{version}]"):
                    in_section = True
                elif in_section and line.startswith("## ["):
                    break
                elif in_section:
                    version_section += line + "\n"
            
            # Create release
            cmd = [
                "gh", "release", "create", f"v{version}",
                "--title", f"Claude MPM v{version}",
                "--notes", version_section.strip()
            ]
            
            # Add distribution files
            dist_files = list((self.project_root / "dist").glob("*"))
            for f in dist_files:
                cmd.append(str(f))
            
            result = self.run_command(cmd, check=False)
            if result.returncode == 0:
                print(f"Successfully created GitHub release for v{version}")
            else:
                print("Failed to create GitHub release automatically")
                print(f"Please create it manually at: https://github.com/bobmatnyc/claude-mpm/releases/new?tag=v{version}")
        
        return True
    
    def verify_pypi_package(self, version: str, test_pypi: bool = False) -> bool:
        """Verify the package is available on PyPI."""
        print(f"\nVerifying PyPI package availability...")
        
        package_name = "@bobmatnyc/claude-mpm" if test_pypi else "claude-mpm"
        index_url = "https://test.pypi.org/simple/" if test_pypi else "https://pypi.org/simple/"
        
        # Wait a bit for PyPI to update
        time.sleep(5)
        
        # Try to fetch package info
        cmd = ["pip", "index", "versions", package_name]
        if test_pypi:
            cmd.extend(["--index-url", index_url])
        
        result = self.run_command(cmd, check=False)
        if result.returncode == 0 and version in result.stdout:
            print(f"✓ Version {version} is available on {'TestPyPI' if test_pypi else 'PyPI'}")
            return True
        else:
            print(f"⚠ Could not verify version {version} on {'TestPyPI' if test_pypi else 'PyPI'}")
            print("  This might be normal - PyPI can take a few minutes to update")
            return True  # Don't fail the release for this
    
    def verify_npm_package(self, version: str) -> bool:
        """Verify the package is available on npm."""
        print(f"\nVerifying npm package availability...")
        
        # Wait a bit for npm to update
        time.sleep(5)
        
        result = self.run_command(["npm", "view", "@bobmatnyc/claude-mpm", "version"], check=False)
        if result.returncode == 0 and version in result.stdout:
            print(f"✓ Version {version} is available on npm")
            return True
        else:
            print(f"⚠ Could not verify version {version} on npm")
            print("  This might be normal - npm can take a few minutes to update")
            return True  # Don't fail the release for this
    
    def push_to_git(self) -> bool:
        """Push commits and tags to git."""
        print("\nPushing to git...")
        
        # Push commits
        result = self.run_command(["git", "push", "origin", "main"], check=False)
        if result.returncode != 0:
            print("ERROR: Failed to push commits")
            return False
        
        # Push tags
        result = self.run_command(["git", "push", "origin", "--tags"], check=False)
        if result.returncode != 0:
            print("ERROR: Failed to push tags")
            return False
            
        print("Successfully pushed commits and tags")
        return True
    
    def run_release(self, bump_type: str, test_pypi: bool = False) -> bool:
        """Run the complete release process."""
        print(f"Starting release process (bump: {bump_type}, dry-run: {self.dry_run})")
        print("=" * 60)
        
        # Pre-release checks
        print("\n📋 Running pre-release checks...")
        if not self.check_working_directory():
            return False
        if not self.check_branch():
            return False
        if not self.run_tests():
            return False
        
        # Get current version for reference
        old_version = self.get_current_version()
        print(f"\nCurrent version: {old_version}")
        
        # Update version
        print("\n📝 Updating version...")
        new_version = self.update_version(bump_type)
        
        # Update package.json
        if not self.update_package_json(new_version):
            return False
        
        # Push changes to git
        if not self.dry_run:
            if not self.push_to_git():
                return False
        
        # Build packages
        print("\n🔨 Building packages...")
        if not self.build_python_package():
            return False
        
        # Publish packages
        if not self.dry_run:
            print("\n📦 Publishing packages...")
            
            # Confirm before publishing
            response = input(f"\nReady to publish version {new_version}. Continue? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted by user")
                return False
            
            # Publish to PyPI
            if not self.publish_to_pypi(test_pypi):
                return False
            
            # Publish to npm
            if not self.publish_to_npm():
                print("WARNING: npm publish failed, but continuing...")
            
            # Create GitHub release
            if not self.create_github_release(new_version):
                print("WARNING: GitHub release creation failed, but continuing...")
            
            # Verify packages
            print("\n✅ Verifying packages...")
            self.verify_pypi_package(new_version, test_pypi)
            self.verify_npm_package(new_version)
        
        # Success!
        print("\n" + "=" * 60)
        print(f"🎉 Release {new_version} completed successfully!")
        print("\nNext steps:")
        if self.dry_run:
            print("  - Review the dry-run output")
            print("  - Run without --dry-run to perform actual release")
        else:
            print(f"  - Check PyPI: https://pypi.org/project/claude-mpm/{new_version}/")
            print(f"  - Check npm: https://www.npmjs.com/package/@bobmatnyc/claude-mpm/v/{new_version}")
            print(f"  - Check GitHub: https://github.com/bobmatnyc/claude-mpm/releases/tag/v{new_version}")
            print("  - Test installation: pip install claude-mpm==" + new_version)
            print("  - Test installation: npm install @bobmatnyc/claude-mpm@" + new_version)
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified release script for Claude MPM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run for patch release
  %(prog)s patch --dry-run
  
  # Release a minor version
  %(prog)s minor
  
  # Major release to TestPyPI first
  %(prog)s major --test-pypi
  
  # Skip tests for emergency patch
  %(prog)s patch --skip-tests
        """
    )
    
    parser.add_argument(
        "bump_type",
        choices=["patch", "minor", "major"],
        help="Type of version bump to perform"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes"
    )
    
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests (not recommended)"
    )
    
    parser.add_argument(
        "--test-pypi",
        action="store_true",
        help="Publish to TestPyPI instead of PyPI"
    )
    
    args = parser.parse_args()
    
    # Create release manager and run release
    manager = ReleaseManager(
        dry_run=args.dry_run,
        skip_tests=args.skip_tests
    )
    
    success = manager.run_release(
        bump_type=args.bump_type,
        test_pypi=args.test_pypi
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()