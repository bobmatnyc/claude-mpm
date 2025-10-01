#!/usr/bin/env python3
"""Test script to verify search viewer functionality in the dashboard."""

import json
from datetime import datetime, timezone


def create_test_search_event():
    """Create a test search event for the dashboard."""

    # Sample search operation event data
    search_event = {
        "event_type": "pre_tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": "test-session-123",
        "agent_type": "Research",
        "tool_name": "Grep",
        "tool_parameters": {
            "pattern": r"function\s+\w+",
            "path": "/Users/masa/Projects/claude-mpm/src",
            "glob": "*.js",
            "type": "javascript",
            "-n": True,
            "-i": False,
        },
    }

    # Sample search result
    search_result = {
        "event_type": "post_tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": "test-session-123",
        "agent_type": "Research",
        "tool_name": "Grep",
        "success": True,
        "duration_ms": 234,
        "result_summary": {
            "output_preview": """Found 15 matches:
src/file1.js:10: function handleClick() {
src/file1.js:25: function processData(data) {
src/file2.js:5:  function init() {
src/file2.js:42: function cleanup() {
src/utils.js:8:  function formatDate(date) {
...(10 more matches)""",
            "output_lines": 15,
            "has_output": True,
            "has_error": False,
        },
    }

    return search_event, search_result


def test_search_viewer_display():
    """Test that the search viewer modal displays correctly."""

    print("Testing Search Viewer Functionality")
    print("=" * 50)

    # Create test events
    pre_event, post_event = create_test_search_event()

    print("\n1. Search Parameters (Pre-event):")
    print(json.dumps(pre_event["tool_parameters"], indent=2))

    print("\n2. Search Results (Post-event):")
    print(json.dumps(post_event["result_summary"], indent=2))

    print("\n3. Expected Modal Display:")
    print("   - Search pattern: ", pre_event["tool_parameters"]["pattern"])
    print("   - Search path: ", pre_event["tool_parameters"]["path"])
    print("   - File type: ", pre_event["tool_parameters"].get("type", "all"))
    print("   - Results preview: ")
    print("     ", post_event["result_summary"]["output_preview"][:100] + "...")

    print("\n4. Verify in Dashboard:")
    print("   a. Navigate to Tools tab")
    print("   b. Click on a Grep/Search operation")
    print("   c. Click 'View Search Details' button")
    print("   d. Verify modal shows:")
    print("      - Search parameters in JSON format")
    print("      - Search results displayed clearly")
    print("      - Modal can be closed with X or Escape key")

    print("\n✅ Test data created successfully")
    print("📝 Manual verification required in the dashboard")


if __name__ == "__main__":
    test_search_viewer_display()
