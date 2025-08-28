#!/usr/bin/env python3
"""
Test script to verify the Code tab redesign with auto-discovery and lazy loading.

This script starts the dashboard server and opens it in a browser to test:
1. Automatic discovery of root-level items when Code tab is opened
2. Lazy loading when clicking on directories and files
3. Advanced options visible by default with TypeScript enabled
4. Removal of manual Analyze button and path input
"""

import subprocess
import time
import webbrowser
import sys

def main():
    print("🚀 Starting Claude MPM Dashboard to test Code tab redesign...")
    print("\nTesting the following features:")
    print("✅ Auto-discovery of root-level items when Code tab opens")
    print("✅ Lazy loading on directory/file clicks")
    print("✅ Advanced options visible by default")
    print("✅ TypeScript checkbox enabled by default")
    print("✅ No manual Analyze button or path input")
    
    # Start the dashboard
    print("\n📊 Starting dashboard server...")
    try:
        # Start dashboard in background
        process = subprocess.Popen(
            ["./scripts/claude-mpm", "dashboard"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it time to start
        time.sleep(3)
        
        # Open browser
        print("🌐 Opening dashboard in browser...")
        webbrowser.open("http://localhost:8765")
        
        print("\n✨ Dashboard is running!")
        print("\nTo test the Code tab:")
        print("1. Click on the 'Code' tab")
        print("2. Verify 'Project Root' appears automatically")
        print("3. Click on directories to explore them")
        print("4. Click on files to analyze their AST")
        print("5. Check that TypeScript is enabled by default")
        print("\nPress Ctrl+C to stop the dashboard...")
        
        # Keep running until interrupted
        process.wait()
        
    except KeyboardInterrupt:
        print("\n\n👋 Stopping dashboard...")
        process.terminate()
        process.wait(timeout=5)
        print("✅ Dashboard stopped successfully")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()