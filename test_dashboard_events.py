#!/usr/bin/env python3
"""
Test script to trigger events and check dashboard tabs.
"""

import subprocess
import time
import os
import sys

# Add project root to path
sys.path.insert(0, "src")

def main():
    print("🧪 Testing Dashboard Event Filtering")
    print("=" * 40)
    
    print("📊 Dashboard should be running at http://localhost:8765")
    print("   Open the dashboard and switch to the Agents or Files tab")
    print("   Check the browser console for debugging output")
    print()
    
    print("🔧 Triggering file operations...")
    
    # Create a test file
    test_file = "dashboard_test_file.txt"
    with open(test_file, "w") as f:
        f.write("This is a test file for dashboard debugging\n")
    print(f"✓ Created {test_file}")
    
    # Run a claude-mpm command that will trigger Read tool
    print("🤖 Running claude-mpm command to trigger tool events...")
    
    cmd = [
        "./claude-mpm", "run", 
        "--non-interactive", 
        "-i", f"Read the file {test_file} and summarize what it contains"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print("✓ Command completed")
        if result.stdout:
            print("📝 Output snippet:", result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
    except subprocess.TimeoutExpired:
        print("⚠️  Command timed out (this is normal)")
    except Exception as e:
        print(f"❌ Error running command: {e}")
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"✓ Cleaned up {test_file}")
    
    print()
    print("🔍 Check the dashboard console logs to see:")
    print("   1. Events being received and transformed")
    print("   2. Agent tab filtering results")
    print("   3. Files tab filtering results")
    print("   4. Event breakdowns by type and tool")
    print()
    print("💡 Look for log messages like:")
    print("   - 'Received claude_event:'")
    print("   - 'Transformed event:'")
    print("   - 'Agent tab - event type breakdown:'")
    print("   - 'Files tab - filtering summary:'")

if __name__ == "__main__":
    main()