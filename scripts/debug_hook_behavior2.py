#!/usr/bin/env python3
"""Debug script to understand hook behavior in detail."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from claude_mpm.hooks.builtin.todo_agent_prefix_hook import TodoAgentPrefixHook
from claude_mpm.hooks.base_hook import HookContext, HookType
from claude_mpm.core.agent_name_normalizer import agent_name_normalizer

# Create hook instance
hook = TodoAgentPrefixHook()

# Test cases from the failing test
test_cases = [
    ("Research best practices for testing", "[Research]"),
    ("Implement new feature", "[Engineer]"),
    ("Test the implementation", "[QA]"),
    ("Document the API", "[Documentation]"),
    ("Check security vulnerabilities", "[Security]"),
    ("Deploy to production", "[Ops]"),
    ("Create data pipeline", "[Data Engineer]"),
    ("Create new git branch", "[Version Control]"),
]

for content, expected_prefix in test_cases:
    print(f"\nTesting: '{content}'")
    print(f"Expected prefix: {expected_prefix}")
    
    # Check if it already has a prefix
    has_prefix = hook._has_agent_prefix(content)
    print(f"Has prefix: {has_prefix}")
    
    # Check what agent it suggests
    suggested = hook._suggest_agent(content)
    print(f"Suggested agent: {suggested}")
    
    if suggested:
        prefix = agent_name_normalizer.to_todo_prefix(suggested)
        print(f"Generated prefix: {prefix}")
    
    # Create context and execute
    context = HookContext(
        hook_type=HookType.CUSTOM,
        data={
            'tool_name': 'TodoWrite',
            'parameters': {
                'todos': [{'content': content}]
            }
        },
        metadata={},
        timestamp=datetime.now()
    )
    
    result = hook.execute(context)
    print(f"Result - Success: {result.success}, Modified: {result.modified}")
    
    if result.modified and result.data:
        updated_content = result.data['parameters']['todos'][0]['content']
        print(f"Updated content: '{updated_content}'")
    elif result.error:
        print(f"Error: {result.error}")
    
    print("-" * 50)