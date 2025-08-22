#!/usr/bin/env python3
"""Debug remaining memory system issues."""

import json
import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager
from claude_mpm.core.config import Config


def debug_duplicate_issue():
    """Debug why duplicates are still appearing."""
    
    print("Debugging duplicate prevention...")
    print("=" * 40)
    
    config = Config()
    manager = AgentMemoryManager(config, project_root)
    
    test_agent = "debug_duplicate_agent"
    
    duplicate_response = """
Task completed.

```json
{
  "task_completed": true,
  "remember": ["This is a duplicate memory that should only appear once"]
}
```
"""
    
    # Clear any existing memory first
    memory_file = manager.memories_dir / f"{test_agent}_memories.md"
    if memory_file.exists():
        memory_file.unlink()
    
    print("1. Adding memory first time...")
    result1 = manager.extract_and_update_memory(test_agent, duplicate_response)
    print(f"Result 1: {result1}")
    
    memory1 = manager.load_agent_memory(test_agent)
    print("Memory after first addition:")
    print(memory1)
    print("-" * 40)
    
    print("2. Adding same memory second time...")
    result2 = manager.extract_and_update_memory(test_agent, duplicate_response)
    print(f"Result 2: {result2}")
    
    memory2 = manager.load_agent_memory(test_agent)
    print("Memory after second addition:")
    print(memory2)
    print("-" * 40)
    
    # Count occurrences
    count = memory2.count("This is a duplicate memory that should only appear once")
    print(f"Memory appears {count} times")
    
    # Debug the sections parsing
    sections = manager._parse_memory_sections(memory2)
    print("\nParsed sections:")
    for section_name, items in sections.items():
        print(f"  {section_name}: {items}")
    
    # Test the categorization
    learning = "This is a duplicate memory that should only appear once"
    section = manager._categorize_learning(learning)
    print(f"\nLearning categorized to: {section}")


def debug_integration_categorization():
    """Debug why integration memory is not categorized correctly."""
    
    print("\n\nDebugging integration categorization...")
    print("=" * 40)
    
    config = Config()
    manager = AgentMemoryManager(config, project_root)
    
    learning = "Database connections use connection pooling via SQLAlchemy"
    section = manager._categorize_learning(learning)
    print(f"Learning: {learning}")
    print(f"Categorized to: {section}")
    print(f"Expected: Integration Points")
    
    # Check what keywords are present
    learning_lower = learning.lower()
    keywords = ["integration", "interface", "api", "connection", "database", "pooling", "via"]
    present_keywords = [kw for kw in keywords if kw in learning_lower]
    print(f"Present keywords: {present_keywords}")


if __name__ == "__main__":
    debug_duplicate_issue()
    debug_integration_categorization()