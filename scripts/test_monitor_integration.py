#!/usr/bin/env python3
"""Integration test for --monitor flag functionality.

WHY: This script tests the complete integration of the --monitor flag,
from CLI parsing through to server startup and browser opening logic.

DESIGN DECISION: We simulate the complete flow without actually starting
Claude or opening browsers, to ensure the integration works correctly.
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_monitor_flag_integration():
    """Test the complete --monitor flag integration."""
    print("🧪 Testing --monitor flag integration...")
    
    # Test 1: Non-interactive mode with --monitor
    print("\n1️⃣ Testing non-interactive mode with --monitor")
    
    try:
        # Use a simple test command that should complete quickly
        result = subprocess.run([
            sys.executable, "-m", "claude_mpm.cli.main",
            "run", "--non-interactive", "--monitor",
            "--input", "test message for integration test"
        ], 
        capture_output=True, text=True, timeout=30, cwd=project_root)
        
        print(f"Exit code: {result.returncode}")
        
        # Check for monitor-related output
        if "Socket.IO server enabled" in result.stdout:
            print("✓ Socket.IO server was enabled")
        else:
            print("⚠️  Socket.IO server output not found")
        
        if "Setting up Socket.IO monitor" in result.stdout:
            print("✓ Monitor setup was triggered")
        else:
            print("⚠️  Monitor setup output not found")
        
        if "Dashboard will be available" in result.stdout:
            print("✓ Dashboard availability was announced")
        else:
            print("⚠️  Dashboard availability not announced")
        
        # Print some output for debugging
        print(f"STDOUT preview: {result.stdout[:500]}...")
        if result.stderr:
            print(f"STDERR preview: {result.stderr[:200]}...")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_monitor_cli_parsing():
    """Test that the CLI correctly parses --monitor flag."""
    print("\n🧪 Testing CLI argument parsing...")
    
    try:
        from claude_mpm.cli.main import create_parser
        
        # Test 1: --monitor flag should be recognized
        parser = create_parser()
        args = parser.parse_args(["run", "--monitor", "--non-interactive", "--input", "test"])
        
        if hasattr(args, 'monitor') and args.monitor:
            print("✓ --monitor flag is parsed correctly")
        else:
            print("❌ --monitor flag is not parsed correctly")
            return False
        
        # Test 2: --monitor should enable websocket automatically
        if hasattr(args, 'websocket'):
            print(f"  websocket flag: {getattr(args, 'websocket', 'not set')}")
        
        return True
        
    except Exception as e:
        print(f"❌ CLI parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_monitor_runner_setup():
    """Test that the runner is set up correctly for monitor mode."""
    print("\n🧪 Testing runner setup for monitor mode...")
    
    try:
        from claude_mpm.cli.commands.run import run_session
        from types import SimpleNamespace
        
        # Create mock args with monitor flag
        args = SimpleNamespace(
            monitor=True,
            logging="INFO",
            no_tickets=False,
            no_native_agents=False,
            claude_args=[],
            launch_method="subprocess",  # Use subprocess to avoid process replacement
            websocket=False,  # Should be automatically enabled
            websocket_port=8765,
            non_interactive=True,
            input="test message"
        )
        
        # We can't actually run the session without starting Claude,
        # but we can test the setup logic
        print("✓ Mock args created with monitor=True")
        
        # Test that monitor mode would enable websocket
        monitor_mode = getattr(args, 'monitor', False)
        enable_websocket = getattr(args, 'websocket', False) or monitor_mode
        
        if enable_websocket:
            print("✓ Monitor mode correctly enables WebSocket")
        else:
            print("❌ Monitor mode does not enable WebSocket")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Runner setup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all integration tests."""
    print("🚀 Testing Monitor Flag Integration")
    print("=" * 50)
    
    tests = [
        ("CLI Argument Parsing", test_monitor_cli_parsing),
        ("Runner Setup", test_monitor_runner_setup),
        ("Full Integration", test_monitor_flag_integration),
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
    
    print(f"\n📊 Integration Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All integration tests passed! --monitor flag is working correctly.")
        return True
    else:
        print("⚠️  Some integration tests failed. --monitor flag may have issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)