#!/usr/bin/env python3
"""Verify memory services reorganization is complete and working."""

import sys
from pathlib import Path
from typing import List, Tuple


def check_python_file(file_path: Path) -> List[Tuple[str, str]]:
    """Check a Python file for old import patterns."""
    issues = []

    # Skip verification scripts themselves
    if (
        "verify_memory_reorganization" in file_path.name
        or "update_memory_imports" in file_path.name
    ):
        return issues

    try:
        content = file_path.read_text()

        # Check for old import patterns that should have been updated
        # Using markers to avoid self-detection
        old_patterns = [
            (
                "from claude_mpm.services." + "memory_builder",
                "Should be: from claude_mpm.services.memory.builder",
            ),
            (
                "from claude_mpm.services." + "memory_router",
                "Should be: from claude_mpm.services.memory.router",
            ),
            (
                "from claude_mpm.services." + "memory_optimizer",
                "Should be: from claude_mpm.services.memory.optimizer",
            ),
            (
                "from claude_mpm.services." + "simple_cache_service",
                "Should be: from claude_mpm.services.memory.cache.simple_cache",
            ),
            (
                "from claude_mpm.services." + "shared_prompt_cache",
                "Should be: from claude_mpm.services.memory.cache.shared_prompt_cache",
            ),
        ]

        for pattern, suggestion in old_patterns:
            if pattern in content:
                issues.append(
                    (str(file_path), f"Found old import: {pattern}. {suggestion}")
                )

    except Exception:
        # Skip files that can't be read
        pass

    return issues


def verify_new_structure():
    """Verify the new folder structure exists."""
    project_root = Path(__file__).parent.parent
    memory_dir = project_root / "src" / "claude_mpm" / "services" / "memory"
    cache_dir = memory_dir / "cache"

    print("Verifying new folder structure...")

    # Check directories exist
    assert memory_dir.exists(), f"Memory directory not found: {memory_dir}"
    print(f"✓ Memory directory exists: {memory_dir}")

    assert cache_dir.exists(), f"Cache directory not found: {cache_dir}"
    print(f"✓ Cache directory exists: {cache_dir}")

    # Check files exist
    files_to_check = [
        (memory_dir / "__init__.py", "memory/__init__.py"),
        (memory_dir / "builder.py", "memory/builder.py"),
        (memory_dir / "router.py", "memory/router.py"),
        (memory_dir / "optimizer.py", "memory/optimizer.py"),
        (cache_dir / "__init__.py", "cache/__init__.py"),
        (cache_dir / "simple_cache.py", "cache/simple_cache.py"),
        (cache_dir / "shared_prompt_cache.py", "cache/shared_prompt_cache.py"),
    ]

    for file_path, name in files_to_check:
        assert file_path.exists(), f"File not found: {name}"
        print(f"✓ File exists: {name}")

    # Check old files don't exist
    old_files = [
        project_root / "src" / "claude_mpm" / "services" / "memory_builder.py",
        project_root / "src" / "claude_mpm" / "services" / "memory_router.py",
        project_root / "src" / "claude_mpm" / "services" / "memory_optimizer.py",
        project_root / "src" / "claude_mpm" / "services" / "simple_cache_service.py",
        project_root / "src" / "claude_mpm" / "services" / "shared_prompt_cache.py",
    ]

    for old_file in old_files:
        assert not old_file.exists(), f"Old file still exists: {old_file}"
    print("✓ Old files have been removed")


def check_all_imports():
    """Check all Python files for old import patterns."""
    project_root = Path(__file__).parent.parent

    print("\nChecking for old import patterns...")

    all_issues = []
    dirs_to_check = [
        project_root / "src",
        project_root / "tests",
        project_root / "scripts",
    ]

    for dir_path in dirs_to_check:
        if dir_path.exists():
            for py_file in dir_path.rglob("*.py"):
                issues = check_python_file(py_file)
                all_issues.extend(issues)

    if all_issues:
        print("⚠️ Found files with old import patterns:")
        for file_path, issue in all_issues:
            print(f"  - {file_path}: {issue}")
        return False
    print("✓ No old import patterns found")
    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Memory Services Reorganization Verification")
    print("=" * 60)

    try:
        # Verify structure
        verify_new_structure()

        # Check imports
        imports_ok = check_all_imports()

        print("\n" + "=" * 60)
        if imports_ok:
            print("✅ Reorganization verified successfully!")
            print("\nNew structure:")
            print("  src/claude_mpm/services/memory/")
            print("  ├── __init__.py")
            print("  ├── builder.py")
            print("  ├── router.py")
            print("  ├── optimizer.py")
            print("  └── cache/")
            print("      ├── __init__.py")
            print("      ├── simple_cache.py")
            print("      └── shared_prompt_cache.py")
        else:
            print("⚠️ Some issues found. Please review above.")
        print("=" * 60)

        return 0 if imports_ok else 1

    except AssertionError as e:
        print(f"\n❌ Verification failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
