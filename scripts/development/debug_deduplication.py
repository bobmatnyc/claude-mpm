#!/usr/bin/env python3
"""Debug script to check similarity calculation."""

import tempfile
from pathlib import Path

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager
from claude_mpm.services.agents.memory.content_manager import MemoryContentManager

# Test similarity calculation
content_manager = MemoryContentManager(
    {"max_items_per_section": 15, "max_line_length": 120}
)

str1 = "Use async/await for all database operations"
str2 = "Use async/await for all database operations and queries"

similarity = content_manager._calculate_similarity(str1, str2)
print("Similarity between:")
print(f"  '{str1}'")
print(f"  '{str2}'")
print(f"  = {similarity:.3f}")
print(f"  Is duplicate (>0.8)? {similarity > 0.8}")
print()

# Test in actual memory manager
with tempfile.TemporaryDirectory() as tmpdir:
    manager = AgentMemoryManager(working_directory=Path(tmpdir))

    # Add initial item
    manager.update_agent_memory(
        "test_agent",
        "Implementation Guidelines",
        "Use async/await for all database operations",
    )

    print("Initial memory:")
    memory1 = manager.load_agent_memory("test_agent")
    for line in memory1.split("\n"):
        if "async/await" in line:
            print(f"  {line}")

    # Add similar item
    manager.update_agent_memory(
        "test_agent",
        "Implementation Guidelines",
        "Use async/await for all database operations and queries",
    )

    print("\nAfter adding similar item:")
    memory2 = manager.load_agent_memory("test_agent")
    for line in memory2.split("\n"):
        if "async/await" in line:
            print(f"  {line}")

    # Count items
    count = 0
    in_section = False
    for line in memory2.split("\n"):
        if line.startswith("## Implementation Guidelines"):
            in_section = True
        elif line.startswith("## ") and in_section:
            break
        elif in_section and line.strip().startswith("- "):
            count += 1
            print(f"Item {count}: {line.strip()}")
