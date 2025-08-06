#!/usr/bin/env python3
"""Simple footer display test for Claude MPM dashboard."""

import webbrowser
import time
import sys
import os
from pathlib import Path

def test_footer_display():
    """Test footer display by opening the dashboard."""
    
    print("🧪 Testing Footer Display")
    print("=" * 50)
    
    # Find the dashboard file
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    
    if not dashboard_path.exists():
        print("❌ Dashboard file not found!")
        return False
    
    print(f"✅ Found dashboard: {dashboard_path}")
    
    # Open in browser with autoconnect
    url = f"file://{dashboard_path}?autoconnect=true"
    print(f"🌐 Opening dashboard: {url}")
    
    webbrowser.open(url)
    
    print("\n📋 Footer Display Checklist:")
    print("□ Footer visible at bottom of page")
    print("□ Dark semi-transparent background")
    print("□ Three sections: Session | Directory | Branch")
    print("□ Session shows 'Not connected' or session ID")
    print("□ Directory shows 'Unknown' or current path")
    print("□ Branch shows 'Unknown' or git branch")
    print("□ Footer stays fixed when scrolling")
    print("□ Hover over values shows full text")
    
    print("\n💡 Tips:")
    print("1. Connect to see real session data")
    print("2. Footer should update automatically on connection")
    print("3. Check browser console for any errors")
    
    print("\n✨ Test complete - check browser!")
    return True

if __name__ == "__main__":
    success = test_footer_display()
    sys.exit(0 if success else 1)