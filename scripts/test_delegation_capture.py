#!/usr/bin/env python3
"""Test that we're capturing delegation prompts correctly"""

import socketio
import time
import subprocess
import sys

print("=== Testing Delegation Prompt Capture ===")
print("\nThis will send a test prompt that delegates to agents.")
print("Watch the dashboard to see the captured prompts.\n")

# Start monitoring
sio = socketio.Client()
captured_delegations = []

@sio.event
def connect():
    print("✓ Connected to Socket.IO server for monitoring")

@sio.event
def claude_event(data):
    if data.get('type') == 'hook.pre_tool':
        event_data = data.get('data', {})
        if event_data.get('tool_name') == 'Task':
            delegation = event_data.get('delegation_details', {})
            if delegation:
                captured_delegations.append({
                    'agent': delegation.get('agent_type'),
                    'prompt': delegation.get('prompt'),
                    'preview': delegation.get('task_preview')
                })
                print(f"\n📥 Captured delegation to {delegation.get('agent_type')}:")
                print(f"   Preview: {delegation.get('task_preview')}")

# Connect to monitor
try:
    sio.connect('http://localhost:8765')
except Exception as e:
    print(f"⚠️  Could not connect to Socket.IO server: {e}")
    print("Make sure the server is running with --monitor flag")
    sys.exit(1)

# Send a test prompt
print("\n📤 Sending test prompt with delegations...")
test_prompt = """Please do the following tasks in parallel:
1. Ask the research agent to find the top 3 Python web frameworks
2. Ask the engineer agent to write a hello world Flask app
3. Ask the PM agent to create a project plan for a new feature"""

proc = subprocess.Popen(
    ['claude-mpm', 'run', '--non-interactive'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Send prompt and wait
stdout, stderr = proc.communicate(input=test_prompt)

# Give time for events to propagate
time.sleep(2)

# Disconnect and summarize
sio.disconnect()

print("\n" + "="*60)
print("SUMMARY")
print("="*60)

if captured_delegations:
    print(f"\n✅ Captured {len(captured_delegations)} delegation(s):")
    for i, delegation in enumerate(captured_delegations, 1):
        print(f"\n{i}. Agent: {delegation['agent']}")
        print(f"   Prompt preview: {delegation['preview']}")
        if delegation['prompt']:
            print(f"   Full prompt length: {len(delegation['prompt'])} chars")
else:
    print("\n❌ No delegations captured. Check if:")
    print("   - The Socket.IO server is running")
    print("   - The hook handler changes are deployed")
    print("   - Claude actually delegated to agents")

print("\n💡 Check the dashboard for full details!")