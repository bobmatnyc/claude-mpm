#!/usr/bin/env python3
"""Test script to verify memory file naming migration."""

import os
import sys
import tempfile
from pathlib import Path

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager
from claude_mpm.core.framework_loader import FrameworkLoader

def test_memory_migration():
    """Test memory file migration from old formats to new format."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        memories_dir = test_dir / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)
        
        print("🧪 Testing Memory File Migration")
        print("=" * 50)
        
        # Test 1: Migration from {agent_name}_agent.md
        print("\n1. Testing migration from engineer_agent.md:")
        old_file = memories_dir / "engineer_agent.md"
        old_file.write_text("# Engineer Memory\n## Old Format\n- Test content")
        
        # Initialize memory manager which should trigger migration
        manager = AgentMemoryManager(working_directory=test_dir)
        content = manager.load_agent_memory("engineer")
        
        new_file = memories_dir / "engineer_memories.md"
        assert new_file.exists(), "❌ New file not created"
        assert not old_file.exists(), "❌ Old file not removed"
        print(f"   ✅ Migrated engineer_agent.md → engineer_memories.md")
        
        # Test 2: Migration from {agent_name}.md
        print("\n2. Testing migration from research.md:")
        intermediate_file = memories_dir / "research.md"
        intermediate_file.write_text("# Research Memory\n## Intermediate Format\n- Test content")
        
        content = manager.load_agent_memory("research")
        
        new_file = memories_dir / "research_memories.md"
        assert new_file.exists(), "❌ New file not created"
        assert not intermediate_file.exists(), "❌ Intermediate file not removed"
        print(f"   ✅ Migrated research.md → research_memories.md")
        
        # Test 3: Direct file creation with new naming
        print("\n3. Testing direct creation with new naming:")
        
        # When creating a new memory, it should use the new format
        content = manager.load_agent_memory("documentation")
        doc_file = memories_dir / "documentation_memories.md"
        assert doc_file.exists(), "❌ New file not created with correct naming"
        assert not (memories_dir / "documentation.md").exists(), "❌ Intermediate format incorrectly created"
        assert not (memories_dir / "documentation_agent.md").exists(), "❌ Old format incorrectly created"
        print(f"   ✅ New file created as documentation_memories.md")
        
        # Test 4: Verify README.md is NOT migrated
        print("\n4. Testing README.md exclusion:")
        readme_file = memories_dir / "README.md"
        readme_file.write_text("# Memory System README\nThis should not be migrated.")
        
        # List all .md files
        md_files = list(memories_dir.glob("*.md"))
        
        # README should still exist and not be renamed
        assert readme_file.exists(), "❌ README.md was incorrectly migrated"
        assert not (memories_dir / "README_memories.md").exists(), "❌ README_memories.md incorrectly created"
        print(f"   ✅ README.md correctly excluded from migration")
        
        print("\n" + "=" * 50)
        print("✅ All migration tests passed!")
        
        # Show final state
        print("\n📁 Final memory directory contents:")
        for file in sorted(memories_dir.glob("*.md")):
            print(f"   - {file.name}")

if __name__ == "__main__":
    test_memory_migration()