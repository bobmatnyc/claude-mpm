#!/usr/bin/env python3
"""Debug test for module viewer updates."""

import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🔍 Module Viewer Debug Test")
    print("=" * 50)
    
    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\nOpening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)
    
    print("\n📝 Generating test events...")
    
    # Generate a few quick events
    test_commands = [
        "echo 'Test event 1'",
        "echo 'Test event 2'", 
        "echo 'Test event 3'"
    ]
    
    for i, cmd in enumerate(test_commands):
        print(f"\n  Event {i+1}: {cmd}")
        subprocess.run([
            sys.executable, "-m", "claude_mpm", "run",
            "-i", cmd,
            "--non-interactive",
            "--monitor"
        ], cwd=Path(__file__).parent.parent, capture_output=True, timeout=10)
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print("🔍 DEBUGGING INSTRUCTIONS")
    print("=" * 50)
    
    print("\n1. Open the browser Developer Console (F12)")
    print("2. Click on the dashboard to focus it")
    print("3. Press the down arrow key")
    print("4. Check console for these messages:")
    print("   - 'Arrow navigation: 1 from X to Y'")
    print("   - 'Selected event: Y [event type]'")
    print("\n5. The module viewer should update showing:")
    print("   - Event class header")
    print("   - Event type cards")
    print("   - Related event details")
    
    print("\n🐛 If module viewer is NOT updating:")
    print("   - Check console for errors")
    print("   - Verify selectedEventIndex changes")
    print("   - Check if updateModuleViewer() is called")

if __name__ == "__main__":
    main()