#!/usr/bin/env python3
"""Test backward compatibility between old and new registry locations."""

import sys
import yaml
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.project_registry import ProjectRegistry
from claude_mpm.deployment_paths import get_project_root


def analyze_registry_data():
    """Analyze data in both old and new registry locations."""
    print("=== Registry Data Analysis ===")
    
    old_registry_path = Path.home() / ".claude-mpm" / "registry"
    new_registry_path = get_project_root() / ".claude-mpm" / "registry"
    
    print(f"Old registry path: {old_registry_path}")
    print(f"New registry path: {new_registry_path}")
    
    # Analyze old registry
    old_files = list(old_registry_path.glob("*.yaml")) if old_registry_path.exists() else []
    old_projects = []
    
    print(f"\nOld registry files: {len(old_files)}")
    for file in old_files:
        try:
            with open(file) as f:
                data = yaml.safe_load(f)
            old_projects.append({
                'file': file.name,
                'project_id': data.get('project_id'),
                'project_path': data.get('project_path'),
                'project_name': data.get('project_name'),
                'access_count': data.get('metadata', {}).get('access_count', 0),
                'created_at': data.get('metadata', {}).get('created_at'),
                'last_accessed': data.get('metadata', {}).get('last_accessed')
            })
            print(f"  - {file.name}: {data.get('project_name')} ({data.get('project_path')})")
        except Exception as e:
            print(f"  - {file.name}: Error reading - {e}")
    
    # Analyze new registry
    new_files = list(new_registry_path.glob("*.yaml")) if new_registry_path.exists() else []
    new_projects = []
    
    print(f"\nNew registry files: {len(new_files)}")
    for file in new_files:
        try:
            with open(file) as f:
                data = yaml.safe_load(f)
            new_projects.append({
                'file': file.name,
                'project_id': data.get('project_id'),
                'project_path': data.get('project_path'),
                'project_name': data.get('project_name'),
                'access_count': data.get('metadata', {}).get('access_count', 0),
                'created_at': data.get('metadata', {}).get('created_at'),
                'last_accessed': data.get('metadata', {}).get('last_accessed')
            })
            print(f"  - {file.name}: {data.get('project_name')} ({data.get('project_path')})")
        except Exception as e:
            print(f"  - {file.name}: Error reading - {e}")
    
    return old_projects, new_projects


def test_registry_isolation():
    """Test that new registry operates in isolation from old registry."""
    print("\n=== Registry Isolation Test ===")
    
    old_registry_path = Path.home() / ".claude-mpm" / "registry"
    new_registry_path = get_project_root() / ".claude-mpm" / "registry"
    
    # Get initial state of old files
    old_files_before = list(old_registry_path.glob("*.yaml")) if old_registry_path.exists() else []
    old_files_content = {}
    
    for file in old_files_before:
        try:
            with open(file, 'r') as f:
                old_files_content[str(file)] = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file}: {e}")
    
    print(f"Old registry state before test: {len(old_files_before)} files")
    
    # Use the new registry system multiple times
    registry = ProjectRegistry()
    
    # List projects (should only see new registry projects)
    projects = registry.list_projects()
    print(f"Projects found in registry: {len(projects)}")
    
    # Create/update entry multiple times
    for i in range(3):
        entry = registry.get_or_create_project_entry()
        project_id = entry.get('project_id')
        access_count = entry.get('metadata', {}).get('access_count', 0)
        print(f"  Iteration {i+1}: Project {project_id}, Access count: {access_count}")
    
    # Check that old files are completely unchanged
    old_files_after = list(old_registry_path.glob("*.yaml")) if old_registry_path.exists() else []
    
    print(f"\nOld registry state after test: {len(old_files_after)} files")
    
    # Verify no changes to old files
    isolation_successful = True
    
    if len(old_files_before) != len(old_files_after):
        print(f"❌ File count changed: {len(old_files_before)} -> {len(old_files_after)}")
        isolation_successful = False
    else:
        print(f"✓ File count unchanged: {len(old_files_before)}")
    
    # Check file contents
    for file in old_files_after:
        file_str = str(file)
        if file_str in old_files_content:
            try:
                with open(file, 'r') as f:
                    current_content = f.read()
                
                if current_content != old_files_content[file_str]:
                    print(f"❌ {file.name} content changed")
                    isolation_successful = False
                else:
                    print(f"✓ {file.name} content unchanged")
            except Exception as e:
                print(f"⚠ Could not verify {file.name}: {e}")
    
    if isolation_successful:
        print("✅ Registry isolation successful - old files completely untouched")
    else:
        print("❌ Registry isolation failed - old files were modified")
    
    return isolation_successful


