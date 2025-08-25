#!/usr/bin/env python3
"""Update version numbers in agent template JSON files by incrementing minor version."""

import json
import os
from pathlib import Path
from typing import Dict, Any

def increment_minor_version(version) -> str:
    """
    Increment the minor version number.
    
    Handles both string versions (e.g., "1.0.0") and integer versions (e.g., 5).
    
    Examples:
        "1.0.0" -> "1.1.0"
        "2.3.5" -> "2.4.0"
        "0.5.2" -> "0.6.0"
        5 -> "5.1.0"
    """
    # Handle integer versions (convert to X.0.0 format first)
    if isinstance(version, int):
        return f"{version}.1.0"
    
    # Handle string versions
    try:
        parts = str(version).split('.')
        if len(parts) == 1:
            # Single number string like "5"
            return f"{parts[0]}.1.0"
        elif len(parts) != 3:
            print(f"Warning: Invalid version format '{version}', skipping")
            return str(version)
        
        major, minor, patch = parts
        new_minor = int(minor) + 1
        return f"{major}.{new_minor}.0"
    except (ValueError, IndexError) as e:
        print(f"Warning: Could not parse version '{version}': {e}")
        return str(version)

def update_template_version(filepath: Path) -> bool:
    """
    Update the version field in a JSON template file.
    
    Handles multiple version field names:
    - 'version' (backup files)
    - 'template_version' (main templates)
    - 'agent_version' (also in main templates)
    
    Returns:
        True if the file was updated, False otherwise.
    """
    try:
        # Read the JSON file
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check for version fields in order of preference
        version_fields = ['template_version', 'agent_version', 'version']
        version_field = None
        old_version = None
        
        for field in version_fields:
            if field in data:
                version_field = field
                old_version = data[field]
                break
        
        if version_field is None:
            print(f"  No version field found in {filepath.name}")
            return False
        
        new_version = increment_minor_version(old_version)
        
        if str(old_version) == new_version:
            print(f"  {filepath.name}: Version unchanged (parsing issue)")
            return False
        
        # Update the version
        data[version_field] = new_version
        
        # Also update template_changelog if it exists and we're updating template_version
        if version_field == 'template_version' and 'template_changelog' in data:
            from datetime import datetime
            new_changelog_entry = {
                "version": new_version,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "description": "Version bump to trigger redeployment of optimized templates"
            }
            # Insert at the beginning of the changelog
            if isinstance(data['template_changelog'], list):
                data['template_changelog'].insert(0, new_changelog_entry)
        
        # Write back to file with proper formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')  # Add trailing newline
        
        print(f"  {filepath.name}: {version_field}={old_version} -> {new_version}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"  Error parsing JSON in {filepath.name}: {e}")
        return False
    except Exception as e:
        print(f"  Error updating {filepath.name}: {e}")
        return False

def main():
    """Main function to update all agent template versions."""
    templates_dir = Path(__file__).parent.parent / 'src' / 'claude_mpm' / 'agents' / 'templates'
    
    if not templates_dir.exists():
        print(f"Error: Templates directory not found at {templates_dir}")
        return 1
    
    # Find all JSON files (excluding backup directory for main templates)
    json_files = []
    for json_file in templates_dir.glob('*.json'):
        json_files.append(json_file)
    
    # Also process backup files if needed
    backup_dir = templates_dir / 'backup'
    if backup_dir.exists():
        for json_file in backup_dir.glob('*.json'):
            json_files.append(json_file)
    
    if not json_files:
        print("No JSON template files found")
        return 1
    
    print(f"Found {len(json_files)} JSON template files to update\n")
    
    # Update main templates
    print("Updating main templates:")
    main_updated = 0
    for filepath in sorted(json_files):
        if 'backup' not in str(filepath):
            if update_template_version(filepath):
                main_updated += 1
    
    # Update backup templates
    print("\nUpdating backup templates:")
    backup_updated = 0
    for filepath in sorted(json_files):
        if 'backup' in str(filepath):
            if update_template_version(filepath):
                backup_updated += 1
    
    print(f"\nSummary:")
    print(f"  Main templates updated: {main_updated}")
    print(f"  Backup templates updated: {backup_updated}")
    print(f"  Total files updated: {main_updated + backup_updated}")
    
    return 0

if __name__ == '__main__':
    exit(main())