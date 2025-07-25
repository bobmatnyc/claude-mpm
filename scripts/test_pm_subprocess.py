#!/usr/bin/env python3
"""Test PM subprocess with minimal framework."""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.core.claude_launcher import ClaudeLauncher
from claude_mpm.core.minimal_framework_loader import MinimalFrameworkLoader

def main():
    print("🔍 Testing PM Subprocess")
    print("=" * 80)
    
    # Create launcher
    launcher = ClaudeLauncher(model="opus", skip_permissions=True, log_level="DEBUG")
    
    # Load minimal framework
    loader = MinimalFrameworkLoader()
    framework = loader.get_framework_instructions()
    
    # Add delegation format instruction
    framework += """
## Delegation Format
When delegating tasks, use this exact format:
**[Agent Name]**: [Task description]

Example:
**Engineer**: Create a function that calculates factorial
**QA**: Write tests for the factorial function
"""
    
    # Test input
    user_input = "Create a hello world function in Python"
    full_message = framework + "\n\nUser: " + user_input
    
    print(f"Framework length: {len(framework)} chars")
    print(f"Total message length: {len(full_message)} chars")
    print(f"\nUser input: {user_input}")
    print("\nLaunching PM subprocess...\n")
    
    try:
        stdout, stderr, returncode = launcher.launch_oneshot(
            message=full_message,
            use_stdin=True,
            timeout=30
        )
        
        print(f"Return code: {returncode}")
        
        if returncode == 0:
            print("\nPM Response:")
            print("-" * 50)
            print(stdout)
            print("-" * 50)
        else:
            print(f"\nError: {stderr}")
            
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()