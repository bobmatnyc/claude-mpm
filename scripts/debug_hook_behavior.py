#!/usr/bin/env python3
"""Debug script to understand hook behavior."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from claude_mpm.hooks.builtin.todo_agent_prefix_hook import TodoAgentPrefixHook
from claude_mpm.hooks.base_hook import HookContext, HookType

# Create hook instance
hook = TodoAgentPrefixHook()

# Test case
test_todo = "Research best practices for testing"
context = HookContext(
    hook_type=HookType.CUSTOM,
    data={
        'tool_name': 'TodoWrite',
        'parameters': {
            'todos': [{'content': test_todo}]
        }
    },
    metadata={},
    timestamp=datetime.now()
)

print(f"Testing todo: '{test_todo}'")
print(f"Hook validation: {hook.validate(context)}")

# Execute hook
result = hook.execute(context)

print(f"\nResult:")
print(f"  Success: {result.success}")
print(f"  Modified: {result.modified}")
print(f"  Error: {result.error}")

if result.success and result.modified:
    updated_todos = result.data['parameters']['todos']
    print(f"  Updated content: '{updated_todos[0]['content']}'")

# Test with a todo that already has a prefix
prefixed_todo = "[Research] Analyze patterns"
context2 = HookContext(
    hook_type=HookType.CUSTOM,
    data={
        'tool_name': 'TodoWrite',
        'parameters': {
            'todos': [{'content': prefixed_todo}]
        }
    },
    metadata={},
    timestamp=datetime.now()
)

print(f"\n\nTesting prefixed todo: '{prefixed_todo}'")
result2 = hook.execute(context2)
print(f"Result:")
print(f"  Success: {result2.success}")
print(f"  Modified: {result2.modified}")