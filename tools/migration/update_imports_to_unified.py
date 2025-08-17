#!/usr/bin/env python3
"""
Script to update import statements to use the new unified modules.

This script systematically updates all import statements across the codebase
to use the new unified path management and agent registry systems.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Define import replacements
IMPORT_REPLACEMENTS = {
    # Path management imports
    'from claude_mpm.core.unified_paths import': 'from claude_mpm.core.unified_paths import',
    'from claude_mpm.core.unified_paths import': 'from claude_mpm.core.unified_paths import',
    'from claude_mpm.core.unified_paths import': 'from claude_mpm.core.unified_paths import',
    
    # Agent registry imports  
    'from claude_mpm.core.unified_agent_registry import': 'from claude_mpm.core.unified_agent_registry import',
    'from claude_mpm.core.unified_agent_registry import': 'from claude_mpm.core.unified_agent_registry import',
    
    # Specific function imports that need mapping
    'get_path_manager()': 'get_path_manager()',
    'get_path_manager()': 'get_path_manager()',
    'get_path_manager()': 'get_path_manager()',
}

# Function name mappings for unified APIs
FUNCTION_MAPPINGS = {
    # Path management
    'get_path_manager().get_framework_root()': 'get_framework_root()',
    'get_path_manager().get_project_root()': 'get_project_root()',
    'get_path_manager().get_agents_dir()': 'get_agents_dir()',
    'get_path_manager().get_config_dir()': 'get_config_dir()',
    'get_path_manager().find_file_upwards': 'find_file_upwards',
    'get_path_manager().get_package_resource_path': 'get_package_resource_path',
    
    # Agent registry
    'get_agent_registry()': 'get_agent_registry()',
    'get_agent_registry()': 'get_agent_registry()',
}

def update_file_imports(file_path: Path) -> bool:
    """
    Update import statements in a single file.
    
    Args:
        file_path: Path to the file to update
        
    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply import replacements
        for old_import, new_import in IMPORT_REPLACEMENTS.items():
            if old_import in content:
                content = content.replace(old_import, new_import)
                print(f"  Updated import in {file_path}: {old_import} -> {new_import}")
        
        # Apply function mappings
        for old_func, new_func in FUNCTION_MAPPINGS.items():
            if old_func in content:
                content = content.replace(old_func, new_func)
                print(f"  Updated function call in {file_path}: {old_func} -> {new_func}")
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in a directory."""
    python_files = []
    for file_path in directory.rglob("*.py"):
        # Skip certain directories
        skip_dirs = {
            "__pycache__", ".git", "node_modules", ".pytest_cache",
            "venv", ".venv", "dist", "build", ".tox"
        }
        
        if any(skip_dir in str(file_path) for skip_dir in skip_dirs):
            continue
            
        # Skip backup files we created
        if file_path.name.endswith("_original.py"):
            continue
            
        python_files.append(file_path)
    
    return python_files

def update_imports_in_directory(directory: Path) -> Tuple[int, int]:
    """
    Update imports in all Python files in a directory.
    
    Args:
        directory: Directory to process
        
    Returns:
        Tuple of (files_processed, files_modified)
    """
    python_files = find_python_files(directory)
    files_modified = 0
    
    print(f"Processing {len(python_files)} Python files in {directory}")
    
    for file_path in python_files:
        if update_file_imports(file_path):
            files_modified += 1
    
    return len(python_files), files_modified

def main():
    """Main function to update all imports."""
    print("Updating imports to use unified modules...")
    print("=" * 50)
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    src_dir = project_root / "src"
    
    if not src_dir.exists():
        print(f"Error: src directory not found at {src_dir}")
        return 1
    
    # Update imports in src directory
    total_processed, total_modified = update_imports_in_directory(src_dir)
    
    # Also update test files
    tests_dir = project_root / "tests"
    if tests_dir.exists():
        test_processed, test_modified = update_imports_in_directory(tests_dir)
        total_processed += test_processed
        total_modified += test_modified
    
    # Update scripts
    scripts_dir = project_root / "scripts"
    if scripts_dir.exists():
        script_processed, script_modified = update_imports_in_directory(scripts_dir)
        total_processed += script_processed
        total_modified += script_modified
    
    # Update tools
    tools_dir = project_root / "tools"
    if tools_dir.exists():
        tool_processed, tool_modified = update_imports_in_directory(tools_dir)
        total_processed += tool_processed
        total_modified += tool_modified
    
    print("=" * 50)
    print(f"Import update complete!")
    print(f"Files processed: {total_processed}")
    print(f"Files modified: {total_modified}")
    
    if total_modified > 0:
        print("\nRecommendation: Run tests to ensure all imports work correctly.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
