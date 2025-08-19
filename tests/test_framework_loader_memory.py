#!/usr/bin/env python3
"""
Test the FrameworkLoader memory loading functionality after the glob pattern fix.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_memory_loading():
    """Test that memory loading works correctly with the new glob pattern."""
    
    print("=" * 60)
    print("Testing FrameworkLoader Memory Loading")
    print("=" * 60)
    
    # Create a temporary test directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test directories
        memories_dir = tmpdir / "memories"
        memories_dir.mkdir(parents=True)
        
        # Create test memory files
        test_files = {
            "PM_memories.md": "# PM Memory\nTest PM memory content",
            "Engineer_memories.md": "# Engineer Memory\nTest engineer memory",
            "Research_memories.md": "# Research Memory\nTest research memory",
            "QA_memories.md": "# QA Memory\nTest QA memory",
            "README.md": "# README\nThis should NOT be loaded as memory",
            "NOTES.md": "# Notes\nThis should also NOT be loaded",
        }
        
        for filename, content in test_files.items():
            (memories_dir / filename).write_text(content)
        
        # Create a mock FrameworkLoader
        loader = FrameworkLoader()
        
        # Test loading memories with different deployed agents
        deployed_agents = ["Engineer", "QA"]
        
        print(f"\nTest directory: {memories_dir}")
        print(f"Deployed agents: {deployed_agents}")
        print()
        
        # Load memories
        memories = loader._load_memories("test", memories_dir, deployed_agents)
        
        print(f"Loaded {len(memories)} memories:")
        for mem in memories:
            path = Path(mem["path"])
            print(f"  - {path.name}")
        
        # Verify results
        print("\n" + "=" * 60)
        print("Verification:")
        print("=" * 60)
        
        # Check that PM memory was loaded
        pm_loaded = any("PM Memory" in m["content"] for m in memories)
        print(f"✓ PM_memories.md loaded: {pm_loaded}")
        assert pm_loaded, "PM_memories.md should always be loaded"
        
        # Check that deployed agent memories were loaded
        engineer_loaded = any("Engineer Memory" in m["content"] for m in memories)
        print(f"✓ Engineer_memories.md loaded (deployed): {engineer_loaded}")
        assert engineer_loaded, "Engineer_memories.md should be loaded (agent is deployed)"
        
        qa_loaded = any("QA Memory" in m["content"] for m in memories)
        print(f"✓ QA_memories.md loaded (deployed): {qa_loaded}")
        assert qa_loaded, "QA_memories.md should be loaded (agent is deployed)"
        
        # Check that non-deployed agent memory was NOT loaded
        research_loaded = any("Research Memory" in m["content"] for m in memories)
        print(f"✓ Research_memories.md NOT loaded (not deployed): {not research_loaded}")
        assert not research_loaded, "Research_memories.md should NOT be loaded (agent not deployed)"
        
        # Check that README.md was NOT loaded
        readme_loaded = any("README" in m["content"] for m in memories)
        print(f"✓ README.md NOT loaded: {not readme_loaded}")
        assert not readme_loaded, "README.md should NOT be loaded"
        
        # Check that NOTES.md was NOT loaded
        notes_loaded = any("Notes" in m["content"] for m in memories)
        print(f"✓ NOTES.md NOT loaded: {not notes_loaded}")
        assert not notes_loaded, "NOTES.md should NOT be loaded"
        
        # Verify count (PM + 2 deployed agents)
        expected_count = 3
        print(f"\n✓ Expected {expected_count} memories, loaded {len(memories)}")
        assert len(memories) == expected_count, f"Expected {expected_count} memories, got {len(memories)}"
        
        print("\n✅ All tests passed! Memory filtering is working correctly.")
        print("=" * 60)
        
        return True


if __name__ == "__main__":
    try:
        success = test_memory_loading()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)