#!/usr/bin/env python3
"""Verify that dashboard views are displaying data correctly."""

import sys
import time

import requests
from bs4 import BeautifulSoup


def check_page_content(url, page_name):
    """Check if a dashboard page has content."""
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"❌ {page_name}: Failed to load (HTTP {response.status_code})")
            return False

        soup = BeautifulSoup(response.text, "html.parser")

        # Check for the "no data" messages
        no_data_indicators = [
            "No Agent Activity Yet",
            "No Tool Usage Yet",
            "No File Operations Yet",
            "No Agents Found",
            "No Tools Found",
            "No Files Found",
        ]

        page_text = soup.get_text()
        has_no_data_message = any(
            indicator in page_text for indicator in no_data_indicators
        )

        # Check for data indicators
        has_data = False

        if "agents" in url.lower():
            # Check for agent-specific elements
            if (
                "Research Agent" in page_text
                or "Engineer Agent" in page_text
                or "Project Manager" in page_text
            ):
                has_data = True
            # Check for agent status badges
            if soup.find_all(class_="status-badge"):
                has_data = True

        elif "tools" in url.lower():
            # Check for tool names
            tool_names = [
                "Read",
                "Write",
                "Edit",
                "Bash",
                "Grep",
                "WebSearch",
                "TodoWrite",
            ]
            if any(tool in page_text for tool in tool_names):
                has_data = True
            # Check for tool badges
            if soup.find_all(class_="tool-badge"):
                has_data = True

        elif "files" in url.lower():
            # Check for file paths
            file_indicators = [
                "dashboard.js",
                "main.css",
                "README.md",
                "test_dashboard.py",
            ]
            if any(file in page_text for file in file_indicators):
                has_data = True

        # Check stats aren't all zero
        stat_values = soup.find_all(class_="stat-value")
        non_zero_stats = False
        for stat in stat_values:
            text = stat.get_text().strip()
            # Check if any stat is not 0, 0%, 0s, or 0ms
            if text and text not in ["0", "0%", "0s", "0ms"]:
                non_zero_stats = True
                break

        if has_data and non_zero_stats and not has_no_data_message:
            print(f"✅ {page_name}: Data is displaying correctly")
            print(f"   - Found data elements: {has_data}")
            print(f"   - Has non-zero stats: {non_zero_stats}")
            print(f"   - No 'empty' messages: {not has_no_data_message}")
            return True
        print(f"⚠️ {page_name}: May not be showing data")
        print(f"   - Found data elements: {has_data}")
        print(f"   - Has non-zero stats: {non_zero_stats}")
        print(f"   - No 'empty' messages: {not has_no_data_message}")

        # Show what's in the stats
        if stat_values:
            print(
                f"   - Stats found: {[s.get_text().strip() for s in stat_values[:5]]}"
            )

        return False

    except Exception as e:
        print(f"❌ {page_name}: Error checking page - {e}")
        return False


def main():
    """Main verification function."""
    base_url = "http://localhost:8765"

    print("Verifying dashboard displays...")
    print("=" * 50)

    # Give a moment for any pending updates
    time.sleep(2)

    results = []

    # Check each dashboard page
    pages = [
        (f"{base_url}/static/agents.html", "Agents Dashboard"),
        (f"{base_url}/static/tools.html", "Tools Dashboard"),
        (f"{base_url}/static/files.html", "Files Dashboard"),
    ]

    for url, name in pages:
        result = check_page_content(url, name)
        results.append((name, result))
        print()

    print("=" * 50)
    print("Summary:")
    all_passed = all(r[1] for r in results)

    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")

    if all_passed:
        print("\n🎉 All dashboards are displaying data correctly!")
    else:
        print("\n⚠️ Some dashboards may not be displaying data.")
        print("Open the following URLs in your browser to verify:")
        for url, name in pages:
            print(f"  - {url}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
