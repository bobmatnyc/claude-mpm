#!/usr/bin/env python3
"""
Test script to verify the ConfigDirName enum implementation.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config_paths import ConfigPaths, ConfigDirName, CONFIG_DIR_NAME


def test_enum_implementation():
    """Test that the enum is properly implemented and used."""
    print("Testing ConfigDirName enum implementation...")
    
    # Test 1: Enum value
    assert ConfigDirName.CLAUDE_MPM.value == ".claude-mpm", "Enum value incorrect"
    print("✓ Enum value is correct")
    
    # Test 2: ConfigPaths uses enum
    assert ConfigPaths.CONFIG_DIR == ConfigDirName.CLAUDE_MPM.value, "ConfigPaths not using enum"
    print("✓ ConfigPaths.CONFIG_DIR uses enum value")
    
    # Test 3: Backward compatibility
    assert CONFIG_DIR_NAME == ConfigDirName.CLAUDE_MPM.value, "CONFIG_DIR_NAME not compatible"
    print("✓ CONFIG_DIR_NAME maintains backward compatibility")
    
    # Test 4: Path construction
    user_config = ConfigPaths.get_user_config_dir()
    expected = Path.home() / ConfigDirName.CLAUDE_MPM.value
    assert user_config == expected, f"Path construction failed: {user_config} != {expected}"
    print("✓ Path construction with enum works")
    
    # Test 5: All path methods work
    paths_to_test = [
        ("get_user_config_dir", ConfigPaths.get_user_config_dir()),
        ("get_project_config_dir", ConfigPaths.get_project_config_dir()),
        ("get_user_agents_dir", ConfigPaths.get_user_agents_dir()),
        ("get_project_agents_dir", ConfigPaths.get_project_agents_dir()),
        ("get_tracking_dir", ConfigPaths.get_tracking_dir()),
        ("get_backups_dir", ConfigPaths.get_backups_dir()),
        ("get_memories_dir", ConfigPaths.get_memories_dir()),
        ("get_responses_dir", ConfigPaths.get_responses_dir()),
    ]
    
    for method_name, path in paths_to_test:
        assert ConfigDirName.CLAUDE_MPM.value in str(path), f"{method_name} not using enum value"
    print("✓ All path methods use the enum value")
    
    print("\n✅ All tests passed! The enum implementation is working correctly.")


def test_parent_directory_manager_removed():
    """Test that parent_directory_manager has been successfully removed."""
    print("\nTesting parent_directory_manager removal...")
    
    # Test 1: Module doesn't exist
    try:
        from claude_mpm.services.parent_directory_manager import ParentDirectoryManager
        print("✗ parent_directory_manager module still exists!")
        return False
    except ImportError:
        print("✓ parent_directory_manager module successfully removed")
    
    # Test 2: Not accessible from services
    try:
        from claude_mpm import services
        if hasattr(services, 'ParentDirectoryManager'):
            print("✗ ParentDirectoryManager still accessible from services")
            return False
        print("✓ ParentDirectoryManager not accessible from services")
    except Exception as e:
        print(f"Warning checking services: {e}")
    
    # Test 3: Directory doesn't exist
    parent_dir_path = Path(__file__).parent.parent / "src" / "claude_mpm" / "services" / "parent_directory_manager"
    if parent_dir_path.exists():
        print(f"✗ Directory still exists: {parent_dir_path}")
        return False
    print("✓ parent_directory_manager directory removed")
    
    print("\n✅ parent_directory_manager successfully removed!")
    return True


if __name__ == "__main__":
    try:
        test_enum_implementation()
        test_parent_directory_manager_removed()
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)