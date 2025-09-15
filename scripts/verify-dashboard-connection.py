#!/usr/bin/env python3
"""
Verify Activity Dashboard connection and send test events.
"""

import socketio
import time
import json
from datetime import datetime

def main():
    """Send test events to verify dashboard connection."""
    sio = socketio.Client()

    @sio.event
    def connect():
        print("✅ Connected to Socket.IO server")
        print(f"   Socket ID: {sio.sid}")

    @sio.event
    def disconnect():
        print("🔌 Disconnected from server")

    try:
        # Connect to server
        print("🔄 Connecting to server...")
        sio.connect('http://localhost:8765', transports=['polling', 'websocket'])

        # Wait for connection
        time.sleep(1)

        # Send various test events
        test_events = [
            {
                'type': 'session.start',
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'session_id': 'test-session-001',
                    'user': 'test-user',
                    'project': 'Activity Dashboard Test'
                }
            },
            {
                'type': 'agent.start',
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'agent': 'TestAgent',
                    'task': 'Testing dashboard connection',
                    'session_id': 'test-session-001'
                }
            },
            {
                'type': 'tool.execute',
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'tool': 'Read',
                    'parameters': {'file': 'test.txt'},
                    'agent': 'TestAgent',
                    'session_id': 'test-session-001'
                }
            },
            {
                'type': 'todowrite',
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'todos': [
                        {'content': 'Test task 1', 'status': 'completed'},
                        {'content': 'Test task 2', 'status': 'in_progress'},
                        {'content': 'Test task 3', 'status': 'pending'}
                    ],
                    'agent': 'TestAgent',
                    'session_id': 'test-session-001'
                }
            },
            {
                'type': 'agent.complete',
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'agent': 'TestAgent',
                    'result': 'Dashboard connection verified',
                    'session_id': 'test-session-001'
                }
            },
            {
                'type': 'session.end',
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'session_id': 'test-session-001',
                    'duration': 5000,
                    'status': 'success'
                }
            }
        ]

        print("\n📊 Sending test events to verify dashboard...")
        for i, event in enumerate(test_events, 1):
            print(f"   {i}. Sending {event['type']}...")
            sio.emit('claude_event', event)
            time.sleep(0.5)

        print("\n✅ Test events sent successfully!")
        print("\n📌 To verify the connection:")
        print("   1. Open http://localhost:8765/static/activity.html")
        print("   2. Check that status shows 'Connected' (green dot)")
        print("   3. Look for test events in the Activity Tree")
        print("   4. The tree should show:")
        print("      - Test session with TestAgent")
        print("      - Tool executions")
        print("      - Todo items")

        # Keep connection alive for a bit
        time.sleep(2)

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        sio.disconnect()
        print("\n🔌 Test complete, disconnected from server")

if __name__ == '__main__':
    main()