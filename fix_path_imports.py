#!/usr/bin/env python3
"""
Quick script to add 'from pathlib import Path' to Python files that use Path but don't import it.
"""

import os
import re
from pathlib import Path

def needs_path_import(file_path):
    """Check if file uses Path but doesn't import it."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file uses Path
        if not re.search(r'\bPath\b', content):
            return False
            
        # Check if it already imports Path
        if 'from pathlib import Path' in content:
            return False
            
        return True
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def add_path_import(file_path):
    """Add Path import to a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find the best place to insert the import
        insert_index = 0
        
        # Look for existing imports
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                insert_index = i + 1
            elif line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""') and not line.strip().startswith("'''"):
                break
        
        # Insert the import
        if insert_index < len(lines) and lines[insert_index - 1].strip().startswith('from pathlib'):
            # Already has pathlib import, modify it
            for i in range(insert_index):
                if 'from pathlib import' in lines[i] and 'Path' not in lines[i]:
                    lines[i] = lines[i].rstrip() + ', Path\n'
                    break
        else:
            # Add new import
            lines.insert(insert_index, 'from pathlib import Path\n')
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"Added Path import to {file_path}")
        return True
        
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Find and fix all Python files that need Path import."""
    src_dir = Path('src')
    if not src_dir.exists():
        print("src directory not found")
        return
    
    fixed_count = 0
    
    for py_file in src_dir.rglob('*.py'):
        if needs_path_import(py_file):
            if add_path_import(py_file):
                fixed_count += 1
    
    print(f"Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
