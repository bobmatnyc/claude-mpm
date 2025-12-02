#!/usr/bin/env python3
"""
Demonstration script showing agent name consistency between TodoWrite and Task tools.

This script demonstrates:
1. TodoWrite accepting bracketed agent names like [Research], [Version Control]
2. Task tool accepting both capitalized and lowercase formats
3. Proper conversion between formats
4. Error handling for invalid agent names
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print("=" * 60)


def demonstrate_agent_normalization():
    """Demonstrate the agent name normalization functionality."""
    print_section("Agent Name Normalization")

    # Show all supported agents
    print("\nSupported agent types:")
    for key, canonical in AgentNameNormalizer.CANONICAL_NAMES.items():
        print(f"  {key:20} -> {canonical}")

    # Demonstrate normalization
    print("\nNormalization examples:")
    test_inputs = [
        "research",
        "Research",
        "RESEARCH",
        "researcher",
        "version_control",
        "version-control",
        "Version Control",
        "git",
        "data_engineer",
        "data-engineer",
        "Data Engineer",
        "data",
        "qa",
        "QA",
        "testing",
        "test",
    ]

    for input_name in test_inputs:
        normalized = AgentNameNormalizer.normalize(input_name)
        print(f"  '{input_name:20}' -> '{normalized}'")


def demonstrate_todo_format():
    """Demonstrate TodoWrite format handling."""
    print_section("TodoWrite Format")

    # Show TODO prefix generation
    print("\nTODO prefix generation:")
    agents = ["Research", "Engineer", "Version Control", "Data Engineer", "QA"]
    for agent in agents:
        prefix = AgentNameNormalizer.to_todo_prefix(agent)
        print(f"  {agent:20} -> {prefix}")

    # Show extraction from TODOs
    print("\nExtracting agents from TODO text:")
    todos = [
        "[Research] Analyze user behavior patterns",
        "[Version Control] Create release branch v2.0",
        "[Data Engineer] Build data pipeline for analytics",
        "[QA] Run integration test suite",
        "[Security] Perform security audit",
    ]

    for todo in todos:
        agent = AgentNameNormalizer.extract_from_todo(todo)
        print(f"  '{todo[:50]}...' -> Agent: {agent}")

    # Show validation
    print("\nTODO format validation:")
    test_todos = [
        "[Research] Valid todo",
        "[Invalid Agent] This won't work",
        "Missing prefix todo",
        "[Version Control] Another valid todo",
    ]

    for todo in test_todos:
        is_valid, error = AgentNameNormalizer.validate_todo_format(todo)
        status = "✓ Valid" if is_valid else f"✗ Invalid: {error[:50]}..."
        print(f"  '{todo[:30]:30}' -> {status}")


def demonstrate_task_format_conversion():
    """Demonstrate conversion between TodoWrite and Task formats."""
    print_section("TodoWrite <-> Task Format Conversion")

    # TodoWrite to Task format
    print("\nTodoWrite format -> Task format:")
    todo_formats = [
        "Research",
        "Engineer",
        "QA",
        "Security",
        "Documentation",
        "Ops",
        "Version Control",
        "Data Engineer",
        "Architect",
        "PM",
    ]

    for todo_format in todo_formats:
        task_format = AgentNameNormalizer.to_task_format(todo_format)
        print(f"  {todo_format:20} -> {task_format}")

    # Task to TodoWrite format
    print("\nTask format -> TodoWrite format:")
    task_formats = [
        "research",
        "engineer",
        "qa",
        "security",
        "documentation",
        "ops",
        "version-control",
        "data-engineer",
        "architect",
        "pm",
    ]

    for task_format in task_formats:
        todo_format = AgentNameNormalizer.from_task_format(task_format)
        print(f"  {task_format:20} -> {todo_format}")


def demonstrate_hook_behavior():
    """Demonstrate the TodoAgentPrefixHook behavior."""
    print_section("TodoAgentPrefixHook Behavior")

    # NOTE: TodoAgentPrefixHook has been deprecated
    # Use AgentNameNormalizer.to_todo_prefix() instead
    print("\nNote: TodoAgentPrefixHook has been deprecated.")
    print("Use AgentNameNormalizer for agent name normalization.")
    return  # Skip deprecated functionality

    # Original code below (commented out for reference)
    # hook = TodoAgentPrefixHook()
    # Test auto-prefix addition
    print("\nAuto-prefix addition:")
    test_todos = [
        "Research best practices for microservices",
        "Implement user authentication feature",
        "Test the new API endpoints",
        "Document the deployment process",
        "Deploy to production environment",
        "Create data pipeline for analytics",
        "Create git branch for hotfix",
    ]

    for todo_content in test_todos:
        context = HookContext(
            hook_type=HookType.CUSTOM,
            data={
                "tool_name": "TodoWrite",
                "parameters": {"todos": [{"content": todo_content}]},
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = hook.execute(context)

        if result.success and result.modified:
            new_content = result.data["parameters"]["todos"][0]["content"]
            print(f"  '{todo_content[:40]:40}' -> '{new_content}'")
        else:
            print(f"  '{todo_content[:40]:40}' -> Error: {result.error[:30]}...")

    # Test preservation of existing prefixes
    print("\nPreservation of existing prefixes:")
    prefixed_todos = [
        "[Research] Analyze patterns",
        "[Version Control] Create release",
        "[Data Engineer] Build pipeline",
    ]

    for todo_content in prefixed_todos:
        context = HookContext(
            hook_type=HookType.CUSTOM,
            data={
                "tool_name": "TodoWrite",
                "parameters": {"todos": [{"content": todo_content}]},
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = hook.execute(context)

        status = "Not modified" if not result.modified else "Modified"
        print(f"  '{todo_content}' -> {status}")


def demonstrate_color_coding():
    """Demonstrate agent color coding."""
    print_section("Agent Color Coding")

    print("\nColorized agent names:")
    agents = [
        "Research",
        "Engineer",
        "QA",
        "Security",
        "Documentation",
        "Ops",
        "Version Control",
        "Data Engineer",
        "Architect",
        "PM",
    ]

    for agent in agents:
        colorized = AgentNameNormalizer.colorize(agent)
        print(f"  {colorized}")

    print("\nColorized with custom text:")
    colorized = AgentNameNormalizer.colorize("research", "[Research] Analyze patterns")
    print(f"  {colorized}")


def demonstrate_error_cases():
    """Demonstrate error handling."""
    print_section("Error Handling")

    # Unknown agents
    print("\nHandling unknown agents:")
    unknown = ["unknown_agent", "random", "xyz", ""]
    for agent in unknown:
        normalized = AgentNameNormalizer.normalize(agent)
        print(f"  '{agent:20}' -> '{normalized}' (fallback)")

    # Invalid TODO formats
    # NOTE: TodoAgentPrefixValidatorHook has been deprecated
    print("\nNote: TodoAgentPrefixValidatorHook has been deprecated.")
    print("Use AgentNameNormalizer for validation.")
    return  # Skip deprecated functionality

    # Original code below (commented out)
    # validator = TodoAgentPrefixValidatorHook()
    # print("\nValidating invalid TODO formats:")
    invalid_todos = [
        "No prefix here",
        "[Unknown] Invalid agent",
        "[] Empty brackets",
        "[Research] [Engineer] Multiple prefixes?",
    ]

    for todo_content in invalid_todos:
        context = HookContext(
            hook_type=HookType.CUSTOM,
            data={
                "tool_name": "TodoWrite",
                "parameters": {"todos": [{"content": todo_content}]},
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = validator.execute(context)

        if not result.success:
            print(f"  '{todo_content[:30]:30}' -> Error detected")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print(" Agent Name Consistency Demonstration")
    print(" TodoWrite and Task Tool Integration")
    print("=" * 60)

    demonstrate_agent_normalization()
    demonstrate_todo_format()
    demonstrate_task_format_conversion()
    demonstrate_hook_behavior()
    demonstrate_color_coding()
    demonstrate_error_cases()

    print_section("Summary")
    print(
        """
This demonstration shows that:

1. ✓ TodoWrite accepts bracketed agent names like [Research], [Version Control]
2. ✓ Task tool can accept both formats:
   - Capitalized: "Research", "Version Control"
   - Lowercase with hyphens: "research", "version-control"
3. ✓ Proper conversion between formats is supported
4. ✓ Invalid agent names are handled with appropriate errors
5. ✓ All agent types have consistent naming across the system

The agent name normalization ensures consistency between:
- TodoWrite prefixes: [Research], [Version Control], [Data Engineer]
- Task tool formats: research, version-control, data-engineer
- Display names: Research, Version Control, Data Engineer
"""
    )


if __name__ == "__main__":
    main()
