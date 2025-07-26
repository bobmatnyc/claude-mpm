#!/usr/bin/env python3
"""Test the hook handler directly to see its logging behavior."""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up test environment
os.environ['CLAUDE_MPM_LOG_LEVEL'] = 'DEBUG'
os.environ['HOOK_EVENT_TYPE'] = 'UserPromptSubmit'

# Create test event data
test_event = {
    "type": "UserPromptSubmit", 
    "timestamp": 1234567890,
    "data": {
        "prompt": "/mpm status",
        "session_id": "test-session-123",
        "working_dir": os.getcwd()
    }
}

os.environ['HOOK_DATA'] = json.dumps(test_event['data'])

# Import and run the hook handler
hook_handler_path = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"

print("=== Testing Hook Handler Directly ===")
print(f"Hook handler path: {hook_handler_path}")
print(f"Event type: {os.environ['HOOK_EVENT_TYPE']}")
print(f"Event data: {os.environ['HOOK_DATA']}")
print()

# Run the hook handler by importing it
if hook_handler_path.exists():
    # Change to the hook handler directory
    original_dir = os.getcwd()
    os.chdir(hook_handler_path.parent)
    
    # Execute the hook handler
    with open(hook_handler_path) as f:
        code = compile(f.read(), str(hook_handler_path), 'exec')
        exec(code)
    
    os.chdir(original_dir)
else:
    print("Hook handler not found!")

# Check for any log files created
print("\n=== Checking for log files ===")
log_locations = [
    Path.home() / ".claude-mpm" / "logs",
    Path("/tmp"),
    Path(tempfile.gettempdir())
]

for location in log_locations:
    if location.exists():
        log_files = list(location.glob("*claude*log*"))
        if log_files:
            print(f"\nFound log files in {location}:")
            for log_file in sorted(log_files)[-5:]:
                print(f"  - {log_file.name}")