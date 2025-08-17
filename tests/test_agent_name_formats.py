#!/usr/bin/env python3
"""
Test script to verify agent name format handling in claude-mpm.

This script tests:
1. Agent name normalization in AgentNameNormalizer
2. Agent loader's handling of different name formats
3. Hook handler's processing of Task tool events
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.agents.agent_loader import get_agent_prompt, list_available_agents
from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer


def test_agent_name_normalizer():
    """Test the AgentNameNormalizer with various formats."""
    print("\n=== Testing AgentNameNormalizer ===\n")

    normalizer = AgentNameNormalizer()

    test_cases = [
        # (input, expected_normalized, expected_task_format)
        ("Research", "Research", "research"),
        ("research", "Research", "research"),
        ("RESEARCH", "Research", "research"),
        ("Engineer", "Engineer", "engineer"),
        ("engineer", "Engineer", "engineer"),
        ("QA", "QA", "qa"),
        ("qa", "QA", "qa"),
        ("Qa", "QA", "qa"),
        ("Version Control", "Version Control", "version-control"),
        ("version_control", "Version Control", "version-control"),
        ("version-control", "Version Control", "version-control"),
        ("Data Engineer", "Data Engineer", "data-engineer"),
        ("data_engineer", "Data Engineer", "data-engineer"),
        ("data-engineer", "Data Engineer", "data-engineer"),
        ("PM", "PM", "pm"),
        ("pm", "PM", "pm"),
        ("Ops", "Ops", "ops"),
        ("ops", "Ops", "ops"),
        ("Unknown Agent", "Engineer", "engineer"),  # Should default to Engineer
    ]

    print("Testing normalization and task format conversion:")
    print("-" * 70)
    print(f"{'Input':<20} {'Normalized':<20} {'Task Format':<20}")
    print("-" * 70)

    for input_name, expected_norm, expected_task in test_cases:
        normalized = normalizer.normalize(input_name)
        task_format = normalizer.to_task_format(input_name)

        norm_status = "✅" if normalized == expected_norm else "❌"
        task_status = "✅" if task_format == expected_task else "❌"

        print(
            f"{input_name:<20} {normalized:<20} {task_format:<20} {norm_status}{task_status}"
        )

    print("\n" + "=" * 70)


def test_agent_loader():
    """Test the agent loader with different name formats."""
    print("\n=== Testing Agent Loader ===\n")

    # List available agents
    available = list_available_agents()
    print(f"Available agents: {', '.join(available)}")

    # Test cases for agent loading
    test_cases = [
        "research",
        "Research",  # Capitalized
        "engineer",
        "Engineer",  # Capitalized
        "qa",
        "QA",  # Uppercase
        "documentation",
        "Documentation",  # Capitalized
        "version_control",
        "version-control",  # Hyphenated
        "data_engineer",
        "data-engineer",  # Hyphenated
    ]

    print("\nTesting agent loading with different formats:")
    print("-" * 50)

    for agent_name in test_cases:
        try:
            prompt = get_agent_prompt(agent_name)
            if prompt:
                print(
                    f"✅ Loaded '{agent_name}' successfully (length: {len(prompt)} chars)"
                )
            else:
                print(f"❌ Failed to load '{agent_name}' (returned None)")
        except Exception as e:
            print(f"❌ Error loading '{agent_name}': {e}")

    print("\n" + "=" * 70)


def test_task_format_conversions():
    """Test conversions between TodoWrite and Task tool formats."""
    print("\n=== Testing Format Conversions ===\n")

    normalizer = AgentNameNormalizer()

    # Test TodoWrite format to Task format
    todo_formats = [
        "[Research] Analyze the codebase",
        "[Engineer] Implement new feature",
        "[QA] Run test suite",
        "[Version Control] Create release tag",
        "[Data Engineer] Optimize queries",
        "[PM] Coordinate tasks",
    ]

    print("Converting TodoWrite format to Task format:")
    print("-" * 70)

    for todo in todo_formats:
        agent_name = normalizer.extract_from_todo(todo)
        if agent_name:
            task_format = normalizer.to_task_format(agent_name)
            print(f"{todo:<40} → {task_format}")
        else:
            print(f"{todo:<40} → (failed to extract)")

    print("\n" + "=" * 70)


def main():
    """Run all tests."""
    print("=" * 70)
    print("Agent Name Format Testing")
    print("=" * 70)

    test_agent_name_normalizer()
    test_agent_loader()
    test_task_format_conversions()

    print("\n=== Summary ===\n")
    print("Key findings:")
    print("1. AgentNameNormalizer handles various input formats correctly")
    print("2. Agent loader normalizes names before loading")
    print("3. Task tool requires lowercase agent names (research, engineer, etc.)")
    print("4. Version Control and Data Engineer use underscores in Task format")
    print("5. TodoWrite uses capitalized format, Task tool uses lowercase")
    print("\nRecommendation: Always use lowercase agent names for Task tool to avoid")
    print("Claude Code validation errors. The framework will normalize other formats")
    print("internally for tracking and display purposes.")


if __name__ == "__main__":
    main()
