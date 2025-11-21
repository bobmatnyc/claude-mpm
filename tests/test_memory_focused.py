#!/usr/bin/env python3
"""
Focused Memory System Tests

Quick tests to verify core memory functionality is working correctly.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.core.config import Config
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def test_basic_memory_operations():
    """Test basic memory operations."""
    print("=== Testing Basic Memory Operations ===")

    # Setup
    temp_dir = Path(tempfile.mkdtemp())
    config = Config()
    memory_manager = AgentMemoryManager(config=config, working_directory=temp_dir)

    agent_id = "test_agent"
    memories_dir = temp_dir / ".claude-mpm" / "memories"
    memory_file = memories_dir / f"{agent_id}_memories.md"

    try:
        # Test 1: Create initial memory
        print("1. Creating initial memory...")
        memory_manager.load_agent_memory(agent_id)
        assert memory_file.exists(), "Memory file should be created"
        print(f"✓ Memory file created: {memory_file}")

        # Test 2: Add incremental memory
        print("2. Adding incremental memory...")
        success = memory_manager.add_learning(agent_id, "Test memory item")
        assert success, "Adding learning should succeed"

        content = memory_file.read_text()
        assert "- Test memory item" in content, "Memory item should be added"
        print("✓ Incremental memory added")

        # Test 3: Test remember field processing
        print("3. Testing remember field processing...")
        remember_response = json.dumps(
            {
                "remember": ["Remember field item 1", "Remember field item 2"],
                "task_completed": True,
            }
        )

        success = memory_manager.extract_and_update_memory(
            agent_id, f"Response\n```json\n{remember_response}\n```"
        )
        assert success, "Remember field processing should succeed"

        content = memory_file.read_text()
        assert "- Remember field item 1" in content, (
            "Remember field item 1 should be added"
        )
        assert "- Remember field item 2" in content, (
            "Remember field item 2 should be added"
        )
        print("✓ Remember field processing works")

        # Test 4: Test MEMORIES field complete replacement
        print("4. Testing MEMORIES field complete replacement...")
        memories_response = json.dumps(
            {
                "MEMORIES": ["New memory 1", "New memory 2", "New memory 3"],
                "task_completed": True,
            }
        )

        success = memory_manager.extract_and_update_memory(
            agent_id, f"Response\n```json\n{memories_response}\n```"
        )
        assert success, "MEMORIES field processing should succeed"

        content = memory_file.read_text()
        # Old memories should be replaced
        assert "Test memory item" not in content, "Old memory should be replaced"
        assert "Remember field item 1" not in content, "Old memory should be replaced"

        # New memories should be present
        assert "- New memory 1" in content, "New memory 1 should be present"
        assert "- New memory 2" in content, "New memory 2 should be present"
        assert "- New memory 3" in content, "New memory 3 should be present"
        print("✓ MEMORIES field complete replacement works")

        # Test 5: Check timestamp format
        print("5. Checking timestamp format...")
        lines = content.split("\n")
        assert lines[0].startswith("# Agent Memory:"), "Should have proper header"
        assert lines[1].startswith("<!-- Last Updated:"), "Should have timestamp"
        assert "Z -->" in lines[1], "Timestamp should end with Z"
        print("✓ Timestamp format correct")

        print("\n🎉 All basic memory operations working correctly!")
        return True

    finally:
        import shutil

        shutil.rmtree(temp_dir)


def test_multiple_agents():
    """Test multiple agents using project-based storage."""
    print("\n=== Testing Multiple Agents ===")

    # Setup
    temp_dir = Path(tempfile.mkdtemp())
    config = Config()
    memory_manager = AgentMemoryManager(config=config, working_directory=temp_dir)

    memories_dir = temp_dir / ".claude-mpm" / "memories"

    try:
        agents = ["PM", "engineer", "research", "qa"]

        for agent_id in agents:
            print(f"Testing {agent_id} agent...")

            # Add memory for each agent
            success = memory_manager.add_learning(
                agent_id, f"Memory for {agent_id} agent"
            )
            assert success, f"Should add memory for {agent_id}"

            # Check file exists
            memory_file = memories_dir / f"{agent_id}_memories.md"
            assert memory_file.exists(), f"Memory file should exist for {agent_id}"

            # Check content
            content = memory_file.read_text()
            assert f"- Memory for {agent_id} agent" in content, (
                f"Memory should be saved for {agent_id}"
            )

            print(f"✓ {agent_id} agent memory working")

        # Check directory structure
        memory_files = list(memories_dir.glob("*_memories.md"))
        print(f"Memory files found: {[f.name for f in memory_files]}")
        assert len(memory_files) == len(agents), (
            f"Should have {len(agents)} memory files"
        )

        # Check README exists
        readme_file = memories_dir / "README.md"
        assert readme_file.exists(), "README.md should exist"

        print(f"\n✓ All {len(agents)} agents working with project-based storage!")
        return True

    finally:
        import shutil

        shutil.rmtree(temp_dir)


def test_deduplication():
    """Test memory deduplication."""
    print("\n=== Testing Deduplication ===")

    # Setup
    temp_dir = Path(tempfile.mkdtemp())
    config = Config()
    memory_manager = AgentMemoryManager(config=config, working_directory=temp_dir)

    agent_id = "dedup_test"
    memory_file = temp_dir / ".claude-mpm" / "memories" / f"{agent_id}_memories.md"

    try:
        # Add similar memories
        similar_items = [
            "This is a test memory",
            "This is a test memory",  # Exact duplicate
            "This is a TEST memory",  # Case difference
            "This is a completely different memory",
        ]

        # Add all items
        for item in similar_items:
            memory_manager.add_learning(agent_id, item)

        content = memory_file.read_text()
        print(f"Content before deduplication:\n{content}")

        # Should have deduplicated automatically during add_learning
        lines = [line for line in content.split("\n") if line.strip().startswith("- ")]
        print(f"Memory items found: {len(lines)}")

        # Should have fewer items due to deduplication
        assert len(lines) < len(similar_items), "Should have deduplicated some items"

        # Unique content should be preserved
        assert "completely different" in content.lower(), (
            "Unique content should be preserved"
        )

        print("✓ Deduplication working correctly")
        return True

    finally:
        import shutil

        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("FOCUSED MEMORY SYSTEM TESTS")
    print("=" * 50)

    tests = [
        ("Basic Memory Operations", test_basic_memory_operations),
        ("Multiple Agents", test_multiple_agents),
        ("Deduplication", test_deduplication),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "PASSED" if result else "FAILED"
            print(f"\n✅ {test_name}: PASSED")
        except Exception as e:
            results[test_name] = f"FAILED: {e}"
            print(f"\n❌ {test_name}: FAILED - {e}")

    print("\n" + "=" * 50)
    print("SUMMARY:")
    passed = sum(1 for r in results.values() if r == "PASSED")
    total = len(results)

    for test_name, result in results.items():
        symbol = "✅" if result == "PASSED" else "❌"
        print(f"{symbol} {test_name}: {result}")

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All focused tests passed! Core memory system working correctly.")
    else:
        print(f"\n⚠️ {total - passed} tests failed.")
