#!/usr/bin/env python3
"""Test script for the centralized path management system."""

import sys
from pathlib import Path

# Test import with fallback
try:
    from claude_mpm.config.paths import paths, get_version
except ImportError:
    print("Initial import failed, trying with path setup...")
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from claude_mpm.config.paths import paths, get_version


def test_path_management():
    """Test all aspects of the centralized path management system."""
    print("=" * 60)
    print("Testing Centralized Path Management System")
    print("=" * 60)
    
    # Test 1: Basic path properties
    print("\n1. Testing Basic Path Properties:")
    print(f"   Project Root: {paths.project_root}")
    print(f"   Source Dir: {paths.src_dir}")
    print(f"   Claude MPM Dir: {paths.claude_mpm_dir}")
    
    # Verify paths exist
    assert paths.project_root.exists(), "Project root should exist"
    assert paths.src_dir.exists(), "Source directory should exist"
    assert paths.claude_mpm_dir.exists(), "Claude MPM directory should exist"
    print("   ✓ All basic paths exist")
    
    # Test 2: Core directories
    print("\n2. Testing Core Directories:")
    directories = {
        'agents_dir': paths.agents_dir,
        'services_dir': paths.services_dir,
        'hooks_dir': paths.hooks_dir,
        'config_dir': paths.config_dir,
        'cli_dir': paths.cli_dir,
        'core_dir': paths.core_dir,
    }
    
    for name, path in directories.items():
        exists = "✓" if path.exists() else "✗"
        print(f"   {exists} {name}: {path}")
    
    # Test 3: Project directories
    print("\n3. Testing Project Directories:")
    project_dirs = {
        'scripts_dir': paths.scripts_dir,
        'tests_dir': paths.tests_dir,
        'docs_dir': paths.docs_dir,
    }
    
    for name, path in project_dirs.items():
        exists = "✓" if path.exists() else "✗"
        print(f"   {exists} {name}: {path}")
    
    # Test 4: Special files
    print("\n4. Testing Special Files:")
    special_files = {
        'VERSION': paths.version_file,
        'pyproject.toml': paths.pyproject_file,
        'package.json': paths.package_json_file,
        'CLAUDE.md': paths.claude_md_file,
    }
    
    for name, path in special_files.items():
        exists = "✓" if path.exists() else "✗"
        print(f"   {exists} {name}: {path}")
    
    # Test 5: Version detection
    print("\n5. Testing Version Detection:")
    version = paths.get_version()
    print(f"   Version: {version}")
    assert version != 'unknown', "Version should be detected"
    print("   ✓ Version detected successfully")
    
    # Test 6: Path in sys.path
    print("\n6. Testing Python Path Management:")
    src_str = str(paths.src_dir)
    paths.ensure_in_path()
    assert src_str in sys.path, "Source directory should be in sys.path"
    print(f"   ✓ Source directory in sys.path")
    print(f"   Position in sys.path: {sys.path.index(src_str)}")
    
    # Test 7: Relative path calculation
    print("\n7. Testing Relative Path Calculation:")
    test_file = paths.agents_dir / "test.md"
    relative = paths.relative_to_project(test_file)
    print(f"   Absolute: {test_file}")
    print(f"   Relative: {relative}")
    assert str(relative).startswith("src/claude_mpm/agents"), "Relative path should be correct"
    print("   ✓ Relative path calculation works")
    
    # Test 8: Auto-created directories
    print("\n8. Testing Auto-Created Directories:")
    auto_dirs = {
        'logs_dir': paths.logs_dir,
        'temp_dir': paths.temp_dir,
        'claude_mpm_hidden': paths.claude_mpm_dir_hidden,
    }
    
    for name, path in auto_dirs.items():
        exists = path.exists()
        print(f"   {'✓' if exists else '✗'} {name}: {path}")
        assert exists, f"{name} should be auto-created"
    print("   ✓ All auto-created directories exist")
    
    # Test 9: Singleton pattern
    print("\n9. Testing Singleton Pattern:")
    from claude_mpm.config.paths import ClaudeMPMPaths
    paths2 = ClaudeMPMPaths()
    assert paths is paths2, "Should be the same instance"
    print("   ✓ Singleton pattern working correctly")
    
    # Test 10: String representations
    print("\n10. Testing String Representations:")
    print(f"   str(paths): {str(paths)}")
    print(f"   repr(paths):\n{repr(paths)}")
    
    # Test 11: Config path resolution
    print("\n11. Testing Config Path Resolution:")
    config_path = paths.resolve_config_path("test_config.yaml")
    print(f"   Resolved config path: {config_path}")
    assert config_path.parent == paths.config_dir, "Config should resolve to config directory"
    print("   ✓ Config path resolution works")
    
    # Test 12: Comparison with old patterns
    print("\n12. Comparing with Old Patterns:")
    
    # Old pattern simulation
    old_root = Path(__file__).parent.parent
    new_root = paths.project_root
    
    print(f"   Old pattern result: {old_root}")
    print(f"   New pattern result: {new_root}")
    assert old_root == new_root, "Both methods should yield the same result"
    print("   ✓ Compatible with old pattern results")
    
    print("\n" + "=" * 60)
    print("✅ All Path Management Tests Passed!")
    print("=" * 60)
    
    # Summary
    print("\n📊 Summary:")
    print(f"   - Project detected at: {paths.project_root}")
    print(f"   - Version: {version}")
    print(f"   - Total directories checked: {len(directories) + len(project_dirs) + len(auto_dirs)}")
    print(f"   - Total files checked: {len(special_files)}")
    print(f"   - All tests: PASSED")


if __name__ == "__main__":
    try:
        test_path_management()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)