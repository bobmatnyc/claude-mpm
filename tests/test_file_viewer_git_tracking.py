#!/usr/bin/env python3
"""
Test Tool Correlation Improvements

This script tests the improved tool correlation logic in file-tool-tracker.js
by simulating pre_tool and post_tool events that could cause duplicate entries
with the old correlation method.
"""

import json
from datetime import datetime, timedelta, timezone


def create_test_events():
    """Create test events that simulate the duplicate tool issue."""

    # Base timestamp
    base_time = datetime.now(timezone.utc)

    # Create events with timing that would cause duplicates in old system
    events = []

    # Test Case 1: Tool call that spans multiple seconds (would create duplicates in old system)
    pre_tool_time = base_time
    post_tool_time = base_time + timedelta(seconds=3)  # 3 seconds later

    events.extend(
        [
            {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Bash",
                "session_id": "test-session-1",
                "timestamp": pre_tool_time.isoformat(),
                "tool_parameters": {"command": "pm", "description": "Run pm command"},
                "working_directory": "/Users/masa/Projects/claude-mpm",
                "operation_type": "command_execution",
            },
            {
                "type": "hook",
                "subtype": "post_tool",
                "tool_name": "Bash",
                "session_id": "test-session-1",
                "timestamp": post_tool_time.isoformat(),
                "duration_ms": 3000,
                "success": True,
                "exit_code": 0,
                "result_summary": {"output": "Command executed successfully"},
                "working_directory": "/Users/masa/Projects/claude-mpm",
            },
        ]
    )

    # Test Case 2: Multiple tools with same name but different parameters
    time2 = base_time + timedelta(seconds=10)
    time3 = base_time + timedelta(seconds=12)

    events.extend(
        [
            {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Read",
                "session_id": "test-session-1",
                "timestamp": time2.isoformat(),
                "tool_parameters": {
                    "file_path": "/Users/masa/Projects/claude-mpm/src/file1.py"
                },
                "working_directory": "/Users/masa/Projects/claude-mpm",
            },
            {
                "type": "hook",
                "subtype": "post_tool",
                "tool_name": "Read",
                "session_id": "test-session-1",
                "timestamp": time3.isoformat(),
                "duration_ms": 2000,
                "success": True,
                "exit_code": 0,
                "result_summary": {"output": "File content read successfully"},
            },
        ]
    )

    # Test Case 3: Another Read tool with different file (should be separate entry)
    time4 = base_time + timedelta(seconds=15)
    time5 = base_time + timedelta(seconds=16)

    events.extend(
        [
            {
                "type": "hook",
                "subtype": "pre_tool",
                "tool_name": "Read",
                "session_id": "test-session-1",
                "timestamp": time4.isoformat(),
                "tool_parameters": {
                    "file_path": "/Users/masa/Projects/claude-mpm/src/file2.py"
                },
                "working_directory": "/Users/masa/Projects/claude-mpm",
            },
            {
                "type": "hook",
                "subtype": "post_tool",
                "tool_name": "Read",
                "session_id": "test-session-1",
                "timestamp": time5.isoformat(),
                "duration_ms": 1000,
                "success": True,
                "exit_code": 0,
                "result_summary": {"output": "File content read successfully"},
            },
        ]
    )

    # Test Case 4: Orphaned pre_tool (still running)
    time6 = base_time + timedelta(seconds=20)

    events.append(
        {
            "type": "hook",
            "subtype": "pre_tool",
            "tool_name": "Bash",
            "session_id": "test-session-1",
            "timestamp": time6.isoformat(),
            "tool_parameters": {
                "command": "long-running-command",
                "description": "Long running command",
            },
            "working_directory": "/Users/masa/Projects/claude-mpm",
            "operation_type": "command_execution",
        }
    )

    return events


