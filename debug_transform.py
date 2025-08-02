#!/usr/bin/env python3
"""
Debug the event transformation logic to understand why filtering isn't working.
"""

# Simulate the transformEvent function from socket-client.js
def transform_event(event_data):
    """Python version of the JavaScript transformEvent function"""
    if not event_data or not event_data.get('type'):
        return event_data
    
    event_type = event_data['type']
    transformed_event = event_data.copy()
    
    # Transform 'hook.subtype' format to separate type and subtype
    if event_type.startswith('hook.'):
        subtype = event_type[5:]  # Remove 'hook.' prefix
        transformed_event['type'] = 'hook'
        transformed_event['subtype'] = subtype
    # Transform other dotted types like 'session.started' -> type: 'session', subtype: 'started'
    elif '.' in event_type:
        parts = event_type.split('.')
        main_type = parts[0]
        subtype = '.'.join(parts[1:])
        transformed_event['type'] = main_type
        transformed_event['subtype'] = subtype
    
    return transformed_event

# Simulate events that would come from hook_handler.py
test_events = [
    # File operation event (Read tool)
    {
        'type': 'hook.pre_tool',
        'timestamp': '2025-08-02T17:39:00.364121Z',
        'data': {
            'tool_name': 'Read',
            'agent_type': 'main',
            'session_id': 'test-session-123',
            'parameters': {
                'file_path': '/Users/masa/Projects/claude-mpm/README.md'
            }
        }
    },
    # Task delegation event 
    {
        'type': 'hook.pre_tool',
        'timestamp': '2025-08-02T17:39:05.364121Z',
        'data': {
            'tool_name': 'Task',
            'agent_type': 'main',
            'session_id': 'test-session-123',
            'parameters': {
                'subagent_type': 'engineer',
                'prompt': 'Fix this bug in the dashboard',
                'description': 'Debug the filtering logic'
            }
        }
    },
    # Write tool event
    {
        'type': 'hook.post_tool',
        'timestamp': '2025-08-02T17:39:10.364121Z',
        'data': {
            'tool_name': 'Write',
            'agent_type': 'engineer',
            'session_id': 'test-session-123',
            'parameters': {
                'file_path': '/Users/masa/Projects/claude-mpm/debug_output.txt',
                'content': 'Debug information'
            }
        }
    }
]

def test_agent_filtering(event):
    """Test the agent filtering logic from dashboard.js"""
    event_type = event.get('type', '')
    subtype = event.get('subtype', '')
    data = event.get('data', {})
    
    # Agent filtering conditions
    is_direct_agent_event = event_type == 'agent' or 'agent' in event_type
    is_task_delegation = (data.get('tool_name') == 'Task' and 
                         (subtype == 'pre_tool' or event_type == 'hook'))
    is_delegation_event = bool(data.get('subagent_type'))
    has_agent_type = bool(data.get('agent_type') and data.get('agent_type') != 'unknown')
    is_session_event = event_type == 'session'
    
    is_agent_event = (is_direct_agent_event or is_task_delegation or 
                     is_delegation_event or has_agent_type or is_session_event)
    
    return {
        'is_agent_event': is_agent_event,
        'reasons': {
            'is_direct_agent_event': is_direct_agent_event,
            'is_task_delegation': is_task_delegation,
            'is_delegation_event': is_delegation_event,
            'has_agent_type': has_agent_type,
            'is_session_event': is_session_event
        }
    }

def test_tool_filtering(event):
    """Test the tool filtering logic from dashboard.js"""
    event_type = event.get('type', '')
    subtype = event.get('subtype', '')
    data = event.get('data', {})
    
    # Tool filtering conditions
    is_hook_tool_event = (event_type == 'hook' and 
                         ('tool' in subtype or 'pre_' in subtype or 'post_' in subtype))
    has_tool_name = bool(data.get('tool_name'))
    has_tools_array = bool(data.get('tools') and isinstance(data.get('tools'), list))
    is_legacy_hook_event = (event_type.startswith('hook.') and 
                           ('tool' in event_type or 'pre' in event_type or 'post' in event_type))
    
    is_tool_event = (is_hook_tool_event or has_tool_name or 
                    has_tools_array or is_legacy_hook_event)
    
    return {
        'is_tool_event': is_tool_event,
        'reasons': {
            'is_hook_tool_event': is_hook_tool_event,
            'has_tool_name': has_tool_name,
            'has_tools_array': has_tools_array,
            'is_legacy_hook_event': is_legacy_hook_event
        }
    }

def test_file_filtering(event):
    """Test the file filtering logic from dashboard.js"""
    data = event.get('data', {})
    tool_name = data.get('tool_name')
    file_tools = ['Read', 'Write', 'Edit', 'MultiEdit', 'Glob', 'LS', 'NotebookRead', 'NotebookEdit']
    
    # Direct tool name match
    direct_match = tool_name in file_tools
    
    # Hook-based detection
    event_type = event.get('type', '')
    is_hook_event = (event_type == 'hook' or event_type.startswith('hook.')) and data
    hook_tool_match = False
    file_params_match = False
    
    if is_hook_event:
        hook_tool_match = data.get('tool_name') in file_tools
        
        params = data.get('parameters', {})
        has_file_params = bool(params.get('file_path') or params.get('path') or 
                              params.get('notebook_path') or params.get('pattern'))
        has_direct_file_params = bool(data.get('file_path') or data.get('path') or 
                                     data.get('notebook_path') or data.get('pattern'))
        file_params_match = has_file_params or has_direct_file_params
    
    is_file_event = direct_match or hook_tool_match or file_params_match
    
    return {
        'is_file_event': is_file_event,
        'reasons': {
            'direct_match': direct_match,
            'hook_tool_match': hook_tool_match,
            'file_params_match': file_params_match,
            'tool_name': tool_name
        }
    }

def main():
    print("🧪 DASHBOARD EVENT FILTERING DEBUG")
    print("=" * 50)
    
    for i, raw_event in enumerate(test_events):
        print(f"\n📋 Event {i+1}: {raw_event['data']['tool_name']} tool")
        print("Raw event:", raw_event)
        
        # Transform the event
        transformed = transform_event(raw_event)
        print("Transformed:", transformed)
        
        # Test filtering
        agent_result = test_agent_filtering(transformed)
        tool_result = test_tool_filtering(transformed)
        file_result = test_file_filtering(transformed)
        
        print(f"🤖 Agent filtering: {'✅ PASS' if agent_result['is_agent_event'] else '❌ FAIL'}")
        for reason, value in agent_result['reasons'].items():
            if value:
                print(f"   ✓ {reason}")
        
        print(f"🔧 Tool filtering: {'✅ PASS' if tool_result['is_tool_event'] else '❌ FAIL'}")
        for reason, value in tool_result['reasons'].items():
            if value:
                print(f"   ✓ {reason}")
        
        print(f"📁 File filtering: {'✅ PASS' if file_result['is_file_event'] else '❌ FAIL'}")
        for reason, value in file_result['reasons'].items():
            if value and reason != 'tool_name':
                print(f"   ✓ {reason}")
        if file_result['reasons']['tool_name']:
            print(f"   ✓ tool_name: {file_result['reasons']['tool_name']}")
    
    print("\n" + "=" * 50)
    print("🔍 ANALYSIS:")
    print("If any filtering shows ❌ FAIL, that indicates why tabs are empty")
    print("The dashboard filtering logic needs to match these exact conditions")

if __name__ == "__main__":
    main()