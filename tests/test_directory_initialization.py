#!/usr/bin/env python3
"""Test script to verify .claude-mpm directory initialization works correctly."""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.init import ProjectInitializer


def test_directory_initialization():
    """Test that .claude-mpm is created in the correct location."""
    
    # Create a temporary directory to test in
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        test_project_dir = tmpdir_path / "test_project"
        test_project_dir.mkdir()
        
        # Change to the test directory
        original_cwd = Path.cwd()
        try:
            os.chdir(test_project_dir)
            print(f"\nTest 1: Testing in temporary directory: {test_project_dir}")
            
            # Initialize the project directory
            initializer = ProjectInitializer()
            result = initializer.initialize_project_directory()
            
            # Check if it was created in the right place
            expected_dir = test_project_dir / ".claude-mpm"
            if expected_dir.exists():
                print(f"✓ SUCCESS: .claude-mpm created in correct location: {expected_dir}")
                
                # Check subdirectories
                subdirs = ["agents/project-specific", "config", "responses", "logs"]
                for subdir in subdirs:
                    subdir_path = expected_dir / subdir
                    if subdir_path.exists():
                        print(f"  ✓ Subdirectory exists: {subdir}")
                    else:
                        print(f"  ✗ Missing subdirectory: {subdir}")
            else:
                print(f"✗ FAILED: .claude-mpm not found in {test_project_dir}")
                print(f"  Project dir was: {initializer.project_dir}")
            
            # Test 2: Test with explicit path
            print(f"\nTest 2: Testing with explicit project path")
            another_test_dir = tmpdir_path / "another_project"
            another_test_dir.mkdir()
            
            initializer2 = ProjectInitializer()
            result2 = initializer2.initialize_project_directory(another_test_dir)
            
            expected_dir2 = another_test_dir / ".claude-mpm"
            if expected_dir2.exists():
                print(f"✓ SUCCESS: .claude-mpm created with explicit path: {expected_dir2}")
            else:
                print(f"✗ FAILED: .claude-mpm not found in {another_test_dir}")
            
        finally:
            # Restore original directory
            os.chdir(original_cwd)
    
    # Test 3: Test in current real directory (non-destructive check)
    print(f"\nTest 3: Checking current directory behavior")
    print(f"Current working directory: {Path.cwd()}")
    
    initializer3 = ProjectInitializer()
    # Just check what path would be used without creating
    test_path = Path.cwd() / ".claude-mpm"
    print(f"Would use path: {test_path}")
    
    # Check if it already exists
    if test_path.exists():
        print(f"✓ .claude-mpm already exists in current directory")
    else:
        print(f"ℹ .claude-mpm would be created in current directory if initialized")


if __name__ == "__main__":
    print("Testing .claude-mpm directory initialization...")
    print("=" * 60)
    test_directory_initialization()
    print("\n" + "=" * 60)
    print("Tests complete!")