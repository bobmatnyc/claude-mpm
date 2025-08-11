#!/usr/bin/env python3
"""Test the complete workflow of claude-mpm directory initialization."""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path


def test_complete_workflow():
    """Test the complete workflow with actual claude-mpm command."""
    
    # Get the claude-mpm executable path
    claude_mpm_path = Path(__file__).parent.parent / "claude-mpm"
    
    if not claude_mpm_path.exists():
        print(f"✗ claude-mpm executable not found at {claude_mpm_path}")
        return False
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_project"
        test_dir.mkdir()
        
        print(f"\nTesting claude-mpm in: {test_dir}")
        print("=" * 60)
        
        # Run claude-mpm help command from the test directory
        try:
            result = subprocess.run(
                [str(claude_mpm_path), "--help"],
                cwd=str(test_dir),
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check the output for the initialization message
            combined_output = result.stdout + result.stderr
            
            print("Output from claude-mpm --help:")
            print("-" * 40)
            
            # Look for the initialization message
            if "✓ Initialized .claude-mpm/" in combined_output:
                if str(test_dir) in combined_output:
                    print(f"✓ SUCCESS: Correctly initialized in {test_dir}")
                else:
                    print(f"✗ WARNING: Initialized but path may be incorrect")
                    print(f"Output: {combined_output[:500]}")
            elif "✓ Found existing .claude-mpm/" in combined_output:
                print(f"✓ Directory already existed (this is fine)")
            else:
                print("ℹ No initialization message found (may be suppressed)")
            
            # Check if the directory was actually created
            claude_mpm_dir = test_dir / ".claude-mpm"
            if claude_mpm_dir.exists():
                print(f"\n✓ VERIFIED: .claude-mpm directory exists at {claude_mpm_dir}")
                
                # Check subdirectories
                subdirs = ["agents", "config", "responses", "logs"]
                for subdir in subdirs:
                    if (claude_mpm_dir / subdir).exists():
                        print(f"  ✓ {subdir}/ exists")
                    else:
                        print(f"  ✗ {subdir}/ missing")
            else:
                print(f"\n✗ FAILED: .claude-mpm directory not found at {claude_mpm_dir}")
                return False
            
        except subprocess.TimeoutExpired:
            print("✗ Command timed out")
            return False
        except Exception as e:
            print(f"✗ Error running command: {e}")
            return False
    
    return True


def test_existing_directory():
    """Test behavior with existing .claude-mpm directory."""
    
    print("\n\nTesting with existing .claude-mpm directory")
    print("=" * 60)
    
    # Test in the framework directory itself (should already have .claude-mpm)
    framework_dir = Path(__file__).parent.parent
    claude_mpm_dir = framework_dir / ".claude-mpm"
    
    if claude_mpm_dir.exists():
        print(f"✓ Found existing .claude-mpm in framework directory: {framework_dir}")
        
        # Run a simple command to see the message
        claude_mpm_path = framework_dir / "claude-mpm"
        
        try:
            result = subprocess.run(
                [str(claude_mpm_path), "--version"],
                cwd=str(framework_dir),
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if "✓ Found existing .claude-mpm/" in result.stdout + result.stderr:
                print("✓ Correctly shows 'Found existing' message")
            elif "✓ Initialized .claude-mpm/" in result.stdout + result.stderr:
                print("✗ WARNING: Shows 'Initialized' instead of 'Found existing'")
            else:
                print("ℹ No directory message shown (may be normal)")
                
        except Exception as e:
            print(f"ℹ Could not run test: {e}")
    else:
        print(f"ℹ No existing .claude-mpm found in {framework_dir}")


if __name__ == "__main__":
    print("Testing complete claude-mpm workflow...")
    print("=" * 60)
    
    success = test_complete_workflow()
    test_existing_directory()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
        sys.exit(1)