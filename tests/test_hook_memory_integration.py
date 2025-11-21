#!/usr/bin/env python3
"""
Hook Memory Integration Test

Test that the hook system correctly processes MEMORIES and remember fields.
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


def test_hook_memory_extraction():
    """Test hook-style memory extraction from agent responses."""
    print("=== Testing Hook Memory Extraction ===")

    # Setup
    temp_dir = Path(tempfile.mkdtemp())
    config = Config()
    memory_manager = AgentMemoryManager(config=config, working_directory=temp_dir)

    agent_id = "hook_test_agent"
    memory_file = temp_dir / ".claude-mpm" / "memories" / f"{agent_id}_memories.md"

    try:
        print("1. Testing MEMORIES field extraction...")

        # Simulate SubagentStop event output with MEMORIES field
        memories_data = [
            "Agent learned about project architecture",
            "Task delegation patterns identified",
            "Memory system integration successful",
        ]

        structured_response = {
            "task_completed": True,
            "MEMORIES": memories_data,
            "results": "Task completed successfully",
            "tools_used": ["Read", "Edit", "Bash"],
        }

        # Create agent response that hooks would process
        agent_response = f"""
Task completed successfully. I've updated the memory system integration.

```json
{json.dumps(structured_response, indent=2)}
```

The memory system is now working correctly with simple list format and timestamp updates.
"""

        # Test extraction (this simulates what the hook would do)
        success = memory_manager.extract_and_update_memory(agent_id, agent_response)
        assert success, "MEMORIES field extraction should succeed"

        # Verify memory file was created/updated
        assert memory_file.exists(), "Memory file should exist"

        content = memory_file.read_text()
        print(f"Memory file content:\n{content}")

        # Verify all MEMORIES items were saved
        for memory in memories_data:
            assert f"- {memory}" in content, f"Memory should be saved: {memory}"

        print("✓ MEMORIES field extraction working")

        print("\n2. Testing remember field extraction...")

        # Add some incremental memories using remember field
        remember_data = [
            "Additional learning from remember field",
            "Hook processing verified",
        ]

        remember_response = {"remember": remember_data, "task_completed": True}

        remember_agent_response = f"""
Additional task completed. Adding some incremental learnings.

```json
{json.dumps(remember_response, indent=2)}
```

These are incremental updates to existing memories.
"""

        # This should replace all existing memories because MEMORIES was used before
        # But let's first add the remember field to existing memories

        # First, let's test remember field on fresh agent
        fresh_agent_id = "fresh_agent"
        fresh_memory_file = (
            temp_dir / ".claude-mpm" / "memories" / f"{fresh_agent_id}_memories.md"
        )

        # Add initial memory
        memory_manager.add_learning(fresh_agent_id, "Initial memory item")

        # Now add remember field
        success = memory_manager.extract_and_update_memory(
            fresh_agent_id, remember_agent_response
        )
        assert success, "remember field extraction should succeed"

        fresh_content = fresh_memory_file.read_text()
        print(f"\nFresh agent memory after remember field:\n{fresh_content}")

        # Should have both initial and remember field items
        assert "- Initial memory item" in fresh_content, (
            "Initial memory should be preserved"
        )
        for memory in remember_data:
            assert f"- {memory}" in fresh_content, (
                f"Remember field memory should be added: {memory}"
            )

        print("✓ remember field extraction working")

        print("\n3. Testing mixed JSON response formats...")

        # Test inline JSON (not in code block)
        mixed_agent_id = "mixed_agent"
        inline_response = f"""
Task completed with some results.

The response includes: {json.dumps({"remember": ["Inline JSON memory"]})}

And some additional text.
"""

        success = memory_manager.extract_and_update_memory(
            mixed_agent_id, inline_response
        )
        assert success, "Inline JSON extraction should succeed"

        mixed_memory_file = (
            temp_dir / ".claude-mpm" / "memories" / f"{mixed_agent_id}_memories.md"
        )
        mixed_content = mixed_memory_file.read_text()

        assert "- Inline JSON memory" in mixed_content, (
            "Inline JSON memory should be extracted"
        )
        print("✓ Mixed JSON format extraction working")

        print("\n4. Testing timestamp updates...")

        # Check that timestamps are updated with each memory operation
        import time

        initial_content = memory_file.read_text()
        initial_timestamp = initial_content.split("<!-- Last Updated: ")[1].split(
            " -->"
        )[0]

        time.sleep(1.1)  # Wait to ensure timestamp difference

        # Add another memory
        memory_manager.add_learning(agent_id, "Timestamp test memory")

        updated_content = memory_file.read_text()
        updated_timestamp = updated_content.split("<!-- Last Updated: ")[1].split(
            " -->"
        )[0]

        assert updated_timestamp != initial_timestamp, "Timestamp should be updated"
        print(f"✓ Timestamp updated from {initial_timestamp} to {updated_timestamp}")

        print("\n🎉 All hook memory extraction tests passed!")
        return True

    finally:
        import shutil

        shutil.rmtree(temp_dir)


def test_response_format_compatibility():
    """Test compatibility with different agent response formats."""
    print("\n=== Testing Response Format Compatibility ===")

    # Setup
    temp_dir = Path(tempfile.mkdtemp())
    config = Config()
    memory_manager = AgentMemoryManager(config=config, working_directory=temp_dir)

    try:
        test_cases = [
            {
                "name": "Standard JSON block",
                "agent_id": "standard_agent",
                "response": """
Task completed.

```json
{
  "MEMORIES": ["Standard JSON block memory"],
  "task_completed": true
}
```

End of response.
""",
                "expected": ["Standard JSON block memory"],
            },
            {
                "name": "Inline JSON",
                "agent_id": "inline_agent",
                "response": """Task completed with result: {"remember": ["Inline memory item"]}""",
                "expected": ["Inline memory item"],
            },
            {
                "name": "Mixed case fields",
                "agent_id": "mixed_case_agent",
                "response": """
```json
{
  "Remember": ["Mixed case remember field"],
  "task_completed": true
}
```
""",
                "expected": ["Mixed case remember field"],
            },
            {
                "name": "Multiple JSON blocks",
                "agent_id": "multiple_agent",
                "response": """
First block:
```json
{"remember": ["First block memory"]}
```

Second block:
```json
{"MEMORIES": ["Second block replaces all"]}
```
""",
                "expected": [
                    "Second block replaces all"
                ],  # MEMORIES should replace remember
            },
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}. Testing {test_case['name']}...")

            agent_id = test_case["agent_id"]
            response = test_case["response"]
            expected = test_case["expected"]

            success = memory_manager.extract_and_update_memory(agent_id, response)
            assert success, f"Should extract from {test_case['name']}"

            memory_file = (
                temp_dir / ".claude-mpm" / "memories" / f"{agent_id}_memories.md"
            )
            content = memory_file.read_text()

            for expected_memory in expected:
                assert f"- {expected_memory}" in content, (
                    f"Should find expected memory: {expected_memory}"
                )

            print(f"✓ {test_case['name']} working")

        print("\n✅ All response format compatibility tests passed!")
        return True

    finally:
        import shutil

        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("HOOK MEMORY INTEGRATION TESTS")
    print("=" * 50)

    tests = [
        ("Hook Memory Extraction", test_hook_memory_extraction),
        ("Response Format Compatibility", test_response_format_compatibility),
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
        print(
            "\n🎉 All hook integration tests passed! Memory extraction working correctly."
        )
    else:
        print(f"\n⚠️ {total - passed} tests failed.")
