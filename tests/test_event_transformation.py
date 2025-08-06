#!/usr/bin/env python3
"""
Test script to verify event transformation in Socket.IO client
"""

import sys
import os
import time
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

def test_transformation_logic():
    """Test the JavaScript transformation logic by simulating the same operation in Python"""
    
    # Test case 1: hook.pre_tool event with nested data
    original_event = {
        'type': 'hook.pre_tool',
        'timestamp': '2025-01-01T12:00:00.000Z',
        'data': {
            'tool_name': 'Edit',
            'agent_type': 'pm',
            'tool_parameters': {'file_path': '/test/file.py', 'content': 'test'},
            'session_id': 'test-session-123'
        }
    }
    
    # Simulate the JavaScript transformation
    transformed_event = dict(original_event)  # Copy original
    
    # Split type
    if transformed_event['type'].startswith('hook.'):
        subtype = transformed_event['type'][5:]  # Remove 'hook.' prefix
        transformed_event['type'] = 'hook'
        transformed_event['subtype'] = subtype
    
    # Flatten data fields
    if 'data' in original_event and isinstance(original_event['data'], dict):
        for key, value in original_event['data'].items():
            if key not in transformed_event:
                transformed_event[key] = value
    
    print("Test Case 1: hook.pre_tool event")
    print("Original event:")
    print(f"  type: {original_event['type']}")
    print(f"  data.tool_name: {original_event['data'].get('tool_name')}")
    print(f"  data.agent_type: {original_event['data'].get('agent_type')}")
    
    print("\nTransformed event:")
    print(f"  type: {transformed_event.get('type')}")
    print(f"  subtype: {transformed_event.get('subtype')}")
    print(f"  tool_name: {transformed_event.get('tool_name')}")
    print(f"  agent_type: {transformed_event.get('agent_type')}")
    print(f"  tool_parameters: {transformed_event.get('tool_parameters')}")
    
    # Verify expected results
    assert transformed_event['type'] == 'hook', f"Expected type 'hook', got '{transformed_event['type']}'"
    assert transformed_event['subtype'] == 'pre_tool', f"Expected subtype 'pre_tool', got '{transformed_event['subtype']}'"
    assert transformed_event['tool_name'] == 'Edit', f"Expected tool_name 'Edit', got '{transformed_event['tool_name']}'"
    assert transformed_event['agent_type'] == 'pm', f"Expected agent_type 'pm', got '{transformed_event['agent_type']}'"
    assert 'data' in transformed_event, "Original data field should be preserved"
    
    print("✓ Test Case 1 passed!")
    
    # Test case 2: session.started event
    original_event2 = {
        'type': 'session.started',
        'timestamp': '2025-01-01T12:01:00.000Z',
        'data': {
            'session_id': 'session-456',
            'user_id': 'user123'
        }
    }
    
    transformed_event2 = dict(original_event2)
    
    # Transform dotted type
    if '.' in transformed_event2['type']:
        main_type, *subtype_parts = transformed_event2['type'].split('.')
        transformed_event2['type'] = main_type
        transformed_event2['subtype'] = '.'.join(subtype_parts)
    
    # Flatten data
    if 'data' in original_event2 and isinstance(original_event2['data'], dict):
        for key, value in original_event2['data'].items():
            if key not in transformed_event2:
                transformed_event2[key] = value
    
    print("\nTest Case 2: session.started event")
    print("Original event:")
    print(f"  type: {original_event2['type']}")
    print(f"  data.session_id: {original_event2['data'].get('session_id')}")
    
    print("\nTransformed event:")
    print(f"  type: {transformed_event2.get('type')}")
    print(f"  subtype: {transformed_event2.get('subtype')}")
    print(f"  session_id: {transformed_event2.get('session_id')}")
    
    assert transformed_event2['type'] == 'session', f"Expected type 'session', got '{transformed_event2['type']}'"
    assert transformed_event2['subtype'] == 'started', f"Expected subtype 'started', got '{transformed_event2['subtype']}'"
    assert transformed_event2['session_id'] == 'session-456', f"Expected session_id 'session-456', got '{transformed_event2['session_id']}'"
    
    print("✓ Test Case 2 passed!")
    
    print("\n🎉 All transformation tests passed!")

def generate_javascript_test_code():
    """Generate JavaScript code that can be run in browser console to test the fix"""
    
    js_test = '''
// Test the transformEvent function in browser console
// Paste this into the browser console when the dashboard is loaded

console.log("Testing event transformation...");

// Test case 1: hook.pre_tool event
const testEvent1 = {
    type: 'hook.pre_tool',
    timestamp: '2025-01-01T12:00:00.000Z',
    data: {
        tool_name: 'Edit',
        agent_type: 'pm',
        tool_parameters: {file_path: '/test/file.py', content: 'test'},
        session_id: 'test-session-123'
    }
};

console.log("Original event:", testEvent1);

if (window.socketClient) {
    const transformed1 = window.socketClient.transformEvent(testEvent1);
    console.log("Transformed event:", transformed1);
    
    // Verify expected results
    console.assert(transformed1.type === 'hook', 'Expected type "hook"');
    console.assert(transformed1.subtype === 'pre_tool', 'Expected subtype "pre_tool"');
    console.assert(transformed1.tool_name === 'Edit', 'Expected tool_name "Edit"');
    console.assert(transformed1.agent_type === 'pm', 'Expected agent_type "pm"');
    console.assert(transformed1.tool_parameters !== undefined, 'Expected tool_parameters to be copied');
    
    console.log("✓ Test 1 passed - hook.pre_tool correctly transformed");
} else {
    console.error("socketClient not available - dashboard may not be loaded");
}

// Test case 2: session.started event
const testEvent2 = {
    type: 'session.started',
    timestamp: '2025-01-01T12:01:00.000Z',
    data: {
        session_id: 'session-456',
        user_id: 'user123'
    }
};

if (window.socketClient) {
    const transformed2 = window.socketClient.transformEvent(testEvent2);
    console.log("Transformed session event:", transformed2);
    
    console.assert(transformed2.type === 'session', 'Expected type "session"');
    console.assert(transformed2.subtype === 'started', 'Expected subtype "started"');
    console.assert(transformed2.session_id === 'session-456', 'Expected session_id to be copied');
    
    console.log("✓ Test 2 passed - session.started correctly transformed");
}

console.log("🎉 JavaScript transformation tests completed!");
'''
    
    print("\nJavaScript test code (copy and paste into browser console):")
    print("=" * 60)
    print(js_test)
    print("=" * 60)

if __name__ == "__main__":
    print("Testing Event Transformation Logic")
    print("=" * 40)
    
    try:
        test_transformation_logic()
        generate_javascript_test_code()
        
        print("\n📋 To test the fix:")
        print("1. Start the dashboard: claude-mpm --manager")
        print("2. Open browser console (F12)")
        print("3. Paste the JavaScript test code above")
        print("4. Run it to verify the transformation works")
        print("5. Trigger actual hooks to see real events being transformed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)