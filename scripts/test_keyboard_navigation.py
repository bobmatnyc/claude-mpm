#!/usr/bin/env python3
"""Test keyboard navigation in the dashboard."""

import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🎹 Testing Keyboard Navigation")
    print("=" * 50)
    
    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\n1. Opening dashboard...")
    webbrowser.open(dashboard_url)
    time.sleep(3)
    
    print("\n2. Generating test events...")
    
    # Generate a variety of events to test navigation
    test_prompts = [
        ("Quick test 1", "echo 'Test 1'"),
        ("Research task", "Use the Task tool to ask the research agent to analyze keyboard navigation patterns"),
        ("Engineer task", "Use the Task tool to ask the engineer agent to implement a simple function"),
        ("Quick test 2", "echo 'Test 2'"),
        ("PM coordination", "Use the Task tool to ask the pm agent about project status")
    ]
    
    for desc, prompt in test_prompts:
        print(f"\n🔸 {desc}...")
        cmd = [
            sys.executable, "-m", "claude_mpm", "run",
            "-i", prompt,
            "--non-interactive",
            "--monitor"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"   ✅ Success")
        else:
            print(f"   ❌ Error: {result.stderr[:50]}")
        
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print("📊 KEYBOARD NAVIGATION GUIDE")
    print("=" * 50)
    
    print("\n🎹 Available Keyboard Shortcuts:")
    print("   ↑/↓     - Navigate through events")
    print("   Enter   - Show details of selected event")
    print("   Ctrl+K  - Focus search box")
    print("   Ctrl+E  - Export events")
    print("   Ctrl+R  - Clear all events")
    print("   Escape  - Close modal")
    
    print("\n📝 Testing Instructions:")
    print("1. Click on the dashboard window to focus it")
    print("2. Use ↑/↓ arrow keys to navigate through events")
    print("3. Watch the left module viewer update as you navigate")
    print("4. Selected event will be highlighted in blue")
    print("5. Press Enter to view full details")
    
    print("\n🔍 What to Look For:")
    print("- Blue highlight moves with arrow keys")
    print("- Module viewer updates instantly")
    print("- Smooth scrolling when moving off-screen")
    print("- Wrapping at top/bottom of list")
    
    print("\n✨ Keyboard navigation is now active!")

if __name__ == "__main__":
    main()