#!/usr/bin/env python3
"""Test script to verify the new simple list memory system."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config import Config
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def test_memory_system():
    """Test the new simple list memory system."""
    print("Testing new simple list memory system...")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = Path(tmpdir)

        # Initialize memory manager
        config = Config()
        manager = AgentMemoryManager(config, working_dir)

        # Test 1: Create initial memory
        print("\n1. Creating initial memory for test agent...")
        initial_memory = manager.load_agent_memory("test_agent")
        print(f"Initial memory created:\n{initial_memory[:200]}...")

        # Test 2: Add new memories using remember field
        print("\n2. Testing incremental memory addition...")
        new_learnings = [
            "Database connection pool size must be exactly 10 for stability",
            "API rate limit is 100/min (undocumented)",
            "Legacy auth system requires MD5 hash for backwards compatibility",
        ]

        success = manager._add_learnings_to_memory("test_agent", new_learnings)
        if success:
            print("✓ Successfully added new memories")
        else:
            print("✗ Failed to add memories")

        # Test 3: Load and verify memories were added
        print("\n3. Loading updated memory...")
        updated_memory = manager.load_agent_memory("test_agent")
        for learning in new_learnings:
            if learning in updated_memory:
                print(f"✓ Found: {learning[:50]}...")
            else:
                print(f"✗ Missing: {learning[:50]}...")

        # Test 4: Test duplicate detection
        print("\n4. Testing duplicate detection...")
        duplicate_learning = [
            "API rate limit is 100/min (undocumented)"
        ]  # Same as before
        success = manager._add_learnings_to_memory("test_agent", duplicate_learning)

        memory_after_dup = manager.load_agent_memory("test_agent")
        count = memory_after_dup.count("API rate limit is 100/min")
        if count == 1:
            print("✓ Duplicate detection working - item appears only once")
        else:
            print(f"✗ Duplicate detection failed - item appears {count} times")

        # Test 5: Test complete memory replacement with MEMORIES field
        print("\n5. Testing complete memory replacement...")
        complete_memories = [
            "- New memory item 1",
            "- New memory item 2",
            "- New memory item 3",
        ]

        success = manager.replace_agent_memory("test_agent", complete_memories)
        if success:
            print("✓ Successfully replaced memories")

            final_memory = manager.load_agent_memory("test_agent")
            if (
                "New memory item 1" in final_memory
                and "Database connection pool" not in final_memory
            ):
                print("✓ Old memories replaced with new ones")
            else:
                print("✗ Memory replacement didn't work correctly")
        else:
            print("✗ Failed to replace memories")

        # Test 6: Extract memories from JSON response
        print("\n6. Testing memory extraction from JSON response...")
        test_response = """
        Here's my analysis:

        ```json
        {
            "task": "Test task",
            "results": "Test completed",
            "remember": ["Test memory 1", "Test memory 2"],
            "MEMORIES": ["Complete memory 1", "Complete memory 2", "Complete memory 3"]
        }
        ```
        """

        # Test MEMORIES field (complete replacement)
        success = manager.extract_and_update_memory("test_agent", test_response)
        if success:
            print("✓ Successfully extracted and updated memories from response")
            final = manager.load_agent_memory("test_agent")
            if "Complete memory 1" in final:
                print("✓ MEMORIES field correctly replaced all memories")
        else:
            print("✗ Failed to extract memories from response")

        print("\n✅ Memory system tests completed!")

        # Show final memory state
        print("\nFinal memory state:")
        print("-" * 50)
        final_memory = manager.load_agent_memory("test_agent")
        print(final_memory)


if __name__ == "__main__":
    test_memory_system()
