#!/usr/bin/env python3
"""Example of using the TodoAgentPrefixHook to enforce agent prefixes."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from claude_mpm.hooks.builtin.todo_agent_prefix_hook import TodoAgentPrefixHook, TodoAgentPrefixValidatorHook
from claude_mpm.hooks.tool_call_interceptor import ToolCallInterceptor, SimpleHookRunner
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


def demo_auto_prefix_enforcement():
    """Demonstrate automatic prefix addition."""
    print("\n=== Auto-Prefix Enforcement Demo ===\n")
    
    # Create hook runner and register the auto-prefix hook
    runner = SimpleHookRunner()
    auto_hook = TodoAgentPrefixHook()
    runner.register_hook(auto_hook)
    
    # Create interceptor
    interceptor = ToolCallInterceptor(runner)
    
    # Test cases
    test_todos = [
        {
            'todos': [
                {'content': 'implement user authentication', 'status': 'pending', 'priority': 'high', 'id': '1'},
                {'content': 'write unit tests for auth module', 'status': 'pending', 'priority': 'medium', 'id': '2'},
                {'content': 'research best practices for JWT', 'status': 'pending', 'priority': 'low', 'id': '3'},
                {'content': '[Engineer] fix login bug', 'status': 'pending', 'priority': 'high', 'id': '4'},  # Already has prefix
            ]
        }
    ]
    
    for params in test_todos:
        print("Original todos:")
        for todo in params['todos']:
            print(f"  - {todo['content']}")
        
        # Intercept the TodoWrite call
        result = interceptor.intercept_tool_call_sync('TodoWrite', params)
        
        if result['allowed']:
            print("\nModified todos (with auto-added prefixes):")
            for todo in result['parameters']['todos']:
                print(f"  - {todo['content']}")
        else:
            print(f"\nBlocked: {result['error']}")
        
        print("\n" + "-" * 50)


def demo_validation_only():
    """Demonstrate validation-only mode."""
    print("\n=== Validation-Only Demo ===\n")
    
    # Create hook runner and register the validator hook
    runner = SimpleHookRunner()
    validator_hook = TodoAgentPrefixValidatorHook()
    runner.register_hook(validator_hook)
    
    # Create interceptor
    interceptor = ToolCallInterceptor(runner)
    
    # Test cases
    test_cases = [
        {
            'name': 'Valid todos with proper prefixes',
            'params': {
                'todos': [
                    {'content': '[Engineer] implement user authentication', 'status': 'pending', 'priority': 'high', 'id': '1'},
                    {'content': '[QA] write unit tests for auth module', 'status': 'pending', 'priority': 'medium', 'id': '2'},
                    {'content': '[Research] investigate OAuth2 best practices', 'status': 'pending', 'priority': 'low', 'id': '3'},
                ]
            }
        },
        {
            'name': 'Invalid todos missing prefixes',
            'params': {
                'todos': [
                    {'content': 'implement payment processing', 'status': 'pending', 'priority': 'high', 'id': '1'},
                    {'content': 'debug checkout flow', 'status': 'pending', 'priority': 'medium', 'id': '2'},
                ]
            }
        },
        {
            'name': 'Mixed valid and invalid',
            'params': {
                'todos': [
                    {'content': '[Security] audit authentication system', 'status': 'pending', 'priority': 'high', 'id': '1'},
                    {'content': 'update documentation', 'status': 'pending', 'priority': 'low', 'id': '2'},  # Missing prefix
                    {'content': '[Ops] configure CI/CD pipeline', 'status': 'pending', 'priority': 'medium', 'id': '3'},
                ]
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"Test: {test_case['name']}")
        print("Todos:")
        for todo in test_case['params']['todos']:
            print(f"  - {todo['content']}")
        
        # Intercept the TodoWrite call
        result = interceptor.intercept_tool_call_sync('TodoWrite', test_case['params'])
        
        if result['allowed']:
            print("✅ Validation passed!")
        else:
            print(f"❌ Validation failed:\n{result['error']}")
        
        print("\n" + "-" * 50)


def demo_combined_hooks():
    """Demonstrate using both hooks with different priorities."""
    print("\n=== Combined Hooks Demo ===\n")
    
    # Create hook runner and register both hooks
    runner = SimpleHookRunner()
    
    # Register validator first (lower priority number = runs first)
    validator_hook = TodoAgentPrefixValidatorHook()
    validator_hook.priority = 10
    runner.register_hook(validator_hook)
    
    # Register auto-fixer second
    auto_hook = TodoAgentPrefixHook()
    auto_hook.priority = 20
    runner.register_hook(auto_hook)
    
    # Create interceptor
    interceptor = ToolCallInterceptor(runner)
    
    # Test with todos that need prefixes
    params = {
        'todos': [
            {'content': 'analyze system performance', 'status': 'pending', 'priority': 'high', 'id': '1'},
            {'content': 'optimize database queries', 'status': 'pending', 'priority': 'medium', 'id': '2'},
        ]
    }
    
    print("Original todos:")
    for todo in params['todos']:
        print(f"  - {todo['content']}")
    
    # Note: In this configuration, the validator will fail first before auto-fix can run
    # To have auto-fix run first, swap the priorities
    result = interceptor.intercept_tool_call_sync('TodoWrite', params)
    
    if result['allowed']:
        print("\n✅ Allowed! Final todos:")
        for todo in result['parameters']['todos']:
            print(f"  - {todo['content']}")
    else:
        print(f"\n❌ Blocked:\n{result['error']}")


if __name__ == '__main__':
    # Run all demos
    demo_auto_prefix_enforcement()
    demo_validation_only()
    demo_combined_hooks()
    
    print("\n=== Hook Configuration Tips ===")
    print("1. Use TodoAgentPrefixHook for automatic prefix addition")
    print("2. Use TodoAgentPrefixValidatorHook for strict validation")
    print("3. Control execution order with priority values (lower = first)")
    print("4. Register hooks with the SimpleHookRunner in your orchestrator")
    print("5. Use ToolCallInterceptor to integrate with your tool execution flow")