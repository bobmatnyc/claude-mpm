#!/usr/bin/env python3
"""Simple test to demonstrate the JSON viewer functionality."""

import webbrowser
from pathlib import Path
import time

def main():
    print("📋 Testing JSON Event Viewer")
    print("=" * 50)
    
    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}"
    
    print(f"\n✅ Opening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    
    print("\n" + "=" * 50)
    print("📋 JSON VIEWER FEATURES")
    print("=" * 50)
    
    print("\n✨ What the JSON Viewer Does:")
    print("- Displays full JSON object below event summary cards")
    print("- Provides syntax highlighting for better readability")
    print("- Shows all event data in a scrollable, formatted view")
    print("- Preserves complete event structure for inspection")
    
    print("\n🎨 Syntax Highlighting Colors:")
    print("- Keys: Blue (#0969da)")
    print("- String values: Dark blue (#0a3069)")
    print("- Numbers: Blue (#0550ae)")
    print("- Booleans: Red (#cf222e)")
    print("- Null values: Gray (#6e7781)")
    
    print("\n📝 How to Test the JSON Viewer:")
    print("1. Connect to the WebSocket server (click Connect)")
    print("2. Generate some events (use claude-mpm with --monitor)")
    print("3. Click on any event in the Events tab")
    print("4. Look at the Event Analysis panel (left side)")
    print("5. Scroll down to see '📋 Full Event JSON' section")
    
    print("\n🔍 What You Can Inspect in JSON:")
    print("- Event type and timestamp")
    print("- Session IDs and correlation data")
    print("- Agent information and tool parameters")
    print("- Tool results and error messages")
    print("- Any custom data in the event payload")
    
    print("\n💡 Navigation Tips:")
    print("- Use ↑/↓ arrow keys to navigate between events")
    print("- Selected event is highlighted in light blue")
    print("- JSON view updates automatically with selection")
    print("- Event summary cards show key information at a glance")
    
    print("\n✅ JSON Viewer is Ready!")
    print("The dashboard is now open in your browser.")
    print("Generate some events to see the JSON viewer in action.")

if __name__ == "__main__":
    main()