def test_data_consistency():
    """Test data consistency between registry operations."""
    print("\n=== Data Consistency Test ===")
    
    registry = ProjectRegistry()
    
    # Get project multiple times and ensure consistency
    entries = []
    for i in range(3):
        entry = registry.get_or_create_project_entry()
        entries.append(entry)
        print(f"Entry {i+1}: ID={entry.get('project_id')}, Count={entry.get('metadata', {}).get('access_count')}")
    
    # All entries should have the same project_id
    project_ids = [entry.get('project_id') for entry in entries]
    project_paths = [entry.get('project_path') for entry in entries]
    
    consistency_check = {
        "same_project_id": len(set(project_ids)) == 1,
        "same_project_path": len(set(project_paths)) == 1,
        "increasing_access_count": all(
            entries[i].get('metadata', {}).get('access_count', 0) < 
            entries[i+1].get('metadata', {}).get('access_count', 0)
            for i in range(len(entries) - 1)
        )
    }
    
    print(f"\nConsistency checks:")
    for check, passed in consistency_check.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"  {check}: {status}")
    
    all_consistent = all(consistency_check.values())
    if all_consistent:
        print("✅ Data consistency verified")
    else:
        print("❌ Data consistency issues detected")
    
    return all_consistent


def test_migration_data_availability():
    """Test that data would be available for migration if needed."""
    print("\n=== Migration Data Availability Test ===")
    
    old_registry_path = Path.home() / ".claude-mpm" / "registry"
    
    if not old_registry_path.exists():
        print("No old registry data available for migration")
        return True
    
    old_files = list(old_registry_path.glob("*.yaml"))
    print(f"Old registry files available: {len(old_files)}")
    
    migration_compatible_count = 0
    
    for file in old_files:
        try:
            with open(file) as f:
                data = yaml.safe_load(f)
            
            # Check for minimal required fields for migration
            required_fields = ['project_id', 'project_path', 'project_name']
            optional_fields = ['metadata', 'git', 'project_info', 'environment']
            
            has_required = all(field in data for field in required_fields)
            has_optional = sum(1 for field in optional_fields if field in data)
            
            print(f"  {file.name}:")
            print(f"    Required fields: {has_required} ({'✓' if has_required else '❌'})")
            print(f"    Optional fields: {has_optional}/{len(optional_fields)}")
            print(f"    Project: {data.get('project_name')} at {data.get('project_path')}")
            
            if has_required:
                migration_compatible_count += 1
        
        except Exception as e:
            print(f"  {file.name}: ❌ Cannot read - {e}")
    
    print(f"\nMigration summary:")
    print(f"  Total files: {len(old_files)}")
    print(f"  Migration-compatible: {migration_compatible_count}")
    
    if migration_compatible_count == len(old_files):
        print("✅ All old registry files are migration-compatible")
        return True
    else:
        print(f"⚠ {len(old_files) - migration_compatible_count} files need attention for migration")
        return migration_compatible_count > 0


def main():
    """Run comprehensive backward compatibility tests."""
    print("=== BACKWARD COMPATIBILITY VERIFICATION ===\n")
    
    try:
        # Analyze data in both locations
        old_projects, new_projects = analyze_registry_data()
        
        # Test registry isolation
        isolation_ok = test_registry_isolation()
        
        # Test data consistency
        consistency_ok = test_data_consistency()
        
        # Test migration data availability
        migration_ready = test_migration_data_availability()
        
        # Summary
        print("\n=== BACKWARD COMPATIBILITY SUMMARY ===")
        
        results = {
            "Registry operates in isolation": isolation_ok,
            "Data consistency maintained": consistency_ok,
            "Migration data available": migration_ready,
        }
        
        all_passed = True
        for test, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test}: {status}")
            all_passed = all_passed and passed
        
        print(f"\nData summary:")
        print(f"  Old registry projects: {len(old_projects)}")
        print(f"  New registry projects: {len(new_projects)}")
        
        if all_passed:
            print("\n✅ BACKWARD COMPATIBILITY VERIFIED")
            print("  - New system operates completely independently")
            print("  - Old registry files are preserved and untouched")
            print("  - Data migration would be possible if implemented")
            print("  - No interference between old and new systems")
            return 0
        else:
            print("\n❌ BACKWARD COMPATIBILITY ISSUES DETECTED")
            return 1
    
    except Exception as e:
        print(f"\n❌ BACKWARD COMPATIBILITY TEST FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())