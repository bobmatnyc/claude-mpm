#!/usr/bin/env python3
"""Test registry migration and backward compatibility."""

import sys
import yaml
import shutil
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.project_registry import ProjectRegistry
from claude_mpm.deployment_paths import get_project_root


def create_test_migration_scenario():
    """Create a test scenario with old registry data."""
    print("=== Setting up Migration Test Scenario ===")
    
    # Create a temporary backup of existing registry files
    old_registry_path = Path.home() / ".claude-mpm" / "registry"
    new_registry_path = get_project_root() / ".claude-mpm" / "registry"
    
    # Backup existing files
    backup_old = None
    backup_new = None
    
    if old_registry_path.exists():
        backup_old = Path(tempfile.mkdtemp()) / "old_registry_backup"
        shutil.copytree(old_registry_path, backup_old)
        print(f"Backed up old registry to: {backup_old}")
    
    if new_registry_path.exists():
        backup_new = Path(tempfile.mkdtemp()) / "new_registry_backup"
        shutil.copytree(new_registry_path, backup_new)
        print(f"Backed up new registry to: {backup_new}")
    
    return backup_old, backup_new


def restore_from_backup(backup_old, backup_new):
    """Restore registry files from backup."""
    print("=== Restoring from Backup ===")
    
    old_registry_path = Path.home() / ".claude-mpm" / "registry"
    new_registry_path = get_project_root() / ".claude-mpm" / "registry"
    
    # Clear current registries
    if old_registry_path.exists():
        shutil.rmtree(old_registry_path)
    if new_registry_path.exists():
        shutil.rmtree(new_registry_path)
    
    # Restore from backups
    if backup_old:
        shutil.copytree(backup_old, old_registry_path)
        shutil.rmtree(backup_old.parent)  # Clean up temp directory
        print(f"Restored old registry from backup")
    
    if backup_new:
        shutil.copytree(backup_new, new_registry_path)
        shutil.rmtree(backup_new.parent)  # Clean up temp directory
        print(f"Restored new registry from backup")


def test_registry_uses_correct_location():
    """Test that ProjectRegistry uses the new deployment root location."""
    print("\n=== Testing Registry Location ===")
    
    expected_path = get_project_root() / ".claude-mpm" / "registry"
    
    registry = ProjectRegistry()
    
    assert registry.registry_dir == expected_path, (
        f"Registry path incorrect!\n"
        f"Expected: {expected_path}\n"
        f"Actual: {registry.registry_dir}"
    )
    
    print(f"✓ Registry uses correct deployment root path: {registry.registry_dir}")
    return True


def test_registry_creates_entries_in_new_location():
    """Test that new registry entries are created in the correct location."""
    print("\n=== Testing Entry Creation in New Location ===")
    
    registry = ProjectRegistry()
    new_registry_path = get_project_root() / ".claude-mpm" / "registry"
    
    # Count existing files
    existing_files = list(new_registry_path.glob("*.yaml")) if new_registry_path.exists() else []
    existing_count = len(existing_files)
    
    print(f"Existing registry files: {existing_count}")
    
    # Create a new entry
    entry = registry.get_or_create_project_entry()
    project_id = entry.get('project_id')
    
    # Verify the entry was created in the new location
    new_files = list(new_registry_path.glob("*.yaml"))
    new_count = len(new_files)
    
    assert new_count > existing_count, "New registry entry should have been created"
    
    # Verify the specific file exists
    expected_file = new_registry_path / f"{project_id}.yaml"
    assert expected_file.exists(), f"Registry file should exist: {expected_file}"
    
    print(f"✓ New entry created in correct location: {expected_file}")
    return True


def test_old_registry_ignored():
    """Test that old registry files are not used by the new system."""
    print("\n=== Testing Old Registry Ignored ===")
    
    old_registry_path = Path.home() / ".claude-mpm" / "registry"
    new_registry_path = get_project_root() / ".claude-mpm" / "registry"
    
    # Count files in both locations
    old_files = list(old_registry_path.glob("*.yaml")) if old_registry_path.exists() else []
    new_files = list(new_registry_path.glob("*.yaml")) if new_registry_path.exists() else []
    
    print(f"Old registry files: {len(old_files)}")
    print(f"New registry files: {len(new_files)}")
    
    # Create registry instance and list projects
    registry = ProjectRegistry()
    projects = registry.list_projects()
    
    print(f"Projects found by registry: {len(projects)}")
    
    # The registry should only find projects from the new location
    assert len(projects) == len(new_files), (
        f"Registry should only read from new location!\n"
        f"New files: {len(new_files)}, Projects found: {len(projects)}"
    )
    
    print("✓ Registry correctly ignores old location and only uses new location")
    return True


