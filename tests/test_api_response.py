#!/usr/bin/env python3
"""
Test script to verify the directory API response format.
"""

import json
import sys

import requests


def test_api_response():
    """Test the directory API and verify response format."""

    # Test the API endpoint
    url = "http://localhost:8765/api/directory"
    params = {"path": "/Users/masa/Projects/claude-mpm"}

    try:
        print(f"🚀 Testing API: {url}")
        print(f"📁 Path: {params['path']}")

        response = requests.get(url, params=params)

        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return False

        data = response.json()

        print("✅ API responded successfully")
        print(f"📊 Response keys: {list(data.keys())}")

        # Check required fields
        required_fields = ["path", "exists", "is_directory", "contents"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False

        print("✅ All required fields present")

        # Check contents structure
        if not isinstance(data["contents"], list):
            print(f"❌ 'contents' is not a list: {type(data['contents'])}")
            return False

        print(f"📁 Found {len(data['contents'])} items")

        # Check first few items structure
        for i, item in enumerate(data["contents"][:3]):
            print(
                f"  Item {i + 1}: {item.get('name', 'NO_NAME')} ({'dir' if item.get('is_directory') else 'file'})"
            )

            required_item_fields = ["name", "path", "is_directory", "is_file"]
            missing_item_fields = [
                field for field in required_item_fields if field not in item
            ]

            if missing_item_fields:
                print(f"    ⚠️  Missing item fields: {missing_item_fields}")
            else:
                print("    ✅ Item structure OK")

        # Summary
        dirs = [item for item in data["contents"] if item.get("is_directory")]
        files = [item for item in data["contents"] if not item.get("is_directory")]

        print("\n📊 Summary:")
        print(f"  Total items: {len(data['contents'])}")
        print(f"  Directories: {len(dirs)}")
        print(f"  Files: {len(files)}")

        if "summary" in data:
            print(f"  API Summary: {data['summary']}")

        return True

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {url}")
        print("   Make sure the monitor is running: ./scripts/claude-mpm monitor start")
        return False
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False


def test_client_expectations():
    """Test what the client code expects vs what API provides."""

    print("\n🔍 Testing client expectations...")

    # What the client expects (from code-tree.js)
    client_expects = {
        "root_field": "contents",  # Fixed: was 'items'
        "item_fields": ["name", "path", "is_directory", "is_file"],
    }

    # What the API provides
    url = "http://localhost:8765/api/directory"
    params = {"path": "/Users/masa/Projects/claude-mpm"}

    try:
        response = requests.get(url, params=params)
        data = response.json()

        # Check root field
        if client_expects["root_field"] in data:
            print(f"✅ Root field '{client_expects['root_field']}' found")
        else:
            print(f"❌ Root field '{client_expects['root_field']}' missing")
            print(f"   Available fields: {list(data.keys())}")

        # Check item fields
        if data.get("contents"):
            first_item = data["contents"][0]
            for field in client_expects["item_fields"]:
                if field in first_item:
                    print(f"✅ Item field '{field}' found")
                else:
                    print(f"❌ Item field '{field}' missing")
                    print(f"   Available item fields: {list(first_item.keys())}")

        return True

    except Exception as e:
        print(f"❌ Error checking client expectations: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Directory API Response Test")
    print("=" * 50)

    success1 = test_api_response()
    success2 = test_client_expectations()

    if success1 and success2:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
