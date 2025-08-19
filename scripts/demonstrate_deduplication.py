#!/usr/bin/env python3
"""
Demonstrate NLP-based Memory Deduplication
==========================================

This script shows how the memory system now intelligently deduplicates
similar items to keep memory clean and relevant.
"""

import tempfile
from pathlib import Path
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def demonstrate_deduplication():
    """Demonstrate the deduplication feature with realistic examples."""
    
    print("\n" + "=" * 70)
    print("Claude MPM - NLP-based Memory Deduplication Demo")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = AgentMemoryManager(working_directory=Path(tmpdir))
        agent_id = "engineer"
        
        # Simulate multiple sessions adding similar learnings
        learnings = [
            # Session 1
            ("pattern", "Always use TypeScript for type safety"),
            ("mistake", "Don't forget to handle null values"),
            ("architecture", "The project uses a service-oriented architecture"),
            
            # Session 2 - Similar items (will be deduplicated)
            ("pattern", "Always use TypeScript for type safety in components"),  # Similar to session 1
            ("mistake", "Don't forget to handle null and undefined values"),  # Similar to session 1
            ("performance", "Cache API responses for better performance"),
            
            # Session 3 - More duplicates and variations
            ("architecture", "The project uses service-oriented architecture with DI"),  # Similar
            ("pattern", "ALWAYS USE TYPESCRIPT FOR TYPE SAFETY"),  # Same but uppercase
            ("performance", "Use Redis for caching frequently accessed data"),
            
            # Session 4 - Different items
            ("security", "Validate all user inputs on the backend"),
            ("integration", "Use circuit breaker pattern for external APIs"),
            ("performance", "Cache API responses to improve performance"),  # Similar to session 2
        ]
        
        print("\nAdding learnings from multiple sessions...\n")
        
        for i, (learning_type, content) in enumerate(learnings, 1):
            success = manager.add_learning(agent_id, learning_type, content)
            status = "✓" if success else "✗"
            print(f"{status} Session {(i-1)//3 + 1}: [{learning_type}] {content[:50]}...")
        
        # Load and display the final memory
        print("\n" + "-" * 70)
        print("Final Memory Contents (after deduplication):")
        print("-" * 70)
        
        memory = manager.load_agent_memory(agent_id)
        
        # Parse and display by section
        sections = {}
        current_section = None
        
        for line in memory.split("\n"):
            if line.startswith("## ") and not "Memory Usage" in line:
                current_section = line[3:].strip()
                sections[current_section] = []
            elif line.strip().startswith("- ") and current_section:
                sections[current_section].append(line.strip()[2:])
        
        # Show deduplicated results
        for section, items in sections.items():
            if items:  # Only show sections with items
                print(f"\n## {section}")
                for item in items:
                    print(f"  - {item}")
        
        # Show statistics
        print("\n" + "-" * 70)
        print("Deduplication Statistics:")
        print("-" * 70)
        
        total_added = len(learnings)
        total_kept = sum(len(items) for items in sections.values())
        duplicates_removed = total_added - total_kept
        
        print(f"Items added: {total_added}")
        print(f"Items kept: {total_kept}")
        print(f"Duplicates removed: {duplicates_removed}")
        print(f"Deduplication rate: {duplicates_removed/total_added*100:.1f}%")
        
        # Demonstrate similarity detection
        print("\n" + "-" * 70)
        print("Similarity Examples (showing why items were deduplicated):")
        print("-" * 70)
        
        from claude_mpm.services.agents.memory.content_manager import MemoryContentManager
        content_manager = MemoryContentManager({"max_items_per_section": 15, "max_line_length": 120})
        
        similar_pairs = [
            ("Always use TypeScript for type safety", "Always use TypeScript for type safety in components"),
            ("Don't forget to handle null values", "Don't forget to handle null and undefined values"),
            ("Cache API responses for better performance", "Cache API responses to improve performance"),
        ]
        
        for str1, str2 in similar_pairs:
            similarity = content_manager._calculate_similarity(str1, str2)
            print(f"\nSimilarity: {similarity:.2%}")
            print(f"  Item 1: '{str1}'")
            print(f"  Item 2: '{str2}'")
            print(f"  Action: {'Deduplicated (kept newer)' if similarity > 0.8 else 'Both kept'}")


if __name__ == "__main__":
    demonstrate_deduplication()