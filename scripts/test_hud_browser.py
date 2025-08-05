#!/usr/bin/env python3
"""
Browser-based testing for HUD functionality.
This test opens the dashboard in a browser and validates the HUD toggle behavior.
"""

import sys
import time
import json
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from claude_mpm.services.socketio_server import SocketIOServer
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

def test_browser_hud():
    """Test HUD functionality in browser."""
    if not IMPORTS_AVAILABLE:
        print("❌ Required imports not available")
        return False
    
    print("🚀 Starting Socket.IO server for browser testing...")
    
    # Use different port to avoid conflicts
    port = 8766
    server = SocketIOServer(port=port)
    
    # Start server in background thread
    def run_server():
        try:
            server.start()
        except Exception as e:
            print(f"Server error: {e}")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(3)
    
    # Open dashboard
    dashboard_url = f"http://localhost:{port}"
    print(f"📊 Opening dashboard at {dashboard_url}")
    
    print("\n" + "="*80)
    print("🧪 MANUAL HUD TESTING INSTRUCTIONS")
    print("="*80)
    print("Please perform the following tests in the browser that opens:")
    print("")
    print("1. 🔲 TOGGLE BUTTON BEHAVIOR:")
    print("   ✓ Verify HUD button appears next to Export button")
    print("   ✓ Confirm button is DISABLED when no session is selected") 
    print("   ✓ Check tooltip shows 'Select a session to enable HUD' when disabled")
    print("   ✓ Select any session from dropdown")
    print("   ✓ Verify button becomes ENABLED when session is selected")
    print("   ✓ Check tooltip changes to 'Toggle HUD visualizer'")
    print("")
    print("2. 🔄 HUD MODE ACTIVATION:")
    print("   ✓ Click HUD button to enter HUD mode")
    print("   ✓ Confirm lower pane is completely replaced by visualizer")
    print("   ✓ Verify upper pane (session manager, module viewer) remains unchanged")
    print("   ✓ Check button text changes to 'Normal View'")
    print("   ✓ Verify button has green color when active")
    print("")
    print("3. 📊 VISUALIZATION COMPONENTS:")
    print("   ✓ Verify Cytoscape.js visualization loads (should see canvas)")
    print("   ✓ Check that graph canvas fills the entire lower pane")
    print("   ✓ Look for 'Reset Layout' and 'Center View' buttons")
    print("   ✓ Test window resize - visualization should resize accordingly")
    print("")
    print("4. 🔵 NODE RENDERING (if events are present):")
    print("   ✓ PM nodes should be green rectangles with 👤 icon")
    print("   ✓ Agent nodes should be purple ellipses with 🤖 icon")
    print("   ✓ Tool nodes should be blue diamonds with 🔧 icon") 
    print("   ✓ Todo nodes should be red triangles with 📝 icon")
    print("")
    print("5. 🌳 TREE LAYOUT:")
    print("   ✓ Nodes should be arranged hierarchically (top to bottom)")
    print("   ✓ Tool calls should branch right from their parent nodes")
    print("   ✓ Agents should branch down from PM nodes")
    print("   ✓ Edges should connect related nodes with arrows")
    print("")
    print("6. 🔙 EXIT HUD MODE:")
    print("   ✓ Click 'Normal View' button to exit HUD")
    print("   ✓ Confirm lower pane returns to original tabbed layout")
    print("   ✓ Button text changes back to 'HUD'")
    print("   ✓ Button loses green color")
    print("")
    print("7. 📱 SESSION SWITCHING:")
    print("   ✓ While in HUD mode, change session selection")
    print("   ✓ Verify HUD exits automatically when session is deselected")
    print("   ✓ Button becomes disabled again")
    print("   ✓ Re-selecting session re-enables button")
    print("")
    print("8. ⚡ REAL-TIME UPDATES (if MPM is running):")
    print("   ✓ Run MPM commands to generate events")
    print("   ✓ Verify new nodes appear in HUD in real-time")
    print("   ✓ Check that relationships are correctly established")
    print("   ✓ Layout should auto-adjust for new nodes")
    print("")
    print("="*80)
    print("Press ENTER after completing all tests...")
    
    try:
        webbrowser.open(dashboard_url)
    except Exception as e:
        print(f"Could not open browser: {e}")
        print(f"Please manually navigate to: {dashboard_url}")
    
    # Wait for user to complete testing
    input()
    
    print("\n✅ Browser testing completed")
    print("Please report any issues found during manual testing")
    
    # Stop server
    try:
        server.stop()
    except:
        pass
    
    return True

def main():
    """Run browser HUD testing."""
    print("🧪 Starting browser-based HUD testing...")
    test_browser_hud()

if __name__ == "__main__":
    main()