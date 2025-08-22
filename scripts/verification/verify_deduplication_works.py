#!/usr/bin/env python3
"""Verify that deduplication actually removes duplicates."""

import tempfile
from pathlib import Path
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def verify_deduplication():
    """Verify deduplication is actually working."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = AgentMemoryManager(working_directory=Path(tmpdir))
        agent_id = "test_agent"
        
        # Create a simple initial memory to avoid template complexity
        initial_memory = """# test_agent Memory

## Test Section

## Recent Learnings
"""
        memory_file = manager.memories_dir / f"{agent_id}_memories.md"
        memory_file.write_text(initial_memory, encoding="utf-8")
        
        print("Step 1: Adding 'Use async/await for database operations'")
        manager.update_agent_memory(
            agent_id,
            "Test Section",
            "Use async/await for database operations"
        )
        
        memory = manager.load_agent_memory(agent_id)
        count1 = memory.count("Use async/await for database operations")
        print(f"  Count of phrase: {count1}")
        
        print("\nStep 2: Adding 'Use async/await for database operations' (exact duplicate)")
        manager.update_agent_memory(
            agent_id,
            "Test Section",
            "Use async/await for database operations"
        )
        
        memory = manager.load_agent_memory(agent_id)
        count2 = memory.count("Use async/await for database operations")
        print(f"  Count of phrase: {count2}")
        print(f"  ✓ Exact duplicate prevented" if count2 == 1 else f"  ✗ Duplicate not prevented")
        
        print("\nStep 3: Adding 'Use async/await for all database operations' (similar)")
        manager.update_agent_memory(
            agent_id,
            "Test Section",
            "Use async/await for all database operations"
        )
        
        memory = manager.load_agent_memory(agent_id)
        has_old = "Use async/await for database operations" in memory
        has_new = "Use async/await for all database operations" in memory
        
        print(f"  Has old version: {has_old}")
        print(f"  Has new version: {has_new}")
        
        # Count total items in Test Section
        lines = memory.split("\n")
        items = []
        in_section = False
        for line in lines:
            if line.startswith("## Test Section"):
                in_section = True
            elif line.startswith("## ") and in_section:
                break
            elif in_section and line.strip().startswith("- "):
                items.append(line.strip()[2:])
        
        print(f"\nFinal items in Test Section ({len(items)} total):")
        for item in items:
            print(f"  - {item}")
        
        print(f"\n✓ Deduplication working correctly!" if len(items) == 1 else f"✗ Expected 1 item, found {len(items)}")


if __name__ == "__main__":
    verify_deduplication()