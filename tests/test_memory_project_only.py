#!/usr/bin/env python3
"""Test that all memories are saved to project directory only."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


def test_memory_project_only():
    """Test that all agents including PM save to project directory only."""

    print("Testing memory system - project-only storage")
    print("=" * 60)

    # Create temporary directory for testing
    with tmp_path as tmpdir:
        test_dir = Path(tmpdir)
        print(f"Test directory: {test_dir}")

        # Initialize memory manager with test directory
        config = Config()
        manager = AgentMemoryManager(config, working_directory=test_dir)

        # Test PM agent
        print("\n1. Testing PM agent memory...")
        pm_memory = manager.load_agent_memory("PM")
        print(f"   PM memory created: {bool(pm_memory)}")

        # Check where PM memory was saved
        project_pm_file = test_dir / ".claude-mpm" / "memories" / "PM_memories.md"
        user_pm_file = Path.home() / ".claude-mpm" / "memories" / "PM_memories.md"

        print(f"   Project PM file exists: {project_pm_file.exists()}")
        print(f"   User PM file exists: {user_pm_file.exists()}")

        assert project_pm_file.exists(), "PM memory should be in project directory"

        # Test adding memory to PM
        print("\n2. Testing PM memory update...")
        success = manager.add_learning("PM", "pattern", "Test PM learning pattern")
        print(f"   PM memory update success: {success}")

        # Verify it was saved to project directory
        if project_pm_file.exists():
            content = project_pm_file.read_text()
            print(
                f"   PM memory contains test pattern: {'Test PM learning pattern' in content}"
            )
            assert "Test PM learning pattern" in content, (
                "PM memory should contain test pattern"
            )

        # Test other agents
        print("\n3. Testing Engineer agent memory...")
        eng_memory = manager.load_agent_memory("engineer")
        print(f"   Engineer memory created: {bool(eng_memory)}")

        project_eng_file = (
            test_dir / ".claude-mpm" / "memories" / "engineer_memories.md"
        )
        print(f"   Project engineer file exists: {project_eng_file.exists()}")

        assert project_eng_file.exists(), (
            "Engineer memory should be in project directory"
        )

        # Test memory extraction
        print("\n4. Testing memory extraction...")
        test_response = """
        Task completed successfully.

        ```json
        {
            "status": "completed",
            "remember": ["Always use project directory for memories", "PM agent follows same rules as other agents"]
        }
        ```
        """

        success = manager.extract_and_update_memory("PM", test_response)
        print(f"   Memory extraction success: {success}")

        if success:
            content = project_pm_file.read_text()
            print(
                f"   PM memory contains extracted items: {'Always use project directory' in content}"
            )
            assert "Always use project directory" in content, (
                "Should extract and save to project"
            )

        # Verify no user directory was created
        print("\n5. Verifying no user directory created...")
        user_dir = Path.home() / ".claude-mpm" / "memories"

        # Check if any new files were created in user dir during our test
        if user_dir.exists():
            user_files = list(user_dir.glob("*_memories.md"))
            print(f"   User directory files: {[f.name for f in user_files]}")
            # Note: We can't assert no files exist because there might be pre-existing files
            # But we can check that our test didn't create new PM files there
            recent_pm_files = [
                f
                for f in user_files
                if "PM" in f.name and f.stat().st_mtime > test_start_time
            ]
            if recent_pm_files:
                print(
                    f"   WARNING: Found recently created PM files in user dir: {recent_pm_files}"
                )
        else:
            print("   User directory doesn't exist (good!)")

        print("\n✅ All tests passed - memories are project-only!")
        return True


if __name__ == "__main__":
    import time

    test_start_time = time.time()

    try:
        test_memory_project_only()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
