#!/usr/bin/env python3
"""Interactive test for cleanup command to verify manual input works."""

import sys
import subprocess

def main():
    print("=== Interactive Cleanup Command Test ===\n")
    print("This test will run the cleanup command and wait for your input.")
    print("When prompted, type 'n' to cancel the operation.\n")
    
    print("Running: claude-mpm cleanup-memory")
    print("(without --dry-run to trigger the confirmation prompt)\n")
    print("-" * 50)
    
    # Run the command interactively
    try:
        result = subprocess.run(
            ['claude-mpm', 'cleanup-memory'],
            check=False
        )
        
        print("-" * 50)
        if result.returncode == 0:
            print("\n✅ Command completed successfully")
        else:
            print(f"\n⚠️ Command exited with code: {result.returncode}")
            
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error running command: {e}")
        return 1
    
    print("\nTest complete. The command should have accepted your keyboard input.")
    print("If you were able to type 'n' and see 'Cleanup cancelled', the fix works!")
    return 0

if __name__ == "__main__":
    sys.exit(main())