def test_backward_compatibility_no_interference():
    """Test that the new system doesn't interfere with old registry files."""
    print("\n=== Testing Backward Compatibility - No Interference ===")
    
    old_registry_path = Path.home() / ".claude-mpm" / "registry"
    
    if not old_registry_path.exists():
        print("No old registry files to test - skipping backward compatibility test")
        return True
    
    # Get initial state of old files
    old_files_before = list(old_registry_path.glob("*.yaml"))
    old_files_content_before = {}
    
    for file in old_files_before:
        with open(file) as f:
            old_files_content_before[file.name] = f.read()
    
    print(f"Old registry files before test: {len(old_files_before)}")
    
    # Use the new registry system
    registry = ProjectRegistry()
    entry = registry.get_or_create_project_entry()
    projects = registry.list_projects()
    
    # Check that old files are unchanged
    old_files_after = list(old_registry_path.glob("*.yaml"))
    old_files_content_after = {}
    
    for file in old_files_after:
        with open(file) as f:
            old_files_content_after[file.name] = f.read()
    
    # Verify no changes to old files
    assert len(old_files_before) == len(old_files_after), "Old file count should not change"
    
    for filename, content in old_files_content_before.items():
        assert filename in old_files_content_after, f"Old file {filename} should still exist"
        assert old_files_content_after[filename] == content, f"Old file {filename} should be unchanged"
    
    print("✓ Old registry files remain completely untouched")
    return True


def test_data_migration_readiness():
    """Test that data migration would be possible if implemented."""
    print("\n=== Testing Data Migration Readiness ===")
    
    old_registry_path = Path.home() / ".claude-mpm" / "registry"
    
    if not old_registry_path.exists():
        print("No old registry files to migrate - migration readiness confirmed")
        return True
    
    old_files = list(old_registry_path.glob("*.yaml"))
    print(f"Found {len(old_files)} files in old location for potential migration")
    
    # Verify old files are readable and have expected structure
    migration_ready_count = 0
    for file in old_files:
        try:
            with open(file) as f:
                data = yaml.safe_load(f)
            
            # Check for expected fields
            required_fields = ['project_id', 'project_path', 'project_name']
            has_required = all(field in data for field in required_fields)
            
            if has_required:
                migration_ready_count += 1
                print(f"  ✓ {file.name} - Ready for migration")
            else:
                print(f"  ⚠ {file.name} - Missing required fields: {[f for f in required_fields if f not in data]}")
                
        except Exception as e:
            print(f"  ❌ {file.name} - Cannot read: {e}")
    
    print(f"Migration-ready files: {migration_ready_count}/{len(old_files)}")
    
    if migration_ready_count > 0:
        print("✓ Old registry files are ready for migration if needed")
    else:
        print("⚠ No migration-ready files found")
    
    return migration_ready_count == len(old_files)


def main():
    """Run all migration and backward compatibility tests."""
    print("=== Registry Migration and Backward Compatibility Tests ===\n")
    
    try:
        # Create backups before testing
        backup_old, backup_new = create_test_migration_scenario()
        
        # Run tests
        results = {
            "correct_location": test_registry_uses_correct_location(),
            "new_entry_creation": test_registry_creates_entries_in_new_location(),
            "old_registry_ignored": test_old_registry_ignored(),
            "backward_compatibility": test_backward_compatibility_no_interference(),
            "migration_readiness": test_data_migration_readiness(),
        }
        
        # Restore backups
        restore_from_backup(backup_old, backup_new)
        
        # Summary
        print("\n=== TEST RESULTS SUMMARY ===")
        all_passed = True
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "❌ FAIL"
            print(f"  {test_name}: {status}")
            all_passed = all_passed and passed
        
        if all_passed:
            print("\n=== ALL MIGRATION TESTS PASSED ===")
            print("✅ Registry correctly uses deployment root location")
            print("✅ Old registry files are preserved and not interfered with")
            print("✅ New system operates independently from old location")
            print("✅ Data migration would be possible if needed")
            return 0
        else:
            print("\n=== SOME MIGRATION TESTS FAILED ===")
            return 1
            
    except Exception as e:
        print(f"\n=== MIGRATION TESTS FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())