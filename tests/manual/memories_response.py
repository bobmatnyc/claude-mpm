#!/usr/bin/env python3
"""Test script to verify MEMORIES field processing in agent responses.

This script tests that:
1. Agents can return a MEMORIES field in their structured response
2. The hook system properly extracts the MEMORIES field
3. The memory manager correctly replaces all memories with the MEMORIES content
4. The memory file is updated with the new memories
"""

import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config import Config
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def test_memories_field_extraction():
    """Test that the memory manager properly handles MEMORIES field."""

    print("Testing MEMORIES field extraction and processing...")

    # Create a temporary directory for test memories
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = Path(tmpdir)
        memories_dir = working_dir / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)

        # Create a test config
        config = Config({"memory": {"enabled": True, "auto_learning": True}})

        # Initialize memory manager
        memory_manager = AgentMemoryManager(config, working_directory=working_dir)

        # Create initial memory for test agent
        test_agent_id = "engineer"
        initial_memories = [
            "- Initial memory item 1",
            "- Initial memory item 2",
            "- Initial memory item 3",
        ]

        # Add initial memories
        for memory in initial_memories:
            memory_manager.add_learning(test_agent_id, memory.lstrip("- "))

        print(f"✓ Created initial memories for {test_agent_id}")

        # Simulate an agent response with MEMORIES field
        agent_response = """
        The task has been completed successfully.

        ```json
        {
            "task": "Update memory system",
            "task_completed": true,
            "results": "Successfully implemented MEMORIES field processing",
            "files_modified": [],
            "tools_used": ["Edit", "Write"],
            "remember": null,
            "MEMORIES": [
                "Complete replacement memory 1",
                "Complete replacement memory 2",
                "Complete replacement memory 3",
                "Complete replacement memory 4",
                "Complete replacement memory 5"
            ]
        }
        ```

        All done!
        """

        # Test memory extraction and update
        print("\nTesting extract_and_update_memory with MEMORIES field...")
        success = memory_manager.extract_and_update_memory(
            test_agent_id, agent_response
        )

        if success:
            print("✓ Successfully processed MEMORIES field")
        else:
            print("✗ Failed to process MEMORIES field")
            return False

        # Load the updated memory and verify
        updated_memory = memory_manager.load_agent_memory(test_agent_id)

        # Parse the memory content to extract items
        memory_lines = updated_memory.split("\n")
        memory_items = []
        for line in memory_lines:
            line = line.strip()
            if line.startswith("- "):
                memory_items.append(line[2:])  # Remove "- " prefix

        print("\nMemory items after MEMORIES update:")
        for item in memory_items:
            print(f"  - {item}")

        # Verify that memories were completely replaced
        expected_memories = [
            "Complete replacement memory 1",
            "Complete replacement memory 2",
            "Complete replacement memory 3",
            "Complete replacement memory 4",
            "Complete replacement memory 5",
        ]

        if set(memory_items) == set(expected_memories):
            print("\n✓ MEMORIES field correctly replaced all memories!")
            print("  Old memories were removed")
            print("  New memories were added")
        else:
            print("\n✗ Memory replacement did not work as expected")
            print(f"  Expected: {expected_memories}")
            print(f"  Got: {memory_items}")
            return False

        # Test with incremental update (remember field)
        print("\n\nTesting incremental update with 'remember' field...")
        incremental_response = """
        Another task completed.

        ```json
        {
            "task": "Add incremental memory",
            "task_completed": true,
            "results": "Added new learning",
            "remember": ["Additional incremental memory item"]
        }
        ```
        """

        success = memory_manager.extract_and_update_memory(
            test_agent_id, incremental_response
        )

        if success:
            print("✓ Successfully processed 'remember' field")
        else:
            print("✗ Failed to process 'remember' field")

        # Check that incremental update worked
        updated_memory = memory_manager.load_agent_memory(test_agent_id)
        memory_lines = updated_memory.split("\n")
        memory_items = []
        for line in memory_lines:
            line = line.strip()
            if line.startswith("- "):
                memory_items.append(line[2:])

        if "Additional incremental memory item" in memory_items:
            print("✓ Incremental memory update worked correctly")
            print(f"  Total memories after incremental update: {len(memory_items)}")
        else:
            print("✗ Incremental memory update failed")

        print("\n" + "=" * 60)
        print("MEMORIES field processing test completed successfully!")
        print("=" * 60)
        return True


def test_empty_memories_handling():
    """Test that empty MEMORIES field is handled correctly."""

    print("\n\nTesting empty MEMORIES field handling...")

    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = Path(tmpdir)
        memories_dir = working_dir / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)

        config = Config({"memory": {"enabled": True, "auto_learning": True}})

        memory_manager = AgentMemoryManager(config, working_directory=working_dir)

        # Test with empty MEMORIES list
        empty_response = """
        ```json
        {
            "task": "Clear memories",
            "MEMORIES": []
        }
        ```
        """

        test_agent_id = "qa"
        success = memory_manager.extract_and_update_memory(
            test_agent_id, empty_response
        )

        if not success:
            print("✓ Empty MEMORIES list correctly ignored")
        else:
            print("✗ Empty MEMORIES list was incorrectly processed")

        # Test with null MEMORIES
        null_response = """
        ```json
        {
            "task": "Task with no memories",
            "MEMORIES": null
        }
        ```
        """

        success = memory_manager.extract_and_update_memory(test_agent_id, null_response)

        if not success:
            print("✓ Null MEMORIES correctly ignored")
        else:
            print("✗ Null MEMORIES was incorrectly processed")

    print("\nEmpty MEMORIES handling test completed!")
    return True


if __name__ == "__main__":
    try:
        # Run the tests
        success1 = test_memories_field_extraction()
        success2 = test_empty_memories_handling()

        if success1 and success2:
            print("\n✅ All MEMORIES field tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
