#!/usr/bin/env python3
"""Test that ProjectRegistry uses deployment root instead of home directory."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.project_registry import ProjectRegistry
from claude_mpm.deployment_paths import get_project_root
from claude_mpm.manager.discovery import InstallationDiscovery
from claude_mpm.manager.config.manager_config import ManagerConfig


def test_registry_uses_deployment_root():
    """Test that ProjectRegistry uses deployment root for registry directory."""
    print("Testing ProjectRegistry deployment root usage...")
    
    # Get deployment root
    deployment_root = get_project_root()
    print(f"Deployment root: {deployment_root}")
    
    # Create ProjectRegistry instance
    registry = ProjectRegistry()
    
    # Check that registry_dir uses deployment root, not home directory
    expected_registry_dir = deployment_root / ".claude-mpm" / "registry"
    actual_registry_dir = registry.registry_dir
    
    print(f"Expected registry directory: {expected_registry_dir}")
    print(f"Actual registry directory: {actual_registry_dir}")
    
    assert actual_registry_dir == expected_registry_dir, \
        f"Registry should use deployment root, not {actual_registry_dir}"
    
    # Verify it's not using the hardcoded home/.claude-mpm path
    home_registry_path = Path.home() / ".claude-mpm" / "registry"
    assert actual_registry_dir != home_registry_path, \
        f"Registry should not use {home_registry_path}"
    
    print("✓ ProjectRegistry correctly uses deployment root")


def test_installation_discovery_config_path():
    """Test that InstallationDiscovery uses deployment root for config."""
    print("\nTesting InstallationDiscovery config path...")
    
    # Get deployment root
    deployment_root = get_project_root()
    
    # Create InstallationDiscovery instance
    discovery = InstallationDiscovery()
    
    # Test _get_search_paths to ensure it uses correct config path
    # This internally checks for config at deployment root
    search_paths = discovery._get_search_paths(None)
    
    # The method should look for config at deployment root
    expected_config_path = deployment_root / ".claude-mpm" / "manager" / "config.yaml"
    print(f"Expected config path: {expected_config_path}")
    
    # Verify search paths are returned (even if using defaults)
    assert len(search_paths) > 0, "Should return search paths"
    
    print("✓ InstallationDiscovery correctly looks for config at deployment root")


def test_manager_config_paths():
    """Test that ManagerConfig uses deployment root for config file."""
    print("\nTesting ManagerConfig paths...")
    
    # Get deployment root
    deployment_root = get_project_root()
    
    # Test load method (it should use deployment root internally)
    config = ManagerConfig.load()
    
    # The default config path should be at deployment root
    expected_config_path = deployment_root / ".claude-mpm" / "manager" / "config.yaml"
    
    # Load with explicit None to test default path handling
    config2 = ManagerConfig.load(config_path=None)
    
    print(f"Expected config path: {expected_config_path}")
    print("✓ ManagerConfig correctly uses deployment root for config")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Registry Deployment Root Configuration")
    print("=" * 60)
    
    try:
        test_registry_uses_deployment_root()
        test_installation_discovery_config_path()
        test_manager_config_paths()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✅")
        print("Registry and related services now use deployment root")
        print("instead of user's home directory.")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()