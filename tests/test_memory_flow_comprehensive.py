#!/usr/bin/env python3
"""Comprehensive test for memory flow and categorization."""

import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def test_memory_categorization():
    """Test that memories are categorized correctly by type."""

    config = Config()
    manager = AgentMemoryManager(config, project_root)

    # Clean slate for testing
    test_agent = "test_categorization_agent"

    # Remove any existing memory file
    memory_file = manager.memories_dir / f"{test_agent}_memories.md"
    if memory_file.exists():
        memory_file.unlink()

    # Test response with different memory types
    test_responses = [
        {
            "name": "architecture_memory",
            "response": """
Task completed.

```json
{
  "task_completed": true,
  "remember": [
    "System uses microservices architecture with event-driven communication"
  ]
}
```
""",
            "expected_section": "Project Architecture",
        },
        {
            "name": "pattern_memory",
            "response": """
Task completed.

```json
{
  "task_completed": true,
  "remember": [
    "Always use dependency injection for service instantiation"
  ]
}
```
""",
            "expected_section": "Coding Patterns Learned",
        },
        {
            "name": "mistake_memory",
            "response": """
Task completed.

```json
{
  "task_completed": true,
  "remember": [
    "Never import services directly - use service container"
  ]
}
```
""",
            "expected_section": "Common Mistakes to Avoid",
        },
        {
            "name": "integration_memory",
            "response": """
Task completed.

```json
{
  "task_completed": true,
  "remember": [
    "Database connections use connection pooling via SQLAlchemy"
  ]
}
```
""",
            "expected_section": "Integration Points",
        },
        {
            "name": "context_memory",
            "response": """
Task completed.

```json
{
  "task_completed": true,
  "remember": [
    "Currently working on version 4.0.19 release candidate"
  ]
}
```
""",
            "expected_section": "Current Technical Context",
        },
        {
            "name": "guideline_memory",
            "response": """
Task completed.

```json
{
  "task_completed": true,
  "remember": [
    "All public methods must include comprehensive docstrings"
  ]
}
```
""",
            "expected_section": "Implementation Guidelines",
        },
    ]

    print("Testing memory categorization...")

    for test_case in test_responses:
        print(f"\n• Testing {test_case['name']}...")

        success = manager.extract_and_update_memory(test_agent, test_case["response"])

        if not success:
            print(f"✗ Failed to extract memory from {test_case['name']}")
            return False

        # Verify memory was categorized correctly
        memory_content = manager.load_agent_memory(test_agent)

        # Check if the expected section exists
        if f"## {test_case['expected_section']}" not in memory_content:
            print(f"✗ Expected section '{test_case['expected_section']}' not found")
            return False

        # Extract the memory text from the response
        memory_match = re.search(r'"remember":\s*\[\s*"([^"]+)"', test_case["response"])
        if memory_match:
            memory_text = memory_match.group(1)
            if memory_text not in memory_content:
                print(f"✗ Memory text '{memory_text}' not found in memory file")
                return False

        print(
            f"✓ {test_case['name']} categorized correctly in '{test_case['expected_section']}'"
        )

    print("\n✓ All memory types categorized correctly!")

    # Show final memory structure
    print("\nFinal memory structure:")
    print("-" * 60)
    memory_content = manager.load_agent_memory(test_agent)
    print(memory_content)
    print("-" * 60)

    return True


def test_duplicate_prevention():
    """Test that duplicate memories are not added."""

    config = Config()
    manager = AgentMemoryManager(config, project_root)

    test_agent = "test_duplicate_agent"

    # Clean slate - remove any existing memory
    memory_file = manager.memories_dir / f"{test_agent}_memories.md"
    if memory_file.exists():
        memory_file.unlink()

    # Add a memory twice
    duplicate_response = """
Task completed.

```json
{
  "task_completed": true,
  "remember": [
    "This is a duplicate memory that should only appear once"
  ]
}
```
"""

    print("Testing duplicate memory prevention...")

    # Add memory first time
    success1 = manager.extract_and_update_memory(test_agent, duplicate_response)
    if not success1:
        print("✗ Failed to add memory first time")
        return False

    # Add same memory second time
    manager.extract_and_update_memory(test_agent, duplicate_response)

    # Check memory content
    memory_content = manager.load_agent_memory(test_agent)
    memory_count = memory_content.count(
        "This is a duplicate memory that should only appear once"
    )

    if memory_count == 1:
        print("✓ Duplicate memory correctly prevented")
        return True
    print(f"✗ Memory appears {memory_count} times (should be 1)")
    return False


def test_json_parsing_edge_cases():
    """Test edge cases in JSON parsing."""

    config = Config()
    manager = AgentMemoryManager(config, project_root)

    test_agent = "test_edge_cases_agent"

    edge_cases = [
        {
            "name": "malformed_json",
            "response": """
Task completed.

```json
{
  "task_completed": true
  "remember": [
    "This JSON is missing a comma"
  ]
}
```
""",
            "should_succeed": False,
        },
        {
            "name": "empty_remember_array",
            "response": """
Task completed.

```json
{
  "task_completed": true,
  "remember": []
}
```
""",
            "should_succeed": False,  # Empty arrays should be ignored
        },
        {
            "name": "remember_with_empty_string",
            "response": """
Task completed.

```json
{
  "task_completed": true,
  "remember": [""]
}
```
""",
            "should_succeed": False,  # Empty strings should be ignored
        },
        {
            "name": "no_json_block",
            "response": """
Task completed without any JSON block.
""",
            "should_succeed": False,
        },
        {
            "name": "multiple_json_blocks",
            "response": """
First block:
```json
{
  "task_completed": true,
  "remember": ["First memory"]
}
```

Second block:
```json
{
  "task_completed": true,
  "remember": ["Second memory"]
}
```
""",
            "should_succeed": True,  # Should find the first valid one
        },
    ]

    print("Testing JSON parsing edge cases...")

    for test_case in edge_cases:
        print(f"\n• Testing {test_case['name']}...")

        success = manager.extract_and_update_memory(test_agent, test_case["response"])

        if success == test_case["should_succeed"]:
            print(f"✓ {test_case['name']} handled correctly (success={success})")
        else:
            print(
                f"✗ {test_case['name']} handled incorrectly (expected success={test_case['should_succeed']}, got={success})"
            )
            return False

    return True


def main():
    """Run all memory flow tests."""

    print("Memory Flow Comprehensive Test")
    print("=" * 60)

    tests = [
        ("Memory Categorization", test_memory_categorization),
        ("Duplicate Prevention", test_duplicate_prevention),
        ("JSON Parsing Edge Cases", test_json_parsing_edge_cases),
    ]

    all_passed = True

    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))

        try:
            passed = test_func()
            if passed:
                print(f"✓ {test_name} passed")
            else:
                print(f"✗ {test_name} failed")
                all_passed = False
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    print("✗ Some tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
