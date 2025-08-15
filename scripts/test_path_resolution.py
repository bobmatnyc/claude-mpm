#!/usr/bin/env python3
"""Test script to verify path resolution works correctly in different installation scenarios."""

import sys
import os
from pathlib import Path

def test_path_resolution():
    """Test path resolution in different scenarios."""
    
    print("=" * 60)
    print("Path Resolution Test")
    print("=" * 60)
    
    # Test 1: Test utils/paths.py PathResolver
    print("\n1. Testing PathResolver (utils/paths.py):")
    print("-" * 40)
    
    try:
        from claude_mpm.utils.paths import PathResolver
        
        # Clear cache to ensure fresh detection
        PathResolver.clear_cache()
        
        framework_root = PathResolver.get_framework_root()
        print(f"  Framework root: {framework_root}")
        
        agents_dir = PathResolver.get_agents_dir()
        print(f"  Agents dir: {agents_dir}")
        print(f"  Agents dir exists: {agents_dir.exists()}")
        
        # Check for templates
        templates_dir = agents_dir / "templates"
        print(f"  Templates dir: {templates_dir}")
        print(f"  Templates dir exists: {templates_dir.exists()}")
        
        if templates_dir.exists():
            templates = list(templates_dir.glob("*.json"))
            print(f"  Found {len(templates)} template files")
            if templates:
                print(f"  Sample templates: {[t.name for t in templates[:3]]}")
        
        # Test new get_package_resource_path method
        print("\n  Testing get_package_resource_path:")
        resource_path = PathResolver.get_package_resource_path('agents/templates')
        print(f"    agents/templates: {resource_path}")
        print(f"    Exists: {resource_path.exists()}")
        
        # Test with a specific file
        try:
            template_file = PathResolver.get_package_resource_path('agents/templates/engineer.json')
            print(f"    agents/templates/engineer.json: {template_file}")
            print(f"    File exists: {template_file.exists()}")
        except FileNotFoundError as e:
            print(f"    Failed to find engineer.json: {e}")
            
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Test config/paths.py ClaudeMPMPaths
    print("\n2. Testing ClaudeMPMPaths (config/paths.py):")
    print("-" * 40)
    
    try:
        from claude_mpm.config.paths import paths
        
        # Access properties to trigger detection
        project_root = paths.project_root
        print(f"  Project root: {project_root}")
        
        # Check if installed
        is_installed = hasattr(paths, '_is_installed') and paths._is_installed
        print(f"  Is installed: {is_installed}")
        
        claude_mpm_dir = paths.claude_mpm_dir
        print(f"  Claude MPM dir: {claude_mpm_dir}")
        print(f"  Claude MPM dir exists: {claude_mpm_dir.exists()}")
        
        agents_dir = paths.agents_dir
        print(f"  Agents dir: {agents_dir}")
        print(f"  Agents dir exists: {agents_dir.exists()}")
        
        # Check for templates
        templates_dir = agents_dir / "templates"
        print(f"  Templates dir: {templates_dir}")
        print(f"  Templates dir exists: {templates_dir.exists()}")
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Check Python environment
    print("\n3. Python Environment Info:")
    print("-" * 40)
    print(f"  Python version: {sys.version}")
    print(f"  Python executable: {sys.executable}")
    print(f"  Current working directory: {os.getcwd()}")
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"  In virtual environment: {in_venv}")
    
    # Check installation type
    import claude_mpm
    module_path = Path(claude_mpm.__file__)
    print(f"  claude_mpm module path: {module_path}")
    
    if 'site-packages' in str(module_path):
        print("  Installation type: pip/pipx (site-packages)")
    elif 'dist-packages' in str(module_path):
        print("  Installation type: system package (dist-packages)")
    else:
        print("  Installation type: development (editable install or local)")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_path_resolution()