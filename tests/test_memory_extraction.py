#!/usr/bin/env python3
"""Test script to verify memory extraction from agent responses."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def test_memory_extraction():
    """Test that memory extraction works correctly."""

    # Initialize memory manager
    config = Config()
    manager = AgentMemoryManager(config, project_root)

    # Test agent response with remember field
    test_response = """
    I've completed the analysis of the codebase.

    ## Summary
    The project uses a service-oriented architecture with clear separation of concerns.

    ```json
    {
      "task_completed": true,
      "instructions": "Analyze the project architecture",
      "results": "Identified service-oriented architecture with 5 domains",
      "files_modified": [],
      "tools_used": ["Read", "Grep"],
      "remember": [
        "Project uses service-oriented architecture with 5 domains",
        "All services implement explicit interfaces for DI",
        "Memory files stored in .claude/memories/ directory"
      ]
    }
    ```
    """

    # Test extraction
    print("Testing memory extraction from agent response...")
    success = manager.extract_and_update_memory("test_agent", test_response)

    if success:
        print("✓ Memory extraction successful!")

        # Load the memory to verify
        memory_content = manager.load_agent_memory("test_agent")
        print("\nExtracted memory content:")
        print("-" * 50)
        print(memory_content)
        print("-" * 50)
    else:
        print("✗ Memory extraction failed!")
        return False

    # Test with null remember field
    test_response_null = """
    Task completed without new learnings.

    ```json
    {
      "task_completed": true,
      "instructions": "Simple task",
      "results": "Completed",
      "files_modified": [],
      "tools_used": ["Read"],
      "remember": null
    }
    ```
    """

    print("\nTesting with null remember field...")
    success_null = manager.extract_and_update_memory("test_agent", test_response_null)

    if not success_null:
        print("✓ Correctly skipped null remember field")
    else:
        print("✗ Unexpectedly processed null remember field")

    # Test adding more memories
    test_response_2 = """
    Found more patterns.

    ```json
    {
      "task_completed": true,
      "instructions": "Continue analysis",
      "results": "Found more patterns",
      "files_modified": [],
      "tools_used": ["Read"],
      "remember": [
        "Config singleton uses lazy initialization pattern",
        "Hooks system enables extensibility through pre/post delegation"
      ]
    }
    ```
    """

    print("\nTesting adding more memories...")
    success_2 = manager.extract_and_update_memory("test_agent", test_response_2)

    if success_2:
        print("✓ Additional memories added successfully!")

        # Load the memory to verify all memories are present
        memory_content = manager.load_agent_memory("test_agent")
        print("\nUpdated memory content:")
        print("-" * 50)
        print(memory_content)
        print("-" * 50)

        # Check that all memories are present
        expected_memories = [
            "Project uses service-oriented architecture with 5 domains",
            "All services implement explicit interfaces for DI",
            "Memory files stored in .claude/memories/ directory",
            "Config singleton uses lazy initialization pattern",
            "Hooks system enables extensibility through pre/post delegation",
        ]

        all_present = all(mem in memory_content for mem in expected_memories)
        if all_present:
            print("\n✓ All memories successfully stored and retrieved!")
        else:
            print("\n✗ Some memories missing from storage")
            return False
    else:
        print("✗ Failed to add additional memories")
        return False

    return True


if __name__ == "__main__":
    print("Memory Extraction Test")
    print("=" * 60)

    success = test_memory_extraction()

    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
