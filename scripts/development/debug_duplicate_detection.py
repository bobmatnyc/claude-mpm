#!/usr/bin/env python3
"""
Debug script to understand why duplicate detection is failing.
"""

import shutil
import sys
import tempfile
from pathlib import Path

# Add the src directory to the path to import claude_mpm modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config import Config
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def debug_duplicate_detection():
    """Debug the duplicate detection mechanism."""

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="memory_debug_")
    working_dir = Path(temp_dir)

    try:
        # Initialize memory manager
        config = Config()
        memory_manager = AgentMemoryManager(config, working_dir)

        agent_id = "debug_agent"
        test_memory = "Always use type hints in Python functions"

        print("=== Debugging Duplicate Detection ===\n")

        # Add same memory 3 times and debug each step
        for i in range(3):
            print(f"--- Attempt {i+1} ---")

            # Load current memory before addition
            current_memory = memory_manager.load_agent_memory(agent_id)
            sections_before = memory_manager._parse_memory_sections(current_memory)

            print("Memory before addition:")
            for section_name, items in sections_before.items():
                print(f"  {section_name}: {len(items)} items")
                for item in items:
                    print(f"    - {item}")

            # Attempt to add memory
            success = memory_manager.add_learning(agent_id, "guideline", test_memory)
            print(f"Add attempt result: {success}")

            # Load memory after addition
            updated_memory = memory_manager.load_agent_memory(agent_id)
            sections_after = memory_manager._parse_memory_sections(updated_memory)

            print("Memory after addition:")
            for section_name, items in sections_after.items():
                print(f"  {section_name}: {len(items)} items")
                for item in items:
                    print(f"    - {item}")

            print(f"Full memory content:\n{updated_memory}\n")
            print("-" * 50)

        # Analyze what happened
        final_memory = memory_manager.load_agent_memory(agent_id)
        occurrences = final_memory.count(test_memory)

        print("Final analysis:")
        print(f"- Test memory: '{test_memory}'")
        print(f"- Total occurrences: {occurrences}")
        print("- Expected: 1")
        print(f"- Duplicate prevention working: {occurrences == 1}")

        # Let's also check the exact logic by manually calling the function
        print("\n=== Testing _add_learnings_to_memory directly ===")

        # Reset memory for direct testing
        memory_manager._save_memory_file(
            agent_id, "# Debug Agent Memory\n\n## Implementation Guidelines\n"
        )

        # Call the function directly multiple times
        for i in range(3):
            result = memory_manager._add_learnings_to_memory(agent_id, [test_memory])
            current = memory_manager.load_agent_memory(agent_id)
            count = current.count(test_memory)
            print(f"Direct call {i+1}: Success={result}, Occurrences={count}")

    finally:
        # Cleanup
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    debug_duplicate_detection()
