#!/usr/bin/env python3
"""
Debug script to trace the session and working directory flow.

WHY: This script helps us understand exactly where "Unknown" values are being set
and why the HUD button is not being enabled properly.
"""

import os
import sys
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def analyze_session_data():
    """Analyze session data structures to understand the flow."""
    print("="*60)
    print("DEBUGGING SESSION AND WORKING DIRECTORY FLOW")
    print("="*60)
    
    # Check if we're in the right directory
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    # Check git status
    try:
        import subprocess
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                               cwd=current_dir, capture_output=True, text=True)
        if result.returncode == 0:
            current_branch = result.stdout.strip()
            print(f"Current git branch: {current_branch}")
        else:
            print(f"Git error: {result.stderr}")
    except Exception as e:
        print(f"Cannot get git branch: {e}")
    
    print("\n" + "-"*60)
    print("EXPECTED FLOW ANALYSIS")
    print("-"*60)
    
    print("1. Dashboard loads → HTML shows 'Unknown' in footer by default")
    print("2. Session manager initializes → calls updateFooterInfo()")
    print("3. updateFooterInfo() sets workingDir = 'Unknown' initially")
    print("4. Working directory manager initializes → calls getDefaultWorkingDir()")
    print("5. getDefaultWorkingDir() should NOT use 'Unknown' values")
    print("6. setWorkingDirectory() should update footer with real directory")
    print("7. updateGitBranch() should be called with real directory")
    print("8. Git branch request should succeed and update footer")
    
    print("\n" + "-"*60) 
    print("POTENTIAL ISSUES")
    print("-"*60)
    
    print("Issue 1: Default HTML shows 'Unknown' and it's never updated")
    print("  → Check if setWorkingDirectory() is being called")
    print("  → Check if working directory manager is initialized")
    
    print("\nIssue 2: Working directory manager uses 'Unknown' from footer")
    print("  → getDefaultWorkingDir() might read 'Unknown' from footer")
    print("  → Should use process.cwd() fallback instead")
    
    print("\nIssue 3: Session selection doesn't trigger HUD button update")
    print("  → Check if sessionChanged events are being fired")
    print("  → Check if HUD manager is receiving events")
    print("  → Check if HUD button exists in DOM")
    
    print("\n" + "-"*60)
    print("DEBUGGING CHECKLIST")
    print("-"*60)
    
    checklist = [
        "✓ Added [GIT-BRANCH-DEBUG] logs to server",
        "✓ Added [WORKING-DIR-DEBUG] logs to working directory manager", 
        "✓ Added [SESSION-DEBUG] logs to session manager",
        "✓ Added [HUD-DEBUG] logs to HUD manager",
        "✓ Added git_branch_response handler to working directory manager",
        "⚠ Need to test actual behavior with debugging logs",
        "⚠ Need to fix root cause of 'Unknown' values",
        "⚠ Need to fix HUD button not enabling"
    ]
    
    for item in checklist:
        print(f"  {item}")
    
    print(f"\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Run: python scripts/test_debug_fixes.py")
    print("2. Open browser console and watch for debug logs")
    print("3. Identify where 'Unknown' values are coming from")  
    print("4. Identify why HUD button is not being enabled")
    print("5. Fix the root causes based on debug output")

if __name__ == '__main__':
    analyze_session_data()