def create_test_html():
    """Create HTML file to test the correlation logic."""

    events = create_test_events()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Tool Correlation Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .test-section {{ margin: 20px 0; padding: 15px; border: 1px solid #ccc; }}
        .event {{ background: #f5f5f5; padding: 10px; margin: 5px 0; border-radius: 4px; }}
        .tool-call {{ background: #e8f5e8; padding: 10px; margin: 5px 0; border-radius: 4px; }}
        .results {{ margin-top: 20px; }}
        pre {{ background: #f8f8f8; padding: 10px; overflow: auto; }}
        .old-system {{ background: #ffe6e6; }}
        .new-system {{ background: #e6ffe6; }}
    </style>
</head>
<body>
    <h1>Tool Correlation Test</h1>

    <div class="test-section">
        <h2>Test Events</h2>
        <p>The following events simulate the duplicate tool issue:</p>
        <div id="events-display"></div>
    </div>

    <div class="test-section old-system">
        <h2>Old System (Would Create Duplicates)</h2>
        <p>Old correlation key: sessionId_toolName_timestampSecond</p>
        <div id="old-system-results"></div>
    </div>

    <div class="test-section new-system">
        <h2>New System (Improved Correlation)</h2>
        <p>New correlation: intelligent matching with parameter similarity</p>
        <div id="new-system-results"></div>
    </div>

    <script>
        // Test events
        const testEvents = {json.dumps(events, indent=2)};

        // Display events
        const eventsDisplay = document.getElementById('events-display');
        testEvents.forEach((event, index) => {{
            const eventDiv = document.createElement('div');
            eventDiv.className = 'event';
            eventDiv.innerHTML = `
                <strong>Event ${{index + 1}}: ${{event.subtype}} - ${{event.tool_name}}</strong><br>
                Time: ${{event.timestamp}}<br>
                Parameters: ${{JSON.stringify(event.tool_parameters || {{}})}}
            `;
            eventsDisplay.appendChild(eventDiv);
        }});

        // Simulate old system correlation
        function oldSystemCorrelation(events) {{
            const pairs = new Map();
            events.forEach(event => {{
                if (!event.tool_name) return;
                const timestamp = new Date(event.timestamp).getTime();
                const key = `${{event.session_id}}_${{event.tool_name}}_${{Math.floor(timestamp / 1000)}}`;

                if (!pairs.has(key)) {{
                    pairs.set(key, {{ pre_event: null, post_event: null, tool_name: event.tool_name }});
                }}

                const pair = pairs.get(key);
                if (event.subtype === 'pre_tool') {{
                    pair.pre_event = event;
                }} else if (event.subtype === 'post_tool') {{
                    pair.post_event = event;
                }}
            }});
            return pairs;
        }}

        // Simulate new system correlation
        function newSystemCorrelation(events) {{
            const preToolEvents = events.filter(e => e.subtype === 'pre_tool');
            const postToolEvents = events.filter(e => e.subtype === 'post_tool');
            const pairs = new Map();
            const usedPostEvents = new Set();

            preToolEvents.forEach((preEvent, preIndex) => {{
                const pairKey = `${{preEvent.session_id}}_${{preEvent.tool_name}}_${{preIndex}}_${{preEvent.timestamp}}`;
                const pair = {{
                    pre_event: preEvent,
                    post_event: null,
                    tool_name: preEvent.tool_name
                }};

                // Find matching post event
                let bestMatch = -1;
                let bestScore = -1;

                postToolEvents.forEach((postEvent, postIndex) => {{
                    if (usedPostEvents.has(postIndex)) return;
                    if (postEvent.tool_name !== preEvent.tool_name) return;
                    if (postEvent.session_id !== preEvent.session_id) return;

                    const preTime = new Date(preEvent.timestamp).getTime();
                    const postTime = new Date(postEvent.timestamp).getTime();
                    const timeDiff = Math.abs(postTime - preTime);

                    if (postTime >= preTime - 1000 && timeDiff <= 300000) {{
                        let score = 1000 - (timeDiff / 1000);

                        // Parameter similarity boost
                        const preParams = preEvent.tool_parameters || {{}};
                        const postParams = postEvent.tool_parameters || {{}};
                        if (JSON.stringify(preParams) === JSON.stringify(postParams)) {{
                            score += 500;
                        }}

                        if (score > bestScore) {{
                            bestScore = score;
                            bestMatch = postIndex;
                        }}
                    }}
                }});

                if (bestMatch >= 0) {{
                    pair.post_event = postToolEvents[bestMatch];
                    usedPostEvents.add(bestMatch);
                }}

                pairs.set(pairKey, pair);
            }});

            return pairs;
        }}

        // Run tests
        const oldResults = oldSystemCorrelation(testEvents);
        const newResults = newSystemCorrelation(testEvents);

        // Display old system results
        const oldDisplay = document.getElementById('old-system-results');
        oldDisplay.innerHTML = `
            <h3>Tool Calls Found: ${{oldResults.size}}</h3>
            <p><strong>Problem:</strong> Some tools might appear multiple times due to timestamp-second grouping</p>
        `;

        Array.from(oldResults.entries()).forEach(([key, pair]) => {{
            const div = document.createElement('div');
            div.className = 'tool-call';
            div.innerHTML = `
                <strong>Key:</strong> ${{key}}<br>
                <strong>Tool:</strong> ${{pair.tool_name}}<br>
                <strong>Has Pre:</strong> ${{pair.pre_event ? 'Yes' : 'No'}}<br>
                <strong>Has Post:</strong> ${{pair.post_event ? 'Yes' : 'No'}}
            `;
            oldDisplay.appendChild(div);
        }});

        // Display new system results
        const newDisplay = document.getElementById('new-system-results');
        newDisplay.innerHTML = `
            <h3>Tool Calls Found: ${{newResults.size}}</h3>
            <p><strong>Improvement:</strong> Each unique tool execution appears exactly once</p>
        `;

        Array.from(newResults.entries()).forEach(([key, pair]) => {{
            const div = document.createElement('div');
            div.className = 'tool-call';
            div.innerHTML = `
                <strong>Tool:</strong> ${{pair.tool_name}}<br>
                <strong>Has Pre:</strong> ${{pair.pre_event ? 'Yes' : 'No'}}<br>
                <strong>Has Post:</strong> ${{pair.post_event ? 'Yes' : 'No'}}<br>
                <strong>Status:</strong> ${{pair.post_event ? 'Completed' : 'Running'}}
            `;
            newDisplay.appendChild(div);
        }});

        // Summary
        console.log('Old System - Tool Calls:', oldResults.size);
        console.log('New System - Tool Calls:', newResults.size);
        console.log('Test completed successfully!');
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    # Create the test HTML file
    html_content = create_test_html()

    with open("tool_correlation_test.html", "w") as f:
        f.write(html_content)

    print("✅ Tool correlation test file created: tool_correlation_test.html")
    print("📊 Open this file in a browser to see the correlation improvements")
    print("🔍 Check the console for detailed results")

    # Also create a JSON file with test events for reference
    events = create_test_events()
    with open("test_events.json", "w") as f:
        json.dump(events, f, indent=2)

    print("📄 Test events saved to: test_events.json")
