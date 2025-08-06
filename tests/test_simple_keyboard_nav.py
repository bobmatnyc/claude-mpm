#!/usr/bin/env python3
"""Simple test for keyboard navigation."""

import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🎹 Keyboard Navigation Test")
    print("=" * 50)
    
    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\nOpening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    
    print("\n✅ Dashboard opened with keyboard navigation enabled!")
    print("\n🎹 Keyboard Shortcuts:")
    print("   ↑/↓     - Navigate through events")
    print("   Enter   - Show details of selected event") 
    print("   Ctrl+K  - Focus search box")
    print("   Esc     - Close modal")
    
    print("\n📝 Try it out:")
    print("1. Click on the dashboard to focus it")
    print("2. Use arrow keys to navigate")
    print("3. Watch the blue highlight move")
    print("4. Module viewer updates automatically")
    print("5. Selected event scrolls into view")

if __name__ == "__main__":
    main()