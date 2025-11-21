#!/usr/bin/env python3
"""
Test Memory Deduplication with NLP Similarity
=============================================

This test suite verifies that the memory system correctly:
1. Prevents exact duplicates
2. Detects and replaces similar items (>80% similarity)
3. Keeps different items that are below the similarity threshold
4. Maintains recency by replacing old items with new similar ones
"""

from pathlib import Path

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager
from claude_mpm.services.agents.memory.content_manager import MemoryContentManager


def test_exact_duplicate_prevention():
    """Test that exact duplicates are prevented."""
    with tmp_path as tmpdir:
        manager = AgentMemoryManager(working_directory=Path(tmpdir))

        # Add initial item
        success = manager.update_agent_memory(
            "test_agent",
            "Recent Learnings",
            "Always validate user input before processing",
        )
        assert success, "Failed to add initial memory"

        # Try to add exact duplicate
        success = manager.update_agent_memory(
            "test_agent",
            "Recent Learnings",
            "Always validate user input before processing",
        )
        assert success, "Failed to process duplicate"

        # Load memory and check only one instance exists
        memory = manager.load_agent_memory("test_agent")
        occurrences = memory.count("Always validate user input before processing")
        assert occurrences == 1, f"Expected 1 occurrence, found {occurrences}"

        print("✓ Exact duplicate prevention works")


def test_similar_item_replacement():
    """Test that similar items (>80% similarity) replace old ones."""
    with tmp_path as tmpdir:
        manager = AgentMemoryManager(working_directory=Path(tmpdir))

        # First, create a simple memory file to avoid template defaults
        simple_memory = """# test_agent Memory

## Implementation Guidelines
- Initial guideline that will remain

## Recent Learnings
"""
        memory_file = manager.memories_dir / "test_agent_memories.md"
        memory_file.write_text(simple_memory, encoding="utf-8")

        # Add initial item
        success = manager.update_agent_memory(
            "test_agent",
            "Implementation Guidelines",
            "Use async/await for all database operations",
        )
        assert success, "Failed to add initial memory"

        # Add similar item with slight variation
        success = manager.update_agent_memory(
            "test_agent",
            "Implementation Guidelines",
            "Use async/await for all database operations and queries",
        )
        assert success, "Failed to add similar item"

        # Load memory and check only newer version exists
        memory = manager.load_agent_memory("test_agent")

        # Check that the new version replaced the old one
        assert "Use async/await for all database operations and queries" in memory

        # Count how many times the base phrase appears
        base_phrase_count = memory.count("Use async/await for all database operations")
        # Should be 1 (as part of the longer phrase)
        assert base_phrase_count == 1, f"Base phrase appears {base_phrase_count} times"

        # Count async-related items (should be just 1 after deduplication)
        lines = memory.split("\n")
        async_items = 0
        for line in lines:
            if (
                line.strip().startswith("- ")
                and "async/await" in line
                and "database operations" in line
            ):
                async_items += 1

        assert async_items == 1, (
            f"Expected 1 async/await item after deduplication, found {async_items}"
        )

        print("✓ Similar item replacement works")


def test_different_items_preserved():
    """Test that different items below similarity threshold are both kept."""
    with tmp_path as tmpdir:
        manager = AgentMemoryManager(working_directory=Path(tmpdir))

        # Add first item
        success = manager.update_agent_memory(
            "test_agent",
            "Common Mistakes to Avoid",
            "Never use mutable default arguments in Python functions",
        )
        assert success, "Failed to add first item"

        # Add different item (low similarity)
        success = manager.update_agent_memory(
            "test_agent",
            "Common Mistakes to Avoid",
            "Always close database connections properly to avoid leaks",
        )
        assert success, "Failed to add second item"

        # Load memory and check both items exist
        memory = manager.load_agent_memory("test_agent")
        assert "Never use mutable default arguments in Python functions" in memory
        assert "Always close database connections properly to avoid leaks" in memory

        print("✓ Different items are preserved")


def test_substring_similarity_detection():
    """Test that substring matches are detected as similar."""
    with tmp_path as tmpdir:
        manager = AgentMemoryManager(working_directory=Path(tmpdir))

        # Add longer item first
        success = manager.update_agent_memory(
            "test_agent",
            "Project Architecture",
            "The authentication system uses JWT tokens with refresh token rotation for enhanced security",
        )
        assert success, "Failed to add initial item"

        # Add shorter version that's a substring
        success = manager.update_agent_memory(
            "test_agent",
            "Project Architecture",
            "The authentication system uses JWT tokens with refresh token rotation",
        )
        assert success, "Failed to add substring item"

        # Load memory and verify deduplication
        memory = manager.load_agent_memory("test_agent")

        # Count occurrences of the pattern
        lines = memory.split("\n")
        jwt_items = 0
        for line in lines:
            if (
                "JWT tokens with refresh token rotation" in line
                and line.strip().startswith("- ")
            ):
                jwt_items += 1

        assert jwt_items == 1, (
            f"Expected 1 JWT item after deduplication, found {jwt_items}"
        )

        print("✓ Substring similarity detection works")


def test_case_insensitive_matching():
    """Test that similarity matching is case-insensitive."""
    with tmp_path as tmpdir:
        manager = AgentMemoryManager(working_directory=Path(tmpdir))

        # Add item with mixed case
        success = manager.update_agent_memory(
            "test_agent",
            "Performance Considerations",
            "Use Redis for caching frequently accessed data",
        )
        assert success, "Failed to add initial item"

        # Add same item with different case
        success = manager.update_agent_memory(
            "test_agent",
            "Performance Considerations",
            "USE REDIS FOR CACHING FREQUENTLY ACCESSED DATA",
        )
        assert success, "Failed to add uppercase item"

        # Load memory and check only one exists
        memory = manager.load_agent_memory("test_agent")

        # Count Redis-related items
        lines = memory.split("\n")
        redis_items = 0
        for line in lines:
            if (
                "redis" in line.lower()
                and "caching" in line.lower()
                and line.strip().startswith("- ")
            ):
                redis_items += 1

        assert redis_items == 1, (
            f"Expected 1 Redis item after deduplication, found {redis_items}"
        )

        print("✓ Case-insensitive matching works")


def test_similarity_calculation():
    """Test the similarity calculation directly."""
    content_manager = MemoryContentManager(
        {"max_items_per_section": 15, "max_line_length": 120}
    )

    # Test exact match
    sim = content_manager._calculate_similarity("Test string", "Test string")
    assert sim == 1.0, f"Exact match should be 1.0, got {sim}"

    # Test case insensitive match
    sim = content_manager._calculate_similarity("Test String", "test string")
    assert sim == 1.0, f"Case insensitive match should be 1.0, got {sim}"

    # Test high similarity
    sim = content_manager._calculate_similarity(
        "Use async/await for database operations",
        "Use async/await for all database operations",
    )
    assert sim > 0.8, f"High similarity should be > 0.8, got {sim}"

    # Test low similarity
    sim = content_manager._calculate_similarity(
        "Use async/await for database operations",
        "Configure logging with proper error levels",
    )
    assert sim < 0.5, f"Low similarity should be < 0.5, got {sim}"

    # Test substring boost
    sim = content_manager._calculate_similarity(
        "The authentication uses JWT tokens",
        "The authentication uses JWT tokens with refresh rotation for security",
    )
    assert sim >= 0.85, f"Substring match should be >= 0.85, got {sim}"

    print("✓ Similarity calculation works correctly")


def test_deduplicate_section():
    """Test the deduplicate_section method."""
    content_manager = MemoryContentManager(
        {"max_items_per_section": 15, "max_line_length": 120}
    )

    # Create content with duplicates
    content = """# Agent Memory

## Test Section
- Use async/await for database operations
- Always validate input parameters
- Use async/await for all database operations
- ALWAYS VALIDATE INPUT PARAMETERS
- Use proper error handling
- Use async/await for database operations and queries

## Another Section
- Different content here
"""

    # Deduplicate the test section
    deduped_content, removed_count = content_manager.deduplicate_section(
        content, "Test Section"
    )

    # Check that duplicates were removed
    assert removed_count >= 2, (
        f"Should have removed at least 2 duplicates, removed {removed_count}"
    )

    # Check remaining items
    lines = deduped_content.split("\n")
    test_items = []
    in_test = False
    for line in lines:
        if line.startswith("## Test Section"):
            in_test = True
        elif line.startswith("## ") and in_test:
            break
        elif in_test and line.strip().startswith("- "):
            test_items.append(line.strip()[2:])

    # Should have 3 unique items (error handling + 2 async variations kept as most recent)
    assert len(test_items) <= 3, (
        f"Expected at most 3 unique items, found {len(test_items)}"
    )
    assert any("error handling" in item for item in test_items), (
        "Error handling item should remain"
    )

    print("✓ Section deduplication works")


def run_all_tests():
    """Run all deduplication tests."""
    print("\n" + "=" * 60)
    print("Memory Deduplication Test Suite")
    print("=" * 60 + "\n")

    test_functions = [
        test_exact_duplicate_prevention,
        test_similar_item_replacement,
        test_different_items_preserved,
        test_substring_similarity_detection,
        test_case_insensitive_matching,
        test_similarity_calculation,
        test_deduplicate_section,
    ]

    failed = []
    for test_func in test_functions:
        try:
            print(f"Running {test_func.__name__}...")
            test_func()
        except AssertionError as e:
            print(f"✗ {test_func.__name__} failed: {e}")
            failed.append(test_func.__name__)
        except Exception as e:
            print(f"✗ {test_func.__name__} error: {e}")
            failed.append(test_func.__name__)

    print("\n" + "=" * 60)
    if failed:
        print(f"Failed tests: {', '.join(failed)}")
        return False
    print("All tests passed! ✓")
    return True


if __name__ == "__main__":
    import sys

    success = run_all_tests()
    sys.exit(0 if success else 1)
