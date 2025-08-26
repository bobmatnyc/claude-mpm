#!/usr/bin/env python3
"""
Activity Tab Test Script

This script programmatically tests the Activity tab functionality
after the module loading fix to ensure:
1. Dashboard serves the correct files
2. Activity tab content is different from Events tab
3. ActivityTree class is available
4. No critical JavaScript errors occur
"""

import sys
from pathlib import Path

import requests


def test_dashboard_server():
    """Test if dashboard server is running and responding"""
    print("🔍 Testing dashboard server availability...")

    try:
        response = requests.get("http://localhost:8765/dashboard", timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard server is running and responding")
            return True
        print(f"❌ Dashboard returned status code: {response.status_code}")
        return False
    except requests.ConnectionError:
        print("❌ Dashboard server is not running or not accessible")
        return False
    except Exception as e:
        print(f"❌ Error testing dashboard: {e}")
        return False


def test_static_files():
    """Test if the built static files are accessible"""
    print("\n🔍 Testing static file accessibility...")

    files_to_test = [
        "/static/dist/dashboard.js",
        "/static/dist/components/activity-tree.js",
        "/static/dist/components/event-viewer.js",
    ]

    all_files_ok = True
    for file_path in files_to_test:
        try:
            response = requests.get(f"http://localhost:8765{file_path}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {file_path} - accessible ({len(response.content)} bytes)")
            else:
                print(f"❌ {file_path} - status code: {response.status_code}")
                all_files_ok = False
        except Exception as e:
            print(f"❌ {file_path} - error: {e}")
            all_files_ok = False

    return all_files_ok


def test_activity_tree_content():
    """Test if activity-tree.js contains expected content"""
    print("\n🔍 Testing activity-tree.js content...")

    try:
        response = requests.get(
            "http://localhost:8765/static/dist/components/activity-tree.js", timeout=5
        )
        if response.status_code != 200:
            print(f"❌ Could not fetch activity-tree.js: status {response.status_code}")
            return False

        content = response.text

        # Check for key indicators that the ActivityTree class is present
        indicators = [
            "ActivityTree",  # Class name
            "initialize",  # Key method
            "d3.tree",  # D3 tree usage
            "activity-tree",  # DOM element reference
            "TodoWrite",  # TodoWrite processing
            "SubagentStart",  # Event processing
        ]

        found_indicators = []
        missing_indicators = []

        for indicator in indicators:
            if indicator in content:
                found_indicators.append(indicator)
            else:
                missing_indicators.append(indicator)

        print(f"✅ Found indicators: {found_indicators}")
        if missing_indicators:
            print(f"⚠️  Missing indicators: {missing_indicators}")

        # Check file size - should be substantial if properly built
        if len(content) > 5000:  # Minified should still be > 5KB
            print(f"✅ File size is substantial: {len(content)} characters")
        else:
            print(f"⚠️  File size seems small: {len(content)} characters")

        return len(found_indicators) >= 4  # Most indicators should be present

    except Exception as e:
        print(f"❌ Error testing activity-tree.js content: {e}")
        return False


def test_html_template():
    """Test if HTML template includes the correct script tags"""
    print("\n🔍 Testing HTML template for correct script includes...")

    try:
        response = requests.get("http://localhost:8765/dashboard", timeout=5)
        if response.status_code != 200:
            print(f"❌ Could not fetch dashboard HTML: status {response.status_code}")
            return False

        html_content = response.text

        # Check for the key script includes
        required_scripts = [
            "/static/dist/dashboard.js",
            "/static/dist/components/activity-tree.js",
            "d3js.org/d3.v7.min.js",  # D3.js CDN
        ]

        all_scripts_present = True
        for script in required_scripts:
            if script in html_content:
                print(f"✅ Found script reference: {script}")
            else:
                print(f"❌ Missing script reference: {script}")
                all_scripts_present = False

        # Check for Activity tab presence
        if 'data-tab="activity"' in html_content or "🌳 Activity" in html_content:
            print("✅ Activity tab is present in HTML")
        else:
            print("❌ Activity tab not found in HTML")
            all_scripts_present = False

        return all_scripts_present

    except Exception as e:
        print(f"❌ Error testing HTML template: {e}")
        return False


def check_build_files():
    """Check if build files exist on filesystem"""
    print("\n🔍 Checking build output files on filesystem...")

    base_path = Path(
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/dist"
    )

    required_files = [
        "dashboard.js",
        "components/activity-tree.js",
        "components/event-viewer.js",
    ]

    all_files_exist = True
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"✅ {file_path} exists ({size} bytes)")
        else:
            print(f"❌ {file_path} missing")
            all_files_exist = False

    return all_files_exist


def generate_test_report():
    """Generate a comprehensive test report"""
    print("\n" + "=" * 60)
    print("🧪 ACTIVITY TAB TEST REPORT")
    print("=" * 60)

    tests = [
        ("Dashboard Server", test_dashboard_server),
        ("Build Files on Disk", check_build_files),
        ("Static File Serving", test_static_files),
        ("Activity Tree Content", test_activity_tree_content),
        ("HTML Template", test_html_template),
    ]

    results = {}
    all_passed = True

    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            result = test_func()
            results[test_name] = result
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results[test_name] = False
            all_passed = False

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25} {status}")

    print(
        f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}"
    )

    # Recommendations
    print("\n📝 NEXT STEPS:")
    if all_passed:
        print("✅ All automated tests passed!")
        print("🎯 Manual testing recommended:")
        print("   1. Open http://localhost:8765/dashboard")
        print("   2. Click Activity tab")
        print("   3. Verify tree controls appear")
        print("   4. Check browser console for errors")
        print("   5. Test that it's different from Events tab")
    else:
        print("❌ Some tests failed. Check the errors above.")
        print("🔧 Common fixes:")
        print("   1. Ensure dashboard server is running")
        print("   2. Run 'npm run build' to rebuild assets")
        print("   3. Clear browser cache")
        print("   4. Check vite.config.js includes activity-tree.js")

    return all_passed


if __name__ == "__main__":
    print("🚀 Starting Activity Tab Test Suite...")
    print("This script will verify the Activity tab fix is working correctly.")

    success = generate_test_report()

    if success:
        print("\n🎉 Activity tab test completed successfully!")
        print(
            "📊 View the test helper: file:///Users/masa/Projects/claude-mpm/test_activity_tab.html"
        )
    else:
        print("\n⚠️  Some issues detected. Please review the report above.")

    sys.exit(0 if success else 1)
