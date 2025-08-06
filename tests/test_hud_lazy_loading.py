#!/usr/bin/env python3
"""
Test HUD lazy loading functionality.

This script launches the Socket.IO server and opens the dashboard
to test the new lazy loading functionality for HUD visualization libraries.
"""

import sys
import time
import webbrowser
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.socketio_server import SocketIOServer

def main():
    """Launch server and open dashboard for HUD lazy loading testing."""
    
    print("🚀 Starting Socket.IO server for HUD lazy loading testing...")
    
    # Start server
    server = SocketIOServer(port=8765)
    server.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Open dashboard in browser
    dashboard_url = "http://localhost:8765"
    print(f"📊 Opening dashboard at {dashboard_url}")
    print("\n" + "="*70)
    print("HUD LAZY LOADING Testing Instructions:")
    print("="*70)
    print("1. The dashboard should open in your browser")
    print("2. Open browser dev tools (F12) and check the Console tab")
    print("3. In Network tab, note that Cytoscape.js libraries are NOT loaded initially")
    print("4. Connect to the Socket.IO server if not auto-connected")
    print("5. Select a session from the dropdown")
    print("6. Click the HUD button - this should trigger lazy loading")
    print("7. Watch the Console for loading messages:")
    print("   - 'Loading HUD visualization libraries...'")
    print("   - Progress messages for each library")
    print("   - 'All HUD libraries loaded successfully'")
    print("8. In Network tab, verify these libraries were loaded:")
    print("   - cytoscape@3.26.0/dist/cytoscape.min.js")
    print("   - dagre@0.8.5/dist/dagre.min.js") 
    print("   - cytoscape-dagre@2.5.0/cytoscape-dagre.js")
    print("9. Verify loading indicator appears during library loading")
    print("10. After loading, HUD visualization should appear")
    print("11. Toggle HUD off and on again - libraries should NOT reload")
    print("12. Test error handling by blocking network requests")
    print("="*70)
    print("\nWhat to verify:")
    print("✓ Libraries load in correct order: cytoscape → dagre → cytoscape-dagre")
    print("✓ Loading spinner and progress bar appear")
    print("✓ Libraries are cached (no reload on subsequent HUD activations)")
    print("✓ Error states show retry button if loading fails")
    print("✓ Pending events are processed after libraries load")
    print("✓ All dependencies are properly available before dagre layout")
    print("="*70)
    print("\nPress Ctrl+C to stop the server...")
    
    try:
        webbrowser.open(dashboard_url)
        
        # Keep server running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
        server.stop()
        print("✅ Server stopped")

if __name__ == "__main__":
    main()