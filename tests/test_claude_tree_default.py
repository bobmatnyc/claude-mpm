#!/usr/bin/env python3
"""
Test script to verify Claude Tree is the default active tab in the monitor dashboard.
"""

import sys
import time
from pathlib import Path

import requests


def test_claude_tree_default():
    """Test that Claude Tree is the default active tab."""

    # Check if monitor is running
    monitor_url = "http://localhost:8765"

    try:
        # Try to fetch the dashboard HTML
        response = requests.get(monitor_url, timeout=5)

        if response.status_code != 200:
            print(f"❌ Monitor not responding properly (status {response.status_code})")
            return False

        html_content = response.text

        # Check for Claude Tree tab being active in HTML
        if 'class="tab-button active" data-tab="claude-tree"' in html_content:
            print("✅ Claude Tree tab is marked as active in HTML")
        else:
            print("❌ Claude Tree tab is NOT marked as active in HTML")
            return False

        # Check for Claude Tree content being active
        if 'class="tab-content active" id="claude-tree-tab"' in html_content:
            print("✅ Claude Tree content is marked as active in HTML")
        else:
            print("❌ Claude Tree content is NOT marked as active in HTML")
            return False

        # Check that Events tab is NOT active
        if 'class="tab-button active" data-tab="events"' not in html_content:
            print("✅ Events tab is correctly NOT marked as active")
        else:
            print("❌ Events tab is incorrectly marked as active")
            return False

        print("\n✅ SUCCESS: Claude Tree is the default active tab!")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to monitor at {monitor_url}")
        print(f"   Error: {e}")
        print("\nTo test the changes:")
        print("1. Start the monitor: claude-mpm monitor")
        print("2. Run this test script again")
        return False


if __name__ == "__main__":
    success = test_claude_tree_default()
    sys.exit(0 if success else 1)
