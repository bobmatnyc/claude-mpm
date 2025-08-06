#!/usr/bin/env python3
"""
Test HUD Debugging Script

This script provides instructions and verification for testing the HUD debugging.
"""

import os
import webbrowser
from pathlib import Path

def main():
    project_root = Path(__file__).parent.parent
    debug_html_path = project_root / "debug_hud.html"
    
    print("🔬 HUD Debugging Test Instructions")
    print("=" * 50)
    
    print("\n📋 Testing Steps:")
    print("1. Open the debug HTML page in your browser")
    print("2. Open browser Developer Tools (F12)")
    print("3. Go to the Console tab")
    print("4. Run the test buttons and observe the logs")
    
    print(f"\n🌐 Debug page location: {debug_html_path}")
    
    if debug_html_path.exists():
        print("✅ Debug HTML file exists")
        
        # Ask if user wants to open it
        response = input("\nWould you like to open the debug page now? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            try:
                webbrowser.open(f"file://{debug_html_path}")
                print("✅ Opened debug page in browser")
            except Exception as e:
                print(f"❌ Could not open browser: {e}")
                print(f"   Please manually open: file://{debug_html_path}")
        else:
            print(f"   Please manually open: file://{debug_html_path}")
            
    else:
        print("❌ Debug HTML file not found")
        print("   Run: python scripts/debug_hud_data_flow.py")
        return
    
    print("\n🔍 What to Look For:")
    print("- Library loading status (should show green checkmarks)")
    print("- Component availability (HUDVisualizer, HUDManager classes)")
    print("- Sample data generation and processing")
    print("- Event filtering by session")
    print("- Node creation in visualization")
    
    print("\n📝 Console Debug Messages to Watch:")
    print("- [HUD-DEBUG] messages from the debug page")
    print("- [HUD-VISUALIZER-DEBUG] messages from the visualizer")
    print("- [HUD-MANAGER-DEBUG] messages from the manager")
    
    print("\n🎯 Common Issues to Check:")
    print("1. Libraries not loading:")
    print("   - Check network connectivity")
    print("   - Verify CDN URLs are accessible")
    
    print("\n2. No events being processed:")
    print("   - Check if events array is empty")
    print("   - Verify session filtering logic")
    print("   - Check event structure matches expected format")
    
    print("\n3. No nodes appearing in visualization:")
    print("   - Check if createNodeFromEvent returns null")
    print("   - Verify addNode is being called")
    print("   - Check if Cytoscape container is visible")
    
    print("\n4. Events filtered out:")
    print("   - Check session ID matching logic") 
    print("   - Verify selectedSessionId is set correctly")
    print("   - Check event.session_id vs event.data.session_id")
    
    print("\n🚀 Next Steps After Debugging:")
    print("1. Test with the actual dashboard at http://localhost:8080")
    print("2. Connect to Claude MPM Socket.IO server")
    print("3. Select a session and activate HUD mode")
    print("4. Check browser console for debug messages")
    
    print("\n💡 Tips:")
    print("- Clear browser cache if you see old JavaScript")
    print("- Use browser's Network tab to check for failed script loads")
    print("- Test with a fresh browser session/incognito mode")

if __name__ == "__main__":
    main()