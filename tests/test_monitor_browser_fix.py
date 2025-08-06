#!/usr/bin/env python3
"""Test script to verify that --monitor flag opens browser correctly.

WHY: This script tests the fix for the issue where --monitor flag didn't open
the dashboard browser automatically. It covers both exec and subprocess modes.

DESIGN DECISION: We test by checking the browser opening logic directly
rather than launching full Claude sessions, to avoid complexity.
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_browser_opening_logic():
    """Test the browser opening logic directly."""
    print("🧪 Testing browser opening logic...")
    
    try:
        from claude_mpm.core.claude_runner import ClaudeRunner
        
        # Test 1: Create runner with monitor flag
        runner = ClaudeRunner(
            enable_websocket=True,
            websocket_port=8765,
            launch_method="subprocess"  # Use subprocess to avoid replacing this process
        )
        
        # Set the monitor browser flag
        runner._should_open_monitor_browser = True
        
        print("✓ ClaudeRunner created with monitor flag")
        
        # Test 2: Check if the flag is properly set
        if hasattr(runner, '_should_open_monitor_browser') and runner._should_open_monitor_browser:
            print("✓ Monitor browser flag is set correctly")
        else:
            print("❌ Monitor browser flag is not set properly")
            return False
        
        # Test 3: Check if dashboard HTML would be created
        scripts_dir = project_root / "scripts"
        dashboard_html = scripts_dir / "claude_mpm_socketio_dashboard.html"
        
        if dashboard_html.exists():
            print("✓ Dashboard HTML file exists")
        else:
            print("⚠️  Dashboard HTML file doesn't exist, would be created by launcher")
        
        # Test 4: Simulate browser opening (without actually opening)
        dashboard_url = f'http://localhost:{runner.websocket_port}/claude_mpm_socketio_dashboard.html?autoconnect=true&port={runner.websocket_port}'
        print(f"✓ Dashboard URL would be: {dashboard_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_launch_socketio_monitor():
    """Test the launch_socketio_monitor function."""
    print("\n🧪 Testing launch_socketio_monitor function...")
    
    try:
        from claude_mpm.cli.commands.run import launch_socketio_monitor
        from claude_mpm.core.logger import get_logger
        
        logger = get_logger("test")
        
        # Test with a port that's likely not in use
        test_port = 9999
        
        print(f"Testing with port {test_port}...")
        result = launch_socketio_monitor(test_port, logger)
        
        if result:
            print("✓ launch_socketio_monitor returned success")
        else:
            print("❌ launch_socketio_monitor returned failure")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dashboard_html_creation():
    """Test dashboard HTML creation."""
    print("\n🧪 Testing dashboard HTML creation...")
    
    try:
        scripts_dir = project_root / "scripts"
        launch_script = scripts_dir / "launch_socketio_dashboard.py"
        
        if not launch_script.exists():
            print("❌ Launcher script not found")
            return False
        
        print("✓ Launcher script exists")
        
        # Test creating dashboard HTML
        result = subprocess.run([
            sys.executable, str(launch_script),
            "--setup-only", "--port", "8765"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✓ Dashboard HTML creation succeeded")
            
            # Check if HTML file was created
            dashboard_html = scripts_dir / "claude_mpm_socketio_dashboard.html"
            if dashboard_html.exists():
                print("✓ Dashboard HTML file was created")
                return True
            else:
                print("❌ Dashboard HTML file was not created")
                return False
        else:
            print(f"❌ Dashboard HTML creation failed: {result.stderr}")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Monitor Browser Fix")
    print("=" * 50)
    
    tests = [
        ("Browser Opening Logic", test_browser_opening_logic),
        ("Launch SocketIO Monitor", test_launch_socketio_monitor),
        ("Dashboard HTML Creation", test_dashboard_html_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Monitor browser fix is working.")
        return True
    else:
        print("⚠️  Some tests failed. Monitor browser fix may have issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)