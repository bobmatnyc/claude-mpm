#!/usr/bin/env python3
"""Test script for TodoAgentPrefixHook."""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.hooks.builtin.todo_agent_prefix_hook import TodoAgentPrefixHook
from claude_mpm.hooks.base_hook import HookContext, HookType
from datetime import datetime


def test_todo_hook():
    """Test the TodoAgentPrefixHook with various inputs."""
    hook = TodoAgentPrefixHook()
    
    print(f"Testing TodoAgentPrefixHook")
    print(f"  Name: {hook.name}")
    print(f"  Priority: {hook.priority}")
    print(f"  Enabled: {hook.enabled}")
    print("-" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Todo without prefix",
            "todos": [
                {"id": "1", "content": "Implement feature X", "status": "pending", "priority": "high"},
                {"id": "2", "content": "Test the implementation", "status": "pending", "priority": "medium"},
            ]
        },
        {
            "name": "Todo with partial prefixes",
            "todos": [
                {"id": "1", "content": "[Engineer] Implement feature X", "status": "pending", "priority": "high"},
                {"id": "2", "content": "Test the implementation", "status": "pending", "priority": "medium"},
                {"id": "3", "content": "[QA] Run comprehensive tests", "status": "pending", "priority": "high"},
            ]
        },
        {
            "name": "Todo with all prefixes",
            "todos": [
                {"id": "1", "content": "[Engineer] Implement feature X", "status": "pending", "priority": "high"},
                {"id": "2", "content": "[QA] Test the implementation", "status": "pending", "priority": "medium"},
            ]
        },
    ]
    
    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        print("Input todos:")
        for todo in test_case['todos']:
            print(f"  - {todo['content']}")
        
        # Create context
        context = HookContext(
            hook_type=HookType.CUSTOM,
            data={
                "tool_name": "TodoWrite",
                "parameters": {
                    "todos": test_case['todos']
                }
            },
            metadata={},
            timestamp=datetime.now()
        )
        
        # Execute hook
        result = hook.execute(context)
        
        print("\nResult:")
        print(f"  Success: {result.success}")
        if result.error:
            print(f"  Error: {result.error}")
        if result.modified:
            print("  Modified todos:")
            for todo in result.data.get('parameters', {}).get('todos', []):
                print(f"    - {todo['content']}")
        else:
            print("  No modifications")
        
        if result.metadata and result.metadata.get('warnings'):
            print("  Warnings:")
            for warning in result.metadata['warnings']:
                print(f"    - {warning}")


if __name__ == "__main__":
    test_todo_hook()