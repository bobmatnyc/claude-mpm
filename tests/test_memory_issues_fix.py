#!/usr/bin/env python3
"""Test and fix identified memory system issues."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def test_specific_issues():
    """Test and identify the specific issues found in comprehensive test."""

    config = Config()
    manager = AgentMemoryManager(config, project_root)

    print("Testing Memory System Issues")
    print("=" * 50)

    # Issue 1: Empty string handling
    print("\n1. Testing empty string handling...")
    test_agent = "test_empty_strings"

    empty_string_response = """
Task completed.

```json
{
  "task_completed": true,
  "remember": ["", "Valid memory", ""]
}
```
"""

    result = manager.extract_and_update_memory(test_agent, empty_string_response)
    print(f"Result: {result}")

    if result:
        memory = manager.load_agent_memory(test_agent)
        print("Memory content:")
        print("-" * 30)
        print(memory)
        print("-" * 30)

        # Check if empty strings were added
        empty_count = memory.count('""') + memory.count("- \n")
        if empty_count > 0:
            print("✗ ISSUE: Empty strings were added to memory")
        else:
            print("✓ Empty strings correctly filtered out")

    # Issue 2: Duplicate prevention
    print("\n2. Testing duplicate prevention...")
    test_agent_dup = "test_duplicate_prevention"

    duplicate_response = """
Task completed.

```json
{
  "task_completed": true,
  "remember": ["This is a test memory item"]
}
```
"""

    # Add same memory twice
    manager.extract_and_update_memory(test_agent_dup, duplicate_response)
    manager.extract_and_update_memory(test_agent_dup, duplicate_response)

    memory = manager.load_agent_memory(test_agent_dup)
    duplicate_count = memory.count("This is a test memory item")

    print(f"Memory added twice, appears {duplicate_count} times")
    if duplicate_count > 1:
        print("✗ ISSUE: Duplicate prevention not working")
        print("Memory content:")
        print(memory)
    else:
        print("✓ Duplicates correctly prevented")

    # Issue 3: Categorization
    print("\n3. Testing categorization...")
    test_agent_cat = "test_categorization"

    pattern_response = """
Task completed.

```json
{
  "task_completed": true,
  "remember": ["Always use dependency injection for service instantiation"]
}
```
"""

    result = manager.extract_and_update_memory(test_agent_cat, pattern_response)
    memory = manager.load_agent_memory(test_agent_cat)

    print("Memory content:")
    print("-" * 30)
    print(memory)
    print("-" * 30)

    if "## Coding Patterns Learned" in memory:
        print("✓ Pattern correctly categorized")
    else:
        print("✗ ISSUE: Pattern not categorized in 'Coding Patterns Learned' section")

    # Issue 4: JSON parsing robustness
    print("\n4. Testing JSON parsing edge cases...")
    test_agent_json = "test_json_parsing"

    # Test malformed JSON
    malformed_response = """
Task completed.

```json
{
  "task_completed": true
  "remember": ["This JSON is missing a comma"]
}
```
"""

    result = manager.extract_and_update_memory(test_agent_json, malformed_response)
    print(f"Malformed JSON result: {result} (should be False)")

    if result:
        print("✗ ISSUE: Malformed JSON was accepted")
    else:
        print("✓ Malformed JSON correctly rejected")

    # Test empty array
    empty_array_response = """
Task completed.

```json
{
  "task_completed": true,
  "remember": []
}
```
"""

    result = manager.extract_and_update_memory(test_agent_json, empty_array_response)
    print(f"Empty array result: {result} (should be False)")

    if result:
        print("✗ ISSUE: Empty array was processed")
    else:
        print("✓ Empty array correctly ignored")


def analyze_categorization_logic():
    """Analyze the categorization logic in detail."""

    print("\n" + "=" * 50)
    print("CATEGORIZATION LOGIC ANALYSIS")
    print("=" * 50)

    config = Config()
    manager = AgentMemoryManager(config, project_root)

    test_cases = [
        (
            "Always use dependency injection for service instantiation",
            "Coding Patterns Learned",
        ),
        (
            "System uses microservices architecture with event-driven communication",
            "Project Architecture",
        ),
        (
            "All public methods must include comprehensive docstrings",
            "Implementation Guidelines",
        ),
        (
            "Never import services directly - use service container",
            "Common Mistakes to Avoid",
        ),
        (
            "Database connections use connection pooling via SQLAlchemy",
            "Integration Points",
        ),
        (
            "Currently working on version 4.0.19 release candidate",
            "Current Technical Context",
        ),
    ]

    for learning, expected_section in test_cases:
        actual_section = manager._categorize_learning(learning)
        status = "✓" if actual_section == expected_section else "✗"
        print(f"{status} '{learning[:50]}...'")
        print(f"   Expected: {expected_section}")
        print(f"   Actual:   {actual_section}")
        print()


def debug_duplicate_logic():
    """Debug the duplicate prevention logic in detail."""

    print("\n" + "=" * 50)
    print("DUPLICATE PREVENTION LOGIC DEBUG")
    print("=" * 50)

    config = Config()
    manager = AgentMemoryManager(config, project_root)

    # Manually test the parsing and duplicate logic
    test_memory = """# Test Agent Memory

<!-- Last Updated: 2025-08-19T04:05:10.068521 -->

## Recent Learnings

- This is a test memory item
"""

    # Parse sections
    sections = manager._parse_memory_sections(test_memory)
    print("Parsed sections:")
    for section, items in sections.items():
        print(f"  {section}: {items}")

    # Test duplicate detection
    new_learning = "This is a test memory item"
    section = "Recent Learnings"

    if section not in sections:
        sections[section] = []

    # Check for duplicates (case-insensitive) - this is the current logic
    normalized_learning = new_learning.lower()
    existing_normalized = [item.lower() for item in sections[section]]

    print(f"\nNew learning: '{new_learning}'")
    print(f"Normalized: '{normalized_learning}'")
    print(f"Existing items: {sections[section]}")
    print(f"Existing normalized: {existing_normalized}")
    print(f"Is duplicate: {normalized_learning in existing_normalized}")

    # The issue might be with how we parse and compare items
    # Let's see what the actual format is
    if sections[section]:
        first_item = sections[section][0]
        print(f"\nFirst existing item raw: '{first_item}'")
        print(f"First existing item stripped: '{first_item.lstrip('- ').strip()}'")
        print(
            f"Comparison should be: '{normalized_learning}' vs '{first_item.lstrip('- ').strip().lower()}'"
        )


if __name__ == "__main__":
    test_specific_issues()
    analyze_categorization_logic()
    debug_duplicate_logic()
