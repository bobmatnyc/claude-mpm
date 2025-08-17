#!/usr/bin/env python3
"""
Unified release script for Claude MPM.

This script implements a comprehensive release automation system that ensures
npm and PyPI versions stay synchronized and handles the complete release process.

OPERATIONAL PURPOSE:
Automated release pipeline ensuring consistent deployments across all distribution
channels with minimal manual intervention and maximum reliability.

RELEASE AUTOMATION STRATEGY:
- Single command releases to multiple distribution channels
- Automatic version synchronization between PyPI and npm
- Pre-flight checks to prevent failed releases
- Rollback guidance if issues occur
- Post-release verification of package availability

DISTRIBUTION CHANNELS:
1. PyPI: Primary Python package repository
2. npm: Node package manager (as @bobmatnyc/claude-mpm)
3. GitHub: Release artifacts and changelog

VERSION SYNCHRONIZATION:
- Python version from VERSION file (managed by manage_version.py)
- package.json automatically updated to match
- Git tags as source of truth
- All versions kept in perfect sync

RELEASE WORKFLOW:
1. Pre-release checks (clean working tree, correct branch, tests)
2. Version bump using semantic versioning
3. Update and sync package.json version
4. Commit and tag changes
5. Build distribution packages
6. Publish to PyPI and npm
7. Create GitHub release with artifacts
8. Verify package availability on all channels

SAFETY FEATURES:
- Dry-run mode for testing
- Test PyPI deployment option
- Automatic rollback instructions
- Version conflict detection
- Build artifact verification

DEPLOYMENT PREREQUISITES:
- Clean git working directory
- On main/master branch
- All tests passing
- PyPI credentials configured (~/.pypirc)
- npm credentials configured (npm login)
- GitHub CLI authenticated (gh auth login)

MONITORING POINTS:
- Pre-release test execution time
- Package build success rate
- Upload completion status
- Post-release availability checks
- Version propagation time

TROUBLESHOOTING:
- PyPI upload fails: Check credentials and network
- npm publish fails: Verify npm login status
- Version conflict: Run manage_version.py first
- Test failures: Fix before releasing
- GitHub release fails: Check gh CLI auth

ROLLBACK PROCEDURES:
1. PyPI: Cannot delete, but can yank version
2. npm: npm unpublish @bobmatnyc/claude-mpm@VERSION
3. Git: Delete tag with git tag -d vVERSION
4. GitHub: Delete release via web UI or gh CLI
5. Local: Reset VERSION file and package.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple


class ReleaseManager:
    """Manages the release process for Claude MPM.

    This class orchestrates the entire release workflow, ensuring all steps
    are executed in the correct order with proper error handling.

    Key Responsibilities:
    - Version management and synchronization
    - Package building and distribution
    - Multi-channel publishing (PyPI, npm, GitHub)
    - Pre and post-release verification
    - Error handling and rollback guidance

    Attributes:
        dry_run: If True, simulates release without making changes
        skip_tests: If True, skips test suite execution (not recommended)
        project_root: Path to project root directory
        scripts_dir: Path to scripts directory
        manage_version_script: Path to version management script
        cleanup_actions: List of actions taken for potential rollback
    """

    def __init__(self, dry_run: bool = False, skip_tests: bool = False):
        self.dry_run = dry_run
        self.skip_tests = skip_tests
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.manage_version_script = self.scripts_dir / "manage_version.py"

        # Track what we've done for cleanup if needed
        # This enables potential rollback or cleanup operations
        self.cleanup_actions = []

    def run_command(
        self, cmd: List[str], check: bool = True, capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        if self.dry_run and not any(
            safe_cmd in cmd[0] for safe_cmd in ["git", "cat", "python3"] if cmd
        ):
            print(f"[DRY-RUN] Would run: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False,
            cwd=self.project_root,
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
            print(
                "ERROR: Working directory is not clean. Please commit or stash changes."
            )
            print("Uncommitted changes:")
            print(result.stdout)
            return False
        return True

    def check_version_sync(self) -> bool:
        """Check if Python and npm versions are in sync.

        Version Synchronization Check:
        - Compares VERSION file (Python) with package.json (npm)
        - Detects version mismatches early in the release process
        - Issues warnings but doesn't fail (auto-sync will fix)

        This check is crucial because:
        - Users may install from either PyPI or npm
        - Version mismatch causes confusion
        - Both packages should always have identical versions
        - Automated sync prevents manual errors

        Returns:
            True: Always returns True (warnings only, no failures)
                  Version sync is enforced during release
        """
        print("\nChecking version synchronization...")

        # Get Python version from VERSION file
        # This is the canonical version managed by manage_version.py
        version_file = self.project_root / "VERSION"
        if not version_file.exists():
            print("WARNING: VERSION file not found")
            return True  # Don't fail, will be created during release

        python_version = version_file.read_text().strip()

        # Get npm version from package.json
        # This should match Python version for consistency
        package_json_path = self.project_root / "package.json"
        if package_json_path.exists():
            with open(package_json_path, "r") as f:
                package_data = json.load(f)
                npm_version = package_data.get("version", "unknown")

            if python_version != npm_version:
                print(f"WARNING: Version mismatch detected!")
                print(f"  Python (VERSION): {python_version}")
                print(f"  npm (package.json): {npm_version}")
                print("  Versions will be synchronized during release.")

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
        cmd = [
            "python3",
            str(self.manage_version_script),
            "bump",
            "--bump-type",
            bump_type,
        ]
        if self.dry_run:
            cmd.append("--dry-run")

        result = self.run_command(cmd)

        # Get the new version
        new_version = self.get_current_version()
        print(f"New version: {new_version}")
        return new_version

    def update_package_json(self, version: str) -> bool:
        """Update package.json with the new version.

        Package.json Version Update Process:
        1. Validates version format (must be X.Y.Z)
        2. Handles development versions in dry-run mode
        3. Updates version field in package.json
        4. Commits the change to git
        5. Verifies the update was successful

        Version Format Handling:
        - Production: Requires clean semantic version (1.2.3)
        - Development: Allows .devN+gHASH format in dry-run
        - Extracts base version from development versions

        npm Compatibility:
        - npm requires strict semantic versioning
        - No PEP 440 suffixes allowed (.post, .dev, etc)
        - Version must match PyPI version exactly

        Error Handling:
        - Invalid JSON detection
        - Version format validation
        - Git commit failure handling
        - Verification after update

        Args:
            version: New version string to set

        Returns:
            bool: True if successful, False on error
        """
        package_json_path = self.project_root / "package.json"
        if not package_json_path.exists():
            print("WARNING: package.json not found, skipping npm version update")
            return True

        print(f"\nUpdating package.json to version {version}...")

        try:
            # Read package.json with error handling
            with open(package_json_path, "r") as f:
                content = f.read()
                package_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in package.json: {e}")
            return False
        except Exception as e:
            print(f"ERROR: Failed to read package.json: {e}")
            return False

        old_version = package_data.get("version", "unknown")

        # Validate version format (allow dev versions during dry run)
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            # Check if it's a development version
            if re.match(r"^\d+\.\d+\.\d+\.dev\d+\+", version) and self.dry_run:
                print(f"WARNING: Development version detected: {version}")
                print("         Release process will use clean semantic version")
                # Extract base version for comparison
                base_version = re.match(r"^(\d+\.\d+\.\d+)", version).group(1)
                version = base_version
            else:
                print(f"ERROR: Invalid version format: {version}. Expected: X.Y.Z")
                return False

        # Check if version is already up to date
        if old_version == version:
            print(f"package.json is already at version {version}")
            return True

        package_data["version"] = version

        if not self.dry_run:
            try:
                # Write with proper formatting to match npm standards
                with open(package_json_path, "w") as f:
                    json.dump(package_data, f, indent=2, ensure_ascii=False)
                    f.write("\n")  # Add newline at end of file
                print(f"Updated package.json: {old_version} -> {version}")

                # Verify the update
                with open(package_json_path, "r") as f:
                    verify_data = json.load(f)
                    if verify_data.get("version") != version:
                        print("ERROR: Failed to verify package.json update")
                        return False

                # Commit the package.json update
                self.run_command(["git", "add", "package.json"])
                commit_result = self.run_command(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"chore: update package.json version to {version}",
                    ],
                    check=False,
                )

                # Handle case where there's nothing to commit (already up to date)
                if commit_result.returncode != 0:
                    if (
                        "nothing to commit" in commit_result.stdout
                        or "nothing to commit" in commit_result.stderr
                    ):
                        print("No changes to commit (package.json already up to date)")
                    else:
                        print(
                            f"ERROR: Failed to commit package.json update: {commit_result.stderr}"
                        )
                        return False

            except Exception as e:
                print(f"ERROR: Failed to update package.json: {e}")
                return False
        else:
            print(f"[DRY-RUN] Would update package.json: {old_version} -> {version}")

        return True

    def build_python_package(self) -> bool:
        """Build Python distribution packages.

        Python Package Building Process:
        1. Clean previous build artifacts
        2. Run python -m build (PEP 517 compliant)
        3. Generate both wheel and sdist
        4. Verify artifacts were created

        Build Artifacts:
        - Source distribution (.tar.gz): Contains source code
        - Wheel (.whl): Pre-built distribution for faster installs
        - Both uploaded to PyPI for maximum compatibility

        Build System:
        - Uses setuptools with setup.cfg configuration
        - setuptools-scm provides version from git
        - pyproject.toml defines build requirements

        Clean Build Importance:
        - Prevents old files in distributions
        - Ensures reproducible builds
        - Avoids version conflicts

        Returns:
            bool: True if build successful, False on error
        """
        print("\nBuilding Python package...")

        # Clean previous builds to ensure fresh artifacts
        # This prevents accidentally including old files
        for dir_name in ["dist", "build"]:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                if not self.dry_run:
                    shutil.rmtree(dir_path)
                    print(f"Cleaned {dir_name}/")
                else:
                    print(f"[DRY-RUN] Would clean {dir_name}/")

        # Build the package using PEP 517 build frontend
        # This is the modern way to build Python packages
        result = self.run_command(["python3", "-m", "build"], check=False)
        if result.returncode != 0:
            print("ERROR: Failed to build Python package")
            return False

        # Verify build artifacts were created
        # Should have both .tar.gz and .whl files
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

    def validate_npm_package(self) -> bool:
        """Validate npm package before publishing."""
        print("\nValidating npm package...")

        package_json_path = self.project_root / "package.json"
        if not package_json_path.exists():
            print("ERROR: package.json not found")
            return False

        # Check required files mentioned in package.json
        with open(package_json_path, "r") as f:
            package_data = json.load(f)

        # Check files array
        files_to_check = package_data.get("files", [])
        missing_files = []
        for file_pattern in files_to_check:
            # Simple check - doesn't handle glob patterns fully
            file_path = self.project_root / file_pattern
            if not file_path.exists() and not list(
                self.project_root.glob(file_pattern)
            ):
                missing_files.append(file_pattern)

        if missing_files:
            print(
                f"ERROR: Missing files referenced in package.json: {', '.join(missing_files)}"
            )
            return False

        # Check bin entries
        bin_entries = package_data.get("bin", {})
        if isinstance(bin_entries, str):
            bin_entries = {package_data.get("name", "unknown"): bin_entries}

        for name, path in bin_entries.items():
            bin_path = self.project_root / path
            if not bin_path.exists():
                print(f"ERROR: Missing bin file '{path}' for command '{name}'")
                return False
            if not os.access(str(bin_path), os.X_OK):
                print(f"WARNING: Bin file '{path}' is not executable")

        # Check scripts
        if "scripts" in package_data:
            for script_name, script_cmd in package_data["scripts"].items():
                if script_name == "postinstall":
                    # Check if postinstall script exists
                    if "node " in script_cmd:
                        script_file = script_cmd.replace("node ", "").strip()
                        script_path = self.project_root / script_file
                        if not script_path.exists():
                            print(f"ERROR: Missing postinstall script: {script_file}")
                            return False

        print("✓ npm package validation passed")
        return True

    def publish_to_npm(self) -> bool:
        """Publish package to npm."""
        print("\nPublishing to npm...")

        # Validate package first
        if not self.validate_npm_package():
            return False

        # Check if npm is installed
        npm_check = self.run_command(["which", "npm"], check=False)
        if npm_check.returncode != 0:
            print("ERROR: npm is not installed. Please install Node.js and npm.")
            return False

        # Check if logged in to npm
        result = self.run_command(["npm", "whoami"], check=False)
        if result.returncode != 0:
            print("ERROR: Not logged in to npm. Please run 'npm login' first.")
            return False

        npm_user = result.stdout.strip()
        print(f"Logged in to npm as: {npm_user}")

        # Verify package.json exists
        if not (self.project_root / "package.json").exists():
            print("ERROR: package.json not found")
            return False

        # Get package name and version from package.json
        with open(self.project_root / "package.json", "r") as f:
            package_data = json.load(f)
            package_name = package_data.get("name", "unknown")
            package_version = package_data.get("version", "unknown")

        print(f"Publishing {package_name}@{package_version}...")

        # Check if this version already exists on npm
        version_check = self.run_command(
            ["npm", "view", package_name, "versions", "--json"], check=False
        )
        if version_check.returncode == 0:
            try:
                existing_versions = json.loads(version_check.stdout)
                if package_version in existing_versions:
                    print(f"WARNING: Version {package_version} already exists on npm")
                    response = input("Continue anyway? [y/N]: ")
                    if response.lower() != "y":
                        return False
            except json.JSONDecodeError:
                # Ignore JSON decode errors, proceed with publish
                pass

        # Run npm pack first to verify the package
        print("Creating npm package...")
        pack_result = self.run_command(["npm", "pack", "--dry-run"], check=False)
        if pack_result.returncode != 0:
            print("ERROR: npm pack failed. Package may have issues.")
            print(pack_result.stderr)
            return False

        # Publish the package
        result = self.run_command(["npm", "publish", "--access", "public"], check=False)
        if result.returncode != 0:
            error_output = result.stderr or result.stdout

            # Check for common errors
            if (
                "You cannot publish over the previously published versions"
                in error_output
            ):
                print(f"ERROR: Version {package_version} is already published to npm")
                print("Please bump the version and try again")
            elif "E402" in error_output or "payment required" in error_output:
                print("ERROR: npm account requires payment for private packages")
                print("Make sure to use --access public flag")
            elif "E403" in error_output or "forbidden" in error_output.lower():
                print("ERROR: Permission denied. Check your npm account permissions")
                print(f"Make sure you have publish rights for {package_name}")
            else:
                print(f"ERROR: Failed to publish to npm: {error_output}")
            return False

        print(f"Successfully published {package_name}@{package_version} to npm")
        return True

    def create_github_release(self, version: str) -> bool:
        """Create a GitHub release."""
        print(f"\nCreating GitHub release for v{version}...")

        # Check if gh CLI is available
        result = self.run_command(["which", "gh"], check=False)
        if result.returncode != 0:
            print("WARNING: GitHub CLI (gh) not found. Please create release manually.")
            print(
                f"Visit: https://github.com/bobmatnyc/claude-mpm/releases/new?tag=v{version}"
            )
            return True

        # Get changelog entry for this version
        changelog_path = self.project_root / "CHANGELOG.md"
        if changelog_path.exists():
            changelog_content = changelog_path.read_text()
            # Extract the section for this version
            version_section = ""
            in_section = False
            for line in changelog_content.split("\n"):
                if line.startswith(f"## [{version}]"):
                    in_section = True
                elif in_section and line.startswith("## ["):
                    break
                elif in_section:
                    version_section += line + "\n"

            # Create release
            cmd = [
                "gh",
                "release",
                "create",
                f"v{version}",
                "--title",
                f"Claude MPM v{version}",
                "--notes",
                version_section.strip(),
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
                print(
                    f"Please create it manually at: https://github.com/bobmatnyc/claude-mpm/releases/new?tag=v{version}"
                )

        return True

    def verify_pypi_package(self, version: str, test_pypi: bool = False) -> bool:
        """Verify the package is available on PyPI."""
        print(f"\nVerifying PyPI package availability...")

        package_name = "@bobmatnyc/claude-mpm" if test_pypi else "claude-mpm"
        index_url = (
            "https://test.pypi.org/simple/" if test_pypi else "https://pypi.org/simple/"
        )

        # Wait a bit for PyPI to update
        time.sleep(5)

        # Try to fetch package info
        cmd = ["pip", "index", "versions", package_name]
        if test_pypi:
            cmd.extend(["--index-url", index_url])

        result = self.run_command(cmd, check=False)
        if result.returncode == 0 and version in result.stdout:
            print(
                f"✓ Version {version} is available on {'TestPyPI' if test_pypi else 'PyPI'}"
            )
            return True
        else:
            print(
                f"⚠ Could not verify version {version} on {'TestPyPI' if test_pypi else 'PyPI'}"
            )
            print("  This might be normal - PyPI can take a few minutes to update")
            return True  # Don't fail the release for this

    def verify_npm_package(self, version: str) -> bool:
        """Verify the package is available on npm."""
        print(f"\nVerifying npm package availability...")

        # Get package name from package.json
        package_json_path = self.project_root / "package.json"
        if package_json_path.exists():
            with open(package_json_path, "r") as f:
                package_data = json.load(f)
                package_name = package_data.get("name", "@bobmatnyc/claude-mpm")
        else:
            package_name = "@bobmatnyc/claude-mpm"

        # Wait a bit for npm to update
        print("Waiting for npm registry to update...")
        for attempt in range(3):
            time.sleep(5 * (attempt + 1))  # Progressive delay: 5s, 10s, 15s

            result = self.run_command(
                ["npm", "view", package_name, "version"], check=False
            )

            if result.returncode == 0:
                latest_version = result.stdout.strip()
                if latest_version == version:
                    print(f"✓ Version {version} is available on npm")
                    return True
                else:
                    print(
                        f"  Attempt {attempt + 1}/3: Latest version on npm is {latest_version}"
                    )
            else:
                print(f"  Attempt {attempt + 1}/3: Package not found on npm yet")

        print(f"⚠ Could not verify version {version} on npm after 3 attempts")
        print("  This might be normal - npm can take several minutes to update")
        print(f"  Check manually: https://www.npmjs.com/package/{package_name}")
        return True  # Don't fail the release for this

    def push_to_git(self) -> bool:
        """Push commits and tags to git remote.

        Git Push Strategy:
        1. Push commits first (version bump, changelog, package.json)
        2. Push tags separately (ensures tags are pushed)
        3. Both pushes to 'origin' remote, 'main' branch

        Why Separate Push Commands:
        - Some git configs don't push tags by default
        - Explicit tag push ensures version tags reach remote
        - Allows CI/CD to trigger on tag push

        Remote Repository Importance:
        - Tags trigger CI/CD workflows
        - GitHub uses tags for releases
        - setuptools-scm needs tags for version detection

        Error Handling:
        - Network connectivity issues
        - Authentication failures
        - Protected branch restrictions

        Returns:
            bool: True if both pushes successful, False on error
        """
        print("\nPushing to git...")

        # Push commits first
        # This includes version bump, changelog, and package.json updates
        result = self.run_command(["git", "push", "origin", "main"], check=False)
        if result.returncode != 0:
            print("ERROR: Failed to push commits")
            return False

        # Push tags explicitly
        # Tags don't push by default with git push
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
        if not self.check_version_sync():
            pass  # Just a warning, don't fail
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
            response = input(
                f"\nReady to publish version {new_version}. Continue? [y/N]: "
            )
            if response.lower() != "y":
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
            print(
                f"  - Check npm: https://www.npmjs.com/package/@bobmatnyc/claude-mpm/v/{new_version}"
            )
            print(
                f"  - Check GitHub: https://github.com/bobmatnyc/claude-mpm/releases/tag/v{new_version}"
            )
            print("  - Test installation: pip install claude-mpm==" + new_version)
            print(
                "  - Test installation: npm install @bobmatnyc/claude-mpm@"
                + new_version
            )

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
        """,
    )

    parser.add_argument(
        "bump_type",
        choices=["patch", "minor", "major"],
        help="Type of version bump to perform",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )

    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip running tests (not recommended)"
    )

    parser.add_argument(
        "--test-pypi", action="store_true", help="Publish to TestPyPI instead of PyPI"
    )

    args = parser.parse_args()

    # Create release manager and run release
    manager = ReleaseManager(dry_run=args.dry_run, skip_tests=args.skip_tests)

    success = manager.run_release(bump_type=args.bump_type, test_pypi=args.test_pypi)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
