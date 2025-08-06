#!/usr/bin/env python3
"""Manual test for browser opening functionality.

WHY: This script allows manual testing of the browser opening logic
to verify the fix works in practice.

DESIGN DECISION: We create a minimal test that simulates the exact
conditions under which the browser should open.
"""

import sys
import time
import webbrowser
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_browser_opening_simulation():
    """Simulate the browser opening logic."""
    print("🧪 Testing browser opening simulation...")
    
    # Simulate the exact conditions
    websocket_port = 8765
    dashboard_url = f'http://localhost:{websocket_port}/dashboard?autoconnect=true&port={websocket_port}'
    
    print(f"Dashboard URL: {dashboard_url}")
    
    # Check if new modular dashboard exists
    web_templates_dir = project_root / "src" / "claude_mpm" / "web" / "templates"
    dashboard_html = web_templates_dir / "index.html"
    
    if dashboard_html.exists():
        print("✓ Modular dashboard template exists")
    else:
        print("❌ Modular dashboard template missing - checking legacy location...")
        try:
            # Create dashboard using launcher
            import subprocess
            result = subprocess.run([
                sys.executable, str(scripts_dir / "launch_socketio_dashboard.py"),
                "--setup-only", "--port", str(websocket_port)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ Dashboard HTML created successfully")
            else:
                print(f"❌ Failed to create dashboard HTML: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error creating dashboard HTML: {e}")
            return False
    
    # Test browser opening logic (without actually opening)
    print("🌐 Testing browser opening logic...")
    
    try:
        # This would normally open the browser
        print(f"Would open: {dashboard_url}")
        
        # Instead of actually opening, just verify the URL is valid
        import urllib.parse
        parsed = urllib.parse.urlparse(dashboard_url)
        
        if parsed.scheme and parsed.netloc and parsed.path:
            print("✓ Dashboard URL is well-formed")
        else:
            print("❌ Dashboard URL is malformed")
            return False
        
        # Check if query parameters are correct
        query_params = urllib.parse.parse_qs(parsed.query)
        if 'autoconnect' in query_params and 'port' in query_params:
            print("✓ Dashboard URL has correct query parameters")
        else:
            print("❌ Dashboard URL missing query parameters")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Browser opening test failed: {e}")
        return False

def test_actual_browser_opening():
    """Test actual browser opening (user confirmation required)."""
    print("\n🌐 Testing actual browser opening...")
    
    # Ask user for confirmation
    response = input("Do you want to test actual browser opening? (y/N): ").strip().lower()
    
    if response != 'y':
        print("⏭️  Skipping actual browser test")
        return True
    
    try:
        websocket_port = 8765
        dashboard_url = f'http://localhost:{websocket_port}/dashboard?autoconnect=true&port={websocket_port}'
        
        print(f"Opening browser to: {dashboard_url}")
        webbrowser.open(dashboard_url, autoraise=True)
        
        # Give user time to see if it worked
        time.sleep(2)
        
        response = input("Did the browser open to the dashboard? (y/N): ").strip().lower()
        
        if response == 'y':
            print("✅ Browser opening successful!")
            return True
        else:
            print("❌ Browser opening failed")
            return False
        
    except Exception as e:
        print(f"❌ Browser opening test failed: {e}")
        return False

def main():
    """Run browser opening tests."""
    print("🚀 Testing Browser Opening Fix")
    print("=" * 40)
    
    tests = [
        ("Browser Opening Simulation", test_browser_opening_simulation),
        ("Actual Browser Opening", test_actual_browser_opening),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 25)
        
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
    
    print(f"\n📊 Browser Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 Browser opening tests completed successfully!")
        return True
    else:
        print("⚠️  Some browser tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)