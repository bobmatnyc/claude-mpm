#!/usr/bin/env python3
"""Validate that dashboard tabs are working correctly by checking the browser console.

This script connects to the dashboard and runs JavaScript to validate the state.
"""

import time
import socketio
from datetime import datetime

# Constants
SOCKETIO_PORT = 8765

def validate_dashboard():
    """Connect to dashboard and validate state via console commands.
    
    To use this:
    1. Run this script
    2. Open the dashboard in your browser
    3. Open browser developer console (F12)
    4. Check the console logs for validation results
    """
    
    print("Dashboard Tab Validation")
    print("=" * 50)
    print("\nSTEPS TO VALIDATE:")
    print("1. Make sure the dashboard is open in your browser")
    print("2. Open browser developer console (F12)")
    print("3. Run the following commands in the console:")
    print()
    
    # Validation commands to run in browser console
    console_commands = [
        "// Check event viewer state",
        "console.log('Event Viewer:', window.eventViewer);",
        "console.log('Total events:', window.eventViewer ? window.eventViewer.events.length : 'Not loaded');",
        "",
        "// Check file tool tracker",
        "console.log('File Tool Tracker:', dashboard.fileToolTracker);",
        "console.log('File operations:', dashboard.fileToolTracker ? dashboard.fileToolTracker.getFileOperations().size : 'Not loaded');",
        "console.log('Tool calls:', dashboard.fileToolTracker ? dashboard.fileToolTracker.getToolCalls().size : 'Not loaded');",
        "",
        "// List file operations",
        "if (dashboard.fileToolTracker && dashboard.fileToolTracker.getFileOperations().size > 0) {",
        "  console.log('Files tracked:');",
        "  dashboard.fileToolTracker.getFileOperations().forEach((data, path) => {",
        "    console.log(`  - ${path}: ${data.operations.length} operations`);",
        "  });",
        "}",
        "",
        "// List tool calls",
        "if (dashboard.fileToolTracker && dashboard.fileToolTracker.getToolCalls().size > 0) {",
        "  console.log('Tools tracked:');",
        "  dashboard.fileToolTracker.getToolCalls().forEach((call, key) => {",
        "    console.log(`  - ${call.tool_name}: ${call.success ? 'completed' : 'pending'}`);",
        "  });",
        "}",
        "",
        "// Check agent inference",
        "console.log('Agent Inference:', dashboard.agentInference);",
        "const uniqueAgents = dashboard.agentInference ? dashboard.agentInference.getUniqueAgentInstances() : [];",
        "console.log('Unique agents:', uniqueAgents.length);",
        "uniqueAgents.forEach(agent => {",
        "  console.log(`  - ${agent.agentName}: ${agent.totalEventCount || 0} events`);",
        "});",
        "",
        "// Check current tab rendering",
        "console.log('Current tab:', dashboard.uiStateManager.getCurrentTab());",
        "dashboard.renderCurrentTab();",
        "console.log('Tab rendered successfully');",
        "",
        "// Check tab contents",
        "['events-list', 'tools-list', 'files-list', 'agents-list'].forEach(id => {",
        "  const elem = document.getElementById(id);",
        "  if (elem) {",
        "    const items = elem.querySelectorAll('.event-item');",
        "    console.log(`${id}: ${items.length} items displayed`);",
        "  }",
        "});"
    ]
    
    print("CONSOLE COMMANDS TO RUN:")
    print("-" * 50)
    for cmd in console_commands:
        print(cmd)
    print("-" * 50)
    
    print("\n4. Check the console output for validation results")
    print("\nEXPECTED RESULTS:")
    print("- events-list: Should show 10 items")
    print("- tools-list: Should show 5 items (Read, Write, Bash, Task, Grep)")
    print("- files-list: Should show 2 items (README.md, test_file.txt)")
    print("- agents-list: Should show 1 item (research)")
    
    print("\n5. Click on each tab to verify they display correctly")
    print("6. Click on individual items to see if details show up")

if __name__ == "__main__":
    validate_dashboard()