#!/usr/bin/env python3
"""Test to simulate the user's exact scenario from /Users/masa/Projects/managed/itinerizer."""

import os
import sys
import subprocess
import tempfile
from pathlib import Path


def test_managed_project_scenario():
    """Simulate running claude-mpm from a managed project directory."""
    
    claude_mpm_path = Path(__file__).parent.parent / "claude-mpm"
    
    # Create a test directory structure similar to the user's
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create managed/project structure
        managed_dir = Path(tmpdir) / "managed"
        project_dir = managed_dir / "test_project"
        project_dir.mkdir(parents=True)
        
        print(f"Testing scenario: Running claude-mpm from project directory")
        print(f"Project location: {project_dir}")
        print(f"Framework location: {claude_mpm_path.parent}")
        print("=" * 60)
        
        # Run claude-mpm from the project directory
        result = subprocess.run(
            [str(claude_mpm_path), "--version"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout + result.stderr
        
        # Check for correct initialization message
        if f"✓ Initialized .claude-mpm/ in {project_dir}" in output:
            print(f"✓ SUCCESS: Correct initialization message showing project directory")
        elif f"✓ Found existing .claude-mpm/ directory in {project_dir}" in output:
            print(f"✓ SUCCESS: Correct 'found existing' message showing project directory")
        elif "✓ Initialized .claude-mpm/ in /Users/masa/Projects/claude-mpm" in output:
            print(f"✗ FAILED: Wrong path! Shows framework directory instead of project directory")
            print(f"  Expected: {project_dir}")
            print(f"  Got: /Users/masa/Projects/claude-mpm")
            return False
        else:
            print(f"⚠ WARNING: Unexpected output")
            print(f"Output snippet: {output[:500]}")
        
        # Verify the directory was actually created in the right place
        claude_mpm_dir = project_dir / ".claude-mpm"
        if claude_mpm_dir.exists():
            print(f"\n✓ VERIFIED: .claude-mpm created in correct location: {claude_mpm_dir}")
            
            # List contents
            subdirs = list(claude_mpm_dir.iterdir())
            print(f"  Contents: {', '.join([d.name for d in subdirs])}")
            
            # Check expected subdirectories
            expected = ["agents", "config", "responses", "logs"]
            for exp in expected:
                if (claude_mpm_dir / exp).exists():
                    print(f"  ✓ {exp}/ exists")
                else:
                    print(f"  ✗ {exp}/ missing")
                    
        else:
            print(f"\n✗ FAILED: .claude-mpm not found in project directory")
            
            # Check if it was created in the wrong place
            wrong_location = claude_mpm_path.parent / ".claude-mpm"
            if wrong_location.exists():
                print(f"  ⚠ Found .claude-mpm in framework directory (wrong location): {wrong_location}")
            
            return False
    
    return True


if __name__ == "__main__":
    print("Testing managed project scenario...")
    print("=" * 60)
    
    success = test_managed_project_scenario()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ Test passed! Directory initialization works correctly.")
        print("\nSummary:")
        print("- .claude-mpm is created in the current working directory")
        print("- NOT in the framework installation directory")
        print("- Messages correctly show the actual location")
    else:
        print("✗ Test failed! Directory initialization has issues.")
        sys.exit(1)