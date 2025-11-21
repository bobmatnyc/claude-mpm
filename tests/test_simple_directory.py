#!/usr/bin/env python3
"""Test the simple directory API directly"""

import json
import sys

import requests


def test_directory(path="."):
    url = "http://localhost:8765/api/directory/list"
    params = {"path": path}

    try:
        response = requests.get(url, params=params)
        data = response.json()

        print(f"\n📁 Directory: {data['path']}")
        print(f"   Exists: {data['exists']}")
        print(f"   Is Directory: {data['is_directory']}")

        if data.get("contents"):
            print(f"\n📋 Contents ({len(data['contents'])} items):")
            for item in data["contents"]:
                icon = "📁" if item["is_directory"] else "📄"
                print(f"   {icon} {item['name']}")
        else:
            print("\n   ⚠️  Empty or no contents")

        if data.get("error"):
            print(f"\n   ❌ Error: {data['error']}")

        return data
    except requests.exceptions.ConnectionError:
        print("❌ Failed to connect to http://localhost:8765")
        print("   Make sure the Socket.IO server is running with: ./claude-mpm run")
        return None
    except Exception as e:
        print(f"❌ Failed to test directory: {e}")
        return None


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/Users/masa/Projects/claude-mpm/src"
    print(f"Testing simple directory listing for: {path}")
    result = test_directory(path)

    # Also test the current working directory
    if path != ".":
        print("\n" + "=" * 50)
        print("Testing current working directory:")
        test_directory(".")

    # Test a few other interesting directories if we're not already testing them
    other_tests = [
        "/Users/masa/Projects/claude-mpm/src/claude_mpm",
        "/Users/masa/Projects/claude-mpm/scripts",
    ]

    for test_path in other_tests:
        if path != test_path:
            print("\n" + "=" * 50)
            print(f"Testing: {test_path}")
            test_directory(test_path)
