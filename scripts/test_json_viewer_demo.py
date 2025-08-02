#!/usr/bin/env python3
"""Interactive JSON viewer test that creates events with rich data."""

import subprocess
import time
import webbrowser
import json
from pathlib import Path
import sys
import requests

def create_test_event():
    """Create a test event with rich JSON data via WebSocket."""
    
    # Create a test event with complex JSON structure
    test_data = {
        "event_type": "test.json_viewer",
        "timestamp": time.time(),
        "data": {
            "user": {
                "id": 12345,
                "name": "Test User",
                "email": "test@example.com",
                "active": True,
                "roles": ["admin", "developer", "tester"]
            },
            "system": {
                "version": "1.2.3",
                "environment": "development",
                "features": {
                    "json_viewer": True,
                    "syntax_highlighting": True,
                    "keyboard_navigation": True,
                    "module_viewer": True
                }
            },
            "metrics": {
                "cpu_usage": 45.2,
                "memory_mb": 1024,
                "active_connections": 3,
                "null_value": None
            },
            "arrays": {
                "numbers": [1, 2, 3, 4, 5],
                "strings": ["alpha", "beta", "gamma"],
                "mixed": [1, "two", 3.14, True, None]
            }
        }
    }
    
    # Send via WebSocket using curl
    payload = {
        "event": "client_event",
        "data": test_data
    }
    
    try:
        # Write payload to temp file
        temp_file = Path("/tmp/test_event.json")
        temp_file.write_text(json.dumps(payload))
        
        # Send via curl to WebSocket endpoint
        cmd = [
            "curl", "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", f"@{temp_file}",
            "http://localhost:8765/socket.io/?EIO=4&transport=polling"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"Event sent: {result.returncode == 0}")
        
    except Exception as e:
        print(f"Error sending event: {e}")

def main():
    print("🧪 JSON Viewer Interactive Test")
    print("=" * 50)
    
    # Check if WebSocket server is running
    try:
        response = requests.get("http://localhost:8765/socket.io/?EIO=4&transport=polling", timeout=2)
        print("✅ WebSocket server is running")
    except:
        print("❌ WebSocket server is not running!")
        print("Please start the server with: ./scripts/start_socketio_server_manual.py")
        return
    
    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\n📊 Opening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)
    
    print("\n" + "=" * 50)
    print("📋 JSON VIEWER TEST INSTRUCTIONS")
    print("=" * 50)
    
    print("\n1️⃣  SETUP:")
    print("   - Dashboard should be open in your browser")
    print("   - Connection status should show 'Connected'")
    print("   - Events tab should be selected")
    
    print("\n2️⃣  GENERATING TEST EVENTS:")
    print("   Press Enter to generate test events with rich JSON data...")
    input()
    
    # Generate multiple test events
    for i in range(3):
        print(f"\n   Generating test event {i+1}...")
        create_test_event()
        time.sleep(0.5)
        
        # Also generate a real event
        cmd = [
            sys.executable, "-m", "claude_mpm", "run",
            "-i", f"echo 'Test event {i+1} for JSON viewer'",
            "--non-interactive",
            "--monitor",
            "--timeout", "5"
        ]
        
        subprocess.Popen(
            cmd,
            cwd=Path(__file__).parent.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(1)
    
    print("\n3️⃣  VIEWING JSON DATA:")
    print("   - Click on any event in the Events list")
    print("   - Look at the Event Analysis panel (left side)")
    print("   - Scroll down to see '📋 Full Event JSON' section")
    
    print("\n4️⃣  JSON VIEWER FEATURES:")
    print("   ✨ Syntax Highlighting:")
    print("      - Keys: Blue (#0969da)")
    print("      - String values: Dark blue (#0a3069)")
    print("      - Numbers: Blue (#0550ae)")
    print("      - Booleans: Red (#cf222e)")
    print("      - Null: Gray (#6e7781)")
    
    print("\n   📜 Scrollable View:")
    print("      - Large JSON objects are scrollable")
    print("      - Max height: 400px")
    print("      - Horizontal scroll for long lines")
    
    print("\n   ⌨️  Keyboard Navigation:")
    print("      - ↑/↓ Arrow keys: Navigate events")
    print("      - Selected event JSON updates automatically")
    
    print("\n5️⃣  WHAT TO CHECK:")
    print("   ✓ JSON formatting with proper indentation")
    print("   ✓ Syntax highlighting for different data types")
    print("   ✓ Nested objects and arrays display correctly")
    print("   ✓ Special values (null, boolean) are highlighted")
    print("   ✓ Scrolling works for large JSON objects")
    
    print("\n" + "=" * 50)
    print("🎯 Test the JSON viewer now in the dashboard!")
    print("Press Ctrl+C when done testing.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n✅ JSON viewer test completed!")

if __name__ == "__main__":
    main()