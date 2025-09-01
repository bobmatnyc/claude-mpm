#!/usr/bin/env python3
"""
Test script to verify the simple directory browser works completely.
This simulates the full browser behavior and API calls.
"""

import json
import sys
import time

import requests


def test_simple_browser():
    """Test the simple directory browser functionality."""

    base_url = "http://localhost:8765"

    print("🧪 Testing Simple Directory Browser")
    print("=" * 50)

    # Test 1: Check if main page loads
    print("\n📄 Test 1: Loading main page...")
    try:
        response = requests.get(f"{base_url}/code-simple", timeout=10)
        if response.status_code == 200:
            print("✅ Main page loads successfully")

            # Check if it contains the expected elements
            html = response.text
            if "code-container" in html and "code-simple.js" in html:
                print("✅ Main page contains required elements")
            else:
                print("❌ Main page missing required elements")
                return False
        else:
            print(f"❌ Main page failed to load: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Main page load error: {e}")
        return False

    # Test 2: Check if JavaScript loads
    print("\n🔗 Test 2: Loading JavaScript...")
    try:
        response = requests.get(
            f"{base_url}/static/js/components/code-simple.js", timeout=10
        )
        if response.status_code == 200:
            print("✅ JavaScript file loads successfully")

            # Check if it contains the expected code
            js_content = response.text
            expected_parts = [
                "SimpleCodeView",
                "loadDirectory",
                "window.simpleCodeView",
                "code-simple.js",
            ]

            all_found = True
            for part in expected_parts:
                if part in js_content:
                    print(f"✅ Found expected code: {part}")
                else:
                    print(f"❌ Missing expected code: {part}")
                    all_found = False

            if not all_found:
                return False

        else:
            print(f"❌ JavaScript failed to load: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ JavaScript load error: {e}")
        return False

    # Test 3: Check API endpoint
    print("\n🌐 Test 3: Testing API endpoint...")
    try:
        test_path = "/Users/masa/Projects/claude-mpm"
        response = requests.get(
            f"{base_url}/api/directory/list", params={"path": test_path}, timeout=10
        )

        if response.status_code == 200:
            print("✅ API endpoint responds successfully")

            data = response.json()
            print("✅ API returns JSON data")

            # Check expected fields
            expected_fields = ["path", "exists", "is_directory", "contents"]
            for field in expected_fields:
                if field in data:
                    print(f"✅ API response has field: {field}")
                else:
                    print(f"❌ API response missing field: {field}")
                    return False

            # Check if contents is populated
            if data.get("exists") and data.get("is_directory") and data.get("contents"):
                item_count = len(data["contents"])
                print(f"✅ API returns {item_count} directory items")

                # Show first few items
                for item in data["contents"][:3]:
                    icon = "📁" if item["is_directory"] else "📄"
                    print(f"  {icon} {item['name']}")

            else:
                print(
                    f"❌ API response invalid: exists={data.get('exists')}, is_directory={data.get('is_directory')}, contents={len(data.get('contents', []))}"
                )
                return False

        else:
            print(f"❌ API failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ API error: {e}")
        return False

    # Test 4: Test different directory paths
    print("\n📁 Test 4: Testing different directory paths...")
    test_paths = [
        "/Users/masa/Projects/claude-mpm/src",
        "/Users/masa/Projects/claude-mpm/docs",
        "/nonexistent/path",
    ]

    for test_path in test_paths:
        try:
            response = requests.get(
                f"{base_url}/api/directory/list", params={"path": test_path}, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                if test_path == "/nonexistent/path":
                    if not data.get("exists"):
                        print(f"✅ Correctly handles non-existent path: {test_path}")
                    else:
                        print(
                            f"❌ Should report non-existent path as not existing: {test_path}"
                        )
                elif data.get("exists"):
                    item_count = len(data.get("contents", []))
                    print(f"✅ Path {test_path}: {item_count} items")
                else:
                    print(f"⚠️  Path {test_path}: not accessible or doesn't exist")
            else:
                print(f"❌ Path {test_path}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Path {test_path}: Error {e}")

    print("\n🎉 All tests completed!")
    print("\nTo manually test the browser:")
    print(f"1. Open: {base_url}/code-simple")
    print("2. Open browser developer tools (F12)")
    print("3. Check Console tab for debug output")
    print("4. Look for these success messages:")
    print("   - '[code-simple.js] Script loaded'")
    print("   - '[SimpleCodeView.init] Starting'")
    print("   - '[SimpleCodeView.render] UI rendered'")
    print("   - '[SimpleCodeView.loadDirectory] Loading path'")
    print("   - 'Status: Loaded X items' (in green)")

    return True


if __name__ == "__main__":
    success = test_simple_browser()
    sys.exit(0 if success else 1)
