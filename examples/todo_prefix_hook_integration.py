#!/usr/bin/env python3
"""
Example integration of the TodoAgentPrefixHook into a claude-mpm orchestrator.

This demonstrates how to integrate the hook into your existing tool execution flow.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.logger import get_logger
from claude_mpm.hooks.builtin.todo_agent_prefix_hook import TodoAgentPrefixHook
from claude_mpm.hooks.tool_call_interceptor import SimpleHookRunner, ToolCallInterceptor

logger = get_logger(__name__)


class ToolExecutorWithHooks:
    """Example tool executor that integrates hook system."""

    def __init__(self):
        """Initialize the tool executor with hooks."""
        # Set up hook system
        self.hook_runner = SimpleHookRunner()
        self.interceptor = ToolCallInterceptor(self.hook_runner)

        # Register the TodoAgentPrefixHook
        todo_hook = TodoAgentPrefixHook()
        self.hook_runner.register_hook(todo_hook)

        logger.info("Tool executor initialized with TodoAgentPrefixHook")

    def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a tool with hook interception.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            metadata: Optional metadata

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool execution is blocked by hooks
        """
        # Intercept the tool call
        interception_result = self.interceptor.intercept_tool_call_sync(
            tool_name, parameters, metadata
        )

        # Check if allowed
        if not interception_result["allowed"]:
            raise ValueError(f"Tool call blocked: {interception_result['error']}")

        # Log if parameters were modified
        if parameters != interception_result["parameters"]:
            logger.info(f"Tool parameters modified by hooks for {tool_name}")

        # Execute the tool with potentially modified parameters
        return self._execute_tool_internal(tool_name, interception_result["parameters"])

    def _execute_tool_internal(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Internal tool execution logic.

        This is where you would integrate with your actual tool execution system.
        """
        # Simulate tool execution
        if tool_name == "TodoWrite":
            todos = parameters.get("todos", [])
            print("\n[TodoWrite Tool Executed]")
            print(f"Creating {len(todos)} todo items:")
            for todo in todos:
                print(f"  - {todo['content']}")
            return {"success": True, "todos_created": len(todos)}
        print(f"\n[{tool_name} Tool Executed]")
        print(f"Parameters: {parameters}")
        return {"success": True}


def demo_integration():
    """Demonstrate the integration in action."""
    print("=== Tool Executor with Hook Integration Demo ===\n")

    # Create executor
    executor = ToolExecutorWithHooks()

    # Test cases
    test_cases = [
        {
            "name": "TodoWrite with missing prefixes",
            "tool": "TodoWrite",
            "params": {
                "todos": [
                    {
                        "content": "implement payment processing",
                        "status": "pending",
                        "priority": "high",
                        "id": "1",
                    },
                    {
                        "content": "add unit tests for payment module",
                        "status": "pending",
                        "priority": "medium",
                        "id": "2",
                    },
                    {
                        "content": "research payment gateway options",
                        "status": "pending",
                        "priority": "low",
                        "id": "3",
                    },
                ]
            },
        },
        {
            "name": "TodoWrite with mixed prefixes",
            "tool": "TodoWrite",
            "params": {
                "todos": [
                    {
                        "content": "Security: audit payment system",
                        "status": "pending",
                        "priority": "high",
                        "id": "1",
                    },
                    {
                        "content": "deploy payment service to staging",
                        "status": "pending",
                        "priority": "medium",
                        "id": "2",
                    },
                ]
            },
        },
        {
            "name": "Other tool (no interception)",
            "tool": "Read",
            "params": {"file_path": "/example/path.py"},
        },
    ]

    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        print("-" * 50)

        try:
            result = executor.execute_tool(test_case["tool"], test_case["params"])
            print(f"\nResult: {result}")
        except ValueError as e:
            print(f"\nError: {e}")

        print("\n" + "=" * 70)


def demo_configuration_options():
    """Show different configuration options."""
    print("\n=== Configuration Options Demo ===\n")

    # Option 1: Auto-prefix only
    print("1. Auto-prefix mode (default):")
    executor1 = ToolExecutorWithHooks()

    # Option 2: Validation only
    print("\n2. Validation-only mode:")
    from claude_mpm.hooks.builtin.todo_agent_prefix_hook import (
        TodoAgentPrefixValidatorHook,
    )

    executor2 = ToolExecutorWithHooks()
    # Replace with validator
    executor2.hook_runner = SimpleHookRunner()
    validator = TodoAgentPrefixValidatorHook()
    executor2.hook_runner.register_hook(validator)
    executor2.interceptor = ToolCallInterceptor(executor2.hook_runner)

    # Option 3: Both hooks with priorities
    print("\n3. Combined mode (validator then auto-fix):")
    executor3 = ToolExecutorWithHooks()
    executor3.hook_runner = SimpleHookRunner()

    # Auto-fix runs first (lower priority)
    auto_hook = TodoAgentPrefixHook()
    auto_hook.priority = 10
    executor3.hook_runner.register_hook(auto_hook)

    # Validator runs second
    validator2 = TodoAgentPrefixValidatorHook()
    validator2.priority = 20
    executor3.hook_runner.register_hook(validator2)

    executor3.interceptor = ToolCallInterceptor(executor3.hook_runner)

    # Test with each configuration
    test_params = {
        "todos": [
            {
                "content": "analyze performance metrics",
                "status": "pending",
                "priority": "high",
                "id": "1",
            }
        ]
    }

    print("\nTesting each configuration with: 'analyze performance metrics'")
    print("-" * 50)

    for i, executor in enumerate([executor1, executor2, executor3], 1):
        print(f"\nConfiguration {i}:")
        try:
            executor.execute_tool("TodoWrite", test_params.copy())
            print("Success!")
        except ValueError as e:
            print(f"Blocked: {e}")


if __name__ == "__main__":
    demo_integration()
    demo_configuration_options()

    print("\n=== Integration Summary ===")
    print("1. Create SimpleHookRunner and ToolCallInterceptor")
    print("2. Register TodoAgentPrefixHook (or TodoAgentPrefixValidatorHook)")
    print("3. Call interceptor.intercept_tool_call_sync() before tool execution")
    print("4. Use modified parameters if allowed")
    print("5. Handle blocking errors appropriately")
