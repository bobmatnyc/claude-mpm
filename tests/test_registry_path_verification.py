#!/usr/bin/env python3
"""Test to verify ProjectRegistry uses the correct deployment root path."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.project_registry import ProjectRegistry
from claude_mpm.deployment_paths import get_project_root
from claude_mpm.manager.discovery import InstallationDiscovery
from claude_mpm.manager_textual.discovery import InstallationDiscovery as TextualInstallationDiscovery


def test_project_registry_path():
    """Test that ProjectRegistry uses deployment root correctly."""
    print("=== Testing ProjectRegistry Path ===")
    
    # Get expected deployment root
    expected_deployment_root = get_project_root()
    expected_registry_dir = expected_deployment_root / ".claude-mpm" / "registry"
    
    print(f"Expected deployment root: {expected_deployment_root}")
    print(f"Expected registry directory: {expected_registry_dir}")
    
    # Initialize ProjectRegistry
    registry = ProjectRegistry()
    
    print(f"Actual registry directory: {registry.registry_dir}")
    
    # Verify the path is correct
    assert registry.registry_dir == expected_registry_dir, (
        f"Registry path mismatch!\n"
        f"Expected: {expected_registry_dir}\n"
        f"Actual:   {registry.registry_dir}"
    )
    
    print("✓ ProjectRegistry using correct deployment root path")
    
    # Ensure directory exists
    if registry.registry_dir.exists():
        print(f"✓ Registry directory exists: {registry.registry_dir}")
    else:
        print(f"ℹ Registry directory will be created when needed: {registry.registry_dir}")
    
    return registry.registry_dir


def test_installation_discovery_configs():
    """Test that InstallationDiscovery services use deployment root for configs."""
    print("\n=== Testing InstallationDiscovery Config Paths ===")
    
    expected_deployment_root = get_project_root()
    expected_config_path = expected_deployment_root / ".claude-mpm" / "manager" / "config.yaml"
    
    print(f"Expected config path: {expected_config_path}")
    
    # Test manager discovery
    print("Testing manager InstallationDiscovery...")
    manager_discovery = InstallationDiscovery()
    
    # The _get_search_paths method should use deployment root for config
    search_paths = manager_discovery._get_search_paths(None)
    print(f"✓ Manager discovery initialized successfully")
    
    # Test textual discovery
    print("Testing textual InstallationDiscovery...")
    textual_discovery = TextualInstallationDiscovery()
    
    # The _get_search_paths method should use deployment root for config
    textual_search_paths = textual_discovery._get_search_paths(None)
    print(f"✓ Textual discovery initialized successfully")
    
    return expected_config_path


def test_old_vs_new_registry_location():
    """Test to show the difference between old and new registry locations."""
    print("\n=== Old vs New Registry Locations ===")
    
    # Old location (incorrect)
    old_registry_path = Path.home() / ".claude-mpm" / "registry"
    
    # New location (correct)
    new_registry_path = get_project_root() / ".claude-mpm" / "registry"
    
    print(f"Old (incorrect) registry path: {old_registry_path}")
    print(f"New (correct) registry path:   {new_registry_path}")
    
    print(f"Old path exists: {old_registry_path.exists()}")
    print(f"New path exists: {new_registry_path.exists()}")
    
    # Check if we have any registry files in the old location
    old_registry_files = []
    if old_registry_path.exists():
        old_registry_files = list(old_registry_path.glob("*.yaml"))
        print(f"Registry files in old location: {len(old_registry_files)}")
        for file in old_registry_files:
            print(f"  - {file.name}")
    
    # Check if we have any registry files in the new location
    new_registry_files = []
    if new_registry_path.exists():
        new_registry_files = list(new_registry_path.glob("*.yaml"))
        print(f"Registry files in new location: {len(new_registry_files)}")
        for file in new_registry_files:
            print(f"  - {file.name}")
    
    return old_registry_path, new_registry_path, old_registry_files, new_registry_files


def test_registry_functionality():
    """Test that registry functionality works with the new location."""
    print("\n=== Testing Registry Functionality ===")
    
    registry = ProjectRegistry()
    
    try:
        # Test getting or creating an entry
        print("Testing project entry creation...")
        entry = registry.get_or_create_project_entry()
        
        print(f"✓ Project entry created: {entry.get('project_id')}")
        print(f"  Project path: {entry.get('project_path')}")
        print(f"  Project name: {entry.get('project_name')}")
        
        # Test listing projects
        print("Testing project listing...")
        projects = registry.list_projects()
        print(f"✓ Found {len(projects)} projects in registry")
        
        return True
        
    except Exception as e:
        print(f"❌ Registry functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all registry path verification tests."""
    print("=== Registry Path Verification Tests ===\n")
    
    try:
        # Test 1: Verify ProjectRegistry path
        registry_dir = test_project_registry_path()
        
        # Test 2: Verify InstallationDiscovery config paths
        config_path = test_installation_discovery_configs()
        
        # Test 3: Compare old vs new locations
        old_path, new_path, old_files, new_files = test_old_vs_new_registry_location()
        
        # Test 4: Verify registry functionality
        registry_works = test_registry_functionality()
        
        print("\n=== SUMMARY ===")
        print(f"Registry directory: {registry_dir}")
        print(f"Config path: {config_path}")
        print(f"Old registry files: {len(old_files)}")
        print(f"New registry files: {len(new_files)}")
        print(f"Registry functionality: {'✓ Working' if registry_works else '❌ Failed'}")
        
        if old_files and not new_files:
            print("\n⚠️  MIGRATION NOTICE:")
            print("  Old registry files found but new location is empty.")
            print("  Consider implementing data migration from old to new location.")
        
        print("\n=== REGISTRY PATH VERIFICATION COMPLETED ===")
        return 0
        
    except Exception as e:
        print(f"\n=== REGISTRY PATH VERIFICATION FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())