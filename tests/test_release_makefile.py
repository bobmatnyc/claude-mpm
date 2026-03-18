#!/usr/bin/env python3
"""
Test script for the new Make-based release system.

This script validates that the Makefile targets are properly defined
and can be executed without errors.
"""

import subprocess
import sys
from pathlib import Path


def run_subcommand(cmd, capture_output=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def test_makefile_targets():
    """Test that all release targets are defined in the Makefile."""
    print("🔍 Testing Makefile release targets...")

    # Expected release targets

    # Check if targets are defined
    success, stdout, stderr = run_subcommand("make -n help")
    if not success:
        print(f"❌ Failed to run 'make help': {stderr}")
        return False

    # Check if release targets appear in help
    success, stdout, stderr = run_subcommand("make help | grep release")
    if success and stdout:
        print("✅ Found release targets in help output")
        print(f"   Targets: {len(stdout.strip().split(chr(10)))} release targets found")
    else:
        print("⚠️  No release targets found in help output")

    # Test dry run of release-check (safest to test)
    print("\n🧪 Testing release-check target...")
    success, stdout, stderr = run_subcommand("make -n release-check")
    if success:
        print("✅ release-check target is properly defined")
    else:
        print(f"❌ release-check target failed: {stderr}")
        return False

    # Test dry run of release-help
    print("\n📖 Testing release-help target...")
    success, stdout, stderr = run_subcommand("make -n release-help")
    if success:
        print("✅ release-help target is properly defined")
    else:
        print(f"❌ release-help target failed: {stderr}")
        return False

    return True


def test_prerequisites():
    """Test that required tools are available."""
    print("\n🔧 Testing prerequisites...")

    tools = [
        ("make", "Make build tool"),
        ("git", "Git version control"),
        ("python", "Python interpreter"),
    ]

    optional_tools = [
        ("cz", "Commitizen"),
        ("gh", "GitHub CLI"),
        ("uv", "Python package installer and publisher"),
        ("npm", "Node.js package manager"),
    ]

    all_good = True

    for tool, description in tools:
        success, _, _ = run_subcommand(f"which {tool}")
        if success:
            print(f"✅ {tool} - {description}")
        else:
            print(f"❌ {tool} - {description} (REQUIRED)")
            all_good = False

    for tool, description in optional_tools:
        success, _, _ = run_subcommand(f"which {tool}")
        if success:
            print(f"✅ {tool} - {description}")
        else:
            print(f"⚠️  {tool} - {description} (optional)")

    return all_good


def test_version_files():
    """Test that version files exist and are readable."""
    print("\n📄 Testing version files...")

    project_root = Path(__file__).parent.parent
    version_files = [
        project_root / "VERSION",
        project_root / "src" / "claude_mpm" / "VERSION",
        project_root / "package.json",
        project_root / "pyproject.toml",
    ]

    all_good = True

    for file_path in version_files:
        if file_path.exists():
            try:
                content = file_path.read_text().strip()
                if content:
                    print(f"✅ {file_path.name} - exists and readable")
                else:
                    print(f"⚠️  {file_path.name} - exists but empty")
            except Exception as e:
                print(f"❌ {file_path.name} - exists but not readable: {e}")
                all_good = False
        else:
            print(f"❌ {file_path.name} - missing")
            all_good = False

    return all_good


def main():
    """Main test function."""
    print("Claude MPM Release System Test")
    print("=" * 40)

    tests = [
        ("Makefile Targets", test_makefile_targets),
        ("Prerequisites", test_prerequisites),
        ("Version Files", test_version_files),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 40)
    print("Test Summary")
    print("=" * 40)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n🎉 All tests passed! The Make-based release system is ready to use.")
        print("\nNext steps:")
        print("  make release-help    # Show release help")
        print("  make release-dry-run # Preview a release")
        print("  make release-patch   # Create a patch release")
        return True
    print("\n⚠️  Some tests failed. Please address the issues above.")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
