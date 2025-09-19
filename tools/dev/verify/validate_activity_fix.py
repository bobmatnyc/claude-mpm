#!/usr/bin/env python3
"""
Validation script for the Activity Tree session fix.
"""

import json
import os
import re
from pathlib import Path


def test_activity_tree_fix():
    """Test that Activity Tree uses authoritative sessions."""
    print("🧪 Testing Activity Tree Session Fix")
    print("=" * 50)

    # Path to the fixed activity-tree.js file
    activity_tree_path = (
        Path(__file__).parent
        / "src/claude_mpm/dashboard/static/js/components/activity-tree.js"
    )

    if not activity_tree_path.exists():
        print("❌ Activity Tree source file not found")
        return False

    # Read the source code
    with open(activity_tree_path, encoding="utf-8") as f:
        content = f.read()

    tests_passed = 0
    total_tests = 6

    # Test 1: Check if onEventUpdate callback receives both events and sessions
    print("\n1. Testing onEventUpdate callback signature...")
    if re.search(r"onEventUpdate\(\s*\(\s*events\s*,\s*sessions\s*\)\s*=>", content):
        print(
            "   ✅ onEventUpdate callback correctly receives both events and sessions"
        )
        tests_passed += 1
    else:
        print("   ❌ onEventUpdate callback does not receive sessions parameter")

    # Test 2: Check if sessions are cleared and rebuilt from authoritative source
    print("\n2. Testing session clearing and rebuilding...")
    if (
        "this.sessions.clear()" in content
        and "for (const [sessionId, sessionData] of sessions.entries())" in content
    ):
        print("   ✅ Sessions are cleared and rebuilt from authoritative source")
        tests_passed += 1
    else:
        print("   ❌ Sessions are not properly cleared and rebuilt")

    # Test 3: Check if getSessionId method was removed
    print("\n3. Testing removal of custom getSessionId method...")
    if "getSessionId method removed" in content:
        print(
            "   ✅ Custom getSessionId method removed (now uses authoritative session IDs)"
        )
        tests_passed += 1
    elif "getSessionId(" not in content:
        print("   ✅ Custom getSessionId method not found (good)")
        tests_passed += 1
    else:
        print("   ❌ Custom getSessionId method still present")

    # Test 4: Check if events without session_id are skipped
    print("\n4. Testing session ID validation...")
    if (
        "event.session_id || event.data?.session_id" in content
        and "Skipping event without session_id" in content
    ):
        print("   ✅ Events without session_id are properly skipped")
        tests_passed += 1
    else:
        print("   ❌ Session ID validation not implemented properly")

    # Test 5: Check if session filter dropdown uses socket client data
    print("\n5. Testing session filter dropdown data source...")
    if (
        "window.socketClient?.getState()?.sessions" in content
        and "matching Events view format" in content
    ):
        print("   ✅ Session filter dropdown uses socket client data")
        tests_passed += 1
    else:
        print("   ❌ Session filter dropdown does not use socket client data")

    # Test 6: Check if initial data loading uses socket client
    print("\n6. Testing initial data loading...")
    if "const socketState = window.socketClient?.getState()" in content:
        print("   ✅ Initial data loading uses socket client state")
        tests_passed += 1
    else:
        print("   ❌ Initial data loading does not use socket client state")

    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("🎉 All tests passed! Activity Tree fix is correctly implemented.")
        return True
    print("⚠️  Some tests failed. The fix may be incomplete.")
    return False


def test_built_files():
    """Test that the built files contain the fix."""
    print("\n🏗️  Testing Built Files")
    print("=" * 30)

    # Check built files
    built_path = (
        Path(__file__).parent
        / "src/claude_mpm/dashboard/static/built/components/activity-tree.js"
    )
    dist_path = (
        Path(__file__).parent
        / "src/claude_mpm/dashboard/static/dist/components/activity-tree.js"
    )

    if built_path.exists():
        print("✅ Built file exists at static/built/components/activity-tree.js")
        with open(built_path, encoding="utf-8") as f:
            built_content = f.read()
        if "onEventUpdate((events,sessions)" in built_content.replace(" ", ""):
            print("✅ Built file contains session fix")
        else:
            print("❌ Built file does not contain session fix")
    else:
        print("❌ Built file not found")

    if dist_path.exists():
        print("✅ Dist file exists at static/dist/components/activity-tree.js")
        with open(dist_path, encoding="utf-8") as f:
            dist_content = f.read()
        if "onEventUpdate((events,sessions)" in dist_content.replace(" ", ""):
            print("✅ Dist file contains session fix")
        else:
            print("❌ Dist file does not contain session fix")
    else:
        print("❌ Dist file not found")


def main():
    """Run all tests."""
    print("Activity Tree Session Fix Validation")
    print("=" * 40)

    # Test source code
    source_tests_passed = test_activity_tree_fix()

    # Test built files
    test_built_files()

    print("\n📋 Summary")
    print("=" * 20)

    if source_tests_passed:
        print("✅ Source code fix validated successfully")
        print(
            "ℹ️  The Activity Tree now uses the same authoritative session data as the Events view"
        )
        print("ℹ️  Both views should show identical session lists")
    else:
        print("❌ Source code fix validation failed")
        print("⚠️  Manual review required")

    print("\n🔧 Next Steps:")
    print(
        "1. Open the dashboard and compare the Activity and Events view session dropdowns"
    )
    print("2. Verify they show the same session list format")
    print("3. Test session filtering works correctly in Activity view")

    return source_tests_passed


if __name__ == "__main__":
    main()
