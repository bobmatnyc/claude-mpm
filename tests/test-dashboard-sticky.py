#!/usr/bin/env python3
"""
Test script to verify that the dashboard sticky state for "Full Event Data"
is working independently from "Structured Data".
"""

import os
import time
import webbrowser
from pathlib import Path


def main():
    """Main test function"""

    print("Dashboard Sticky State Test")
    print("=" * 50)
    print()

    # Check if test HTML exists
    test_file = Path(__file__).parent / "test-sticky-state.html"
    if not test_file.exists():
        print("❌ Test HTML file not found!")
        return

    print("✅ Test HTML file found")
    print()

    # Open test page in browser
    print("Opening test page in browser...")
    test_url = f"file://{test_file.absolute()}"
    webbrowser.open(test_url)
    print(f"Test page URL: {test_url}")
    print()

    # Instructions for manual testing
    print("Manual Test Instructions:")
    print("-" * 30)
    print("1. In the test page:")
    print("   - Toggle 'Structured Data' button")
    print("   - Toggle 'Full Event Data' button")
    print("   - Verify states are independent")
    print()
    print("2. Open the dashboard at http://localhost:8080")
    print("   - Click on any event in the Activity tab")
    print("   - Find the 'Structured Data' section (should respect its toggle state)")
    print("   - Find the 'Full Event Data' section (should respect its toggle state)")
    print("   - Toggle each section and verify they work independently")
    print()
    print("3. Refresh the dashboard page")
    print("   - Verify both sections maintain their expanded/collapsed state")
    print()
    print("4. Switch between different events")
    print("   - Verify the sticky state persists across event selections")
    print()

    # Check localStorage programmatically (if possible via browser automation)
    print("Expected Behavior:")
    print("-" * 30)
    print("✅ 'Structured Data' uses key: 'dashboard-json-expanded'")
    print("✅ 'Full Event Data' uses key: 'dashboard-full-event-expanded'")
    print("✅ Each section toggles independently")
    print("✅ States persist after page refresh")
    print("✅ States persist across event selections")
    print()

    print("Dashboard URL: http://localhost:8080")
    print()
    print("Test completed! Please verify manually in the browser.")


if __name__ == "__main__":
    main()
