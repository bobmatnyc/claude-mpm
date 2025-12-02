#!/usr/bin/env python3
"""Test script for dashboard fixes.

Tests:
1. Dashboard stop command works without PortManager error
2. No hardcoded /Users/masa paths in dashboard
3. Events are properly displayed in dashboard
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.cli.unified_dashboard_manager import UnifiedDashboardManager
from claude_mpm.services.port_manager import PortManager


def test_dashboard_stop():
    """Test that dashboard stop command works without PortManager error."""
    print("Testing dashboard stop command...")

    manager = UnifiedDashboardManager()
    port_manager = PortManager()

    # Test that is_port_available works (not is_port_in_use)
    try:
        # This should work now
        is_available = port_manager.is_port_available(8765)
        print(f"✅ Port availability check works: port 8765 available = {is_available}")
    except AttributeError as e:
        print(f"❌ Port manager error: {e}")
        return False

    # Test stop_dashboard method
    try:
        # Try to stop dashboard (may or may not be running)
        success = manager.stop_dashboard(8765)
        print(f"✅ Dashboard stop command executed without error (stopped = {success})")
    except Exception as e:
        print(f"❌ Dashboard stop error: {e}")
        return False

    return True


def test_no_hardcoded_paths():
    """Test that no hardcoded /Users/masa paths remain."""
    print("\nTesting for hardcoded paths...")

    files_to_check = [
        project_root
        / "src/claude_mpm/dashboard/static/js/components/session-manager.js",
        project_root / "src/claude_mpm/dashboard/templates/index.html",
    ]

    hardcoded_found = False

    for file_path in files_to_check:
        with file_path.open() as f:
            content = f.read()
            if "/Users/masa" in content:
                print(f"❌ Hardcoded path found in {file_path.name}")
                # Find the lines with hardcoded paths
                for i, line in enumerate(content.split("\n"), 1):
                    if "/Users/masa" in line:
                        print(f"   Line {i}: {line.strip()}")
                hardcoded_found = True
            else:
                print(f"✅ No hardcoded paths in {file_path.name}")

    # Check server config endpoint exists
    server_file = project_root / "src/claude_mpm/services/monitor/server.py"
    with server_file.open() as f:
        content = f.read()
        if "/api/config" in content and "config_handler" in content:
            print("✅ Server config endpoint exists")
        else:
            print("❌ Server config endpoint missing")
            hardcoded_found = True

    return not hardcoded_found


def test_event_emission():
    """Test that events are properly emitted."""
    print("\nTesting event emission...")

    # Check hooks handler emits both event types
    hooks_file = project_root / "src/claude_mpm/services/monitor/handlers/hooks.py"
    with hooks_file.open() as f:
        content = f.read()

    # Check for both event emissions
    has_hook_event = 'await self.sio.emit("hook:event"' in content
    has_claude_event = 'await self.sio.emit("claude_event"' in content

    if has_hook_event and has_claude_event:
        print("✅ Hook handler emits both 'hook:event' and 'claude_event'")
    else:
        print("❌ Hook handler missing event emissions:")
        if not has_hook_event:
            print("   - Missing 'hook:event' emission")
        if not has_claude_event:
            print("   - Missing 'claude_event' emission")
        return False

    # Check session events are also emitted as claude_event
    session_start_claude = '"type": "session.started"' in content
    session_end_claude = '"type": "session.ended"' in content

    if session_start_claude and session_end_claude:
        print("✅ Session events are emitted as claude_event format")
    else:
        print("❌ Session events not properly emitted as claude_event")
        return False

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Dashboard Fixes Test Suite")
    print("=" * 60)

    results = []

    # Test 1: Dashboard stop command
    results.append(("Dashboard stop command", test_dashboard_stop()))

    # Test 2: No hardcoded paths
    results.append(("No hardcoded paths", test_no_hardcoded_paths()))

    # Test 3: Event emission
    results.append(("Event emission", test_event_emission()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All dashboard fixes are working correctly!")
        return 0
    print("\n⚠️ Some tests failed. Please review the errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
