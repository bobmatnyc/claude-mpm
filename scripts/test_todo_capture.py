#!/usr/bin/env python3
"""Test TodoWrite list capture"""

import socketio
import json
import time
from datetime import datetime

print("=== Testing TodoWrite Capture ===")

sio = socketio.Client()
captured_todos = []

@sio.event
def connect():
    print("Connected to Socket.IO server")

@sio.event
def claude_event(data):
    if data.get('type') == 'hook.pre_tool':
        event_data = data.get('data', {})
        if event_data.get('tool_name') == 'TodoWrite':
            params = event_data.get('tool_parameters', {})
            captured_todos.append({
                'timestamp': data.get('timestamp'),
                'todos': params.get('todos', []),
                'summary': params.get('todo_summary', {}),
                'count': params.get('todo_count', 0)
            })
            
            print(f"\n📋 Captured TodoWrite at {datetime.now().strftime('%H:%M:%S')}:")
            print(f"   Total tasks: {params.get('todo_count', 0)}")
            print(f"   Summary: {params.get('todo_summary', {}).get('summary', 'N/A')}")
            
            # Show todos
            todos = params.get('todos', [])
            if todos:
                print("   Tasks:")
                for todo in todos:
                    status_emoji = {
                        'completed': '✅',
                        'in_progress': '🔄',
                        'pending': '⏳'
                    }.get(todo.get('status', 'pending'), '❓')
                    
                    priority_emoji = {
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(todo.get('priority', 'medium'), '⚪')
                    
                    print(f"      {status_emoji} {priority_emoji} {todo.get('content', 'No content')}")

# Look at recent history
@sio.event
def history(data):
    events = data.get('events', [])
    todo_events = [e for e in events if e.get('type') == 'hook.pre_tool' 
                   and e.get('data', {}).get('tool_name') == 'TodoWrite']
    
    print(f"\nFound {len(todo_events)} TodoWrite events in history")
    
    for event in todo_events[-3:]:  # Last 3
        params = event.get('data', {}).get('tool_parameters', {})
        timestamp = event.get('timestamp', 'unknown')
        print(f"\n📅 TodoWrite at {timestamp}:")
        
        summary = params.get('todo_summary', {})
        if summary:
            print(f"   {summary.get('summary', 'No summary')}")
            
        todos = params.get('todos', [])
        if todos:
            print("   Full list:")
            for i, todo in enumerate(todos, 1):
                print(f"   {i}. [{todo.get('status', 'unknown')}] {todo.get('content', 'No content')} ({todo.get('priority', 'medium')})")

try:
    sio.connect('http://localhost:8765')
    # Request history
    sio.emit('get_history', {'limit': 100})
    
    print("\n💡 Trigger a TodoWrite to see live capture!")
    print("   Example: Use Claude to create a task list")
    
    # Keep monitoring for a bit
    time.sleep(30)
    
except KeyboardInterrupt:
    print("\nStopping monitor...")
except Exception as e:
    print(f"Error: {e}")
finally:
    if sio.connected:
        sio.disconnect()

print(f"\n📊 Summary: Captured {len(captured_todos)} TodoWrite events during monitoring")