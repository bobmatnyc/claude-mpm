#!/usr/bin/env python3
"""Test PM memory persistence and directory handling fixes."""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_pm_memory_persistence():
    """Test that PM memories are saved to user directory and persist."""

    print("\n" + "=" * 60)
    print("TESTING PM MEMORY PERSISTENCE")
    print("=" * 60)

    # Create memory manager
    config = Config()
    manager = AgentMemoryManager(config, project_root)

    # Get user and project memory directories
    user_mem_dir = Path.home() / ".claude-mpm" / "memories"
    project_mem_dir = project_root / ".claude-mpm" / "memories"

    print(f"\nUser memory directory: {user_mem_dir}")
    print(f"Project memory directory: {project_mem_dir}")

    # Test 1: Verify PM memory file location
    print("\n--- Test 1: PM Memory File Location ---")

    # Create PM response with memory
    pm_response = """
Task completed successfully.

```json
{
  "task": "delegation",
  "remember": ["PM always coordinates multi-agent workflows", "PM memories persist across all projects"]
}
```
"""

    # Extract and save PM memory
    success = manager.extract_and_update_memory("PM", pm_response)
    print(f"Memory extraction result: {success}")

    # Check where PM memory was saved
    user_pm_file = user_mem_dir / "PM_memories.md"
    project_pm_file = project_mem_dir / "PM_memories.md"

    print(f"\nPM memory in user dir exists: {user_pm_file.exists()}")
    print(f"PM memory in project dir exists: {project_pm_file.exists()}")

    assert user_pm_file.exists(), "PM memory should be saved to user directory"
    assert (
        not project_pm_file.exists()
        or project_pm_file.stat().st_mtime < user_pm_file.stat().st_mtime
    ), "PM memory in user directory should be the most recent"

    # Read and display PM memory content
    if user_pm_file.exists():
        content = user_pm_file.read_text()
        print(f"\nPM Memory Content (first 500 chars):\n{content[:500]}")

    print("✓ Test 1 passed: PM memory saved to user directory")

    # Test 2: Verify other agents save to project directory
    print("\n--- Test 2: Other Agent Memory Location ---")

    engineer_response = """
Implementation complete.

```json
{
  "status": "success",
  "remember": ["Use dependency injection for all services", "Follow SOLID principles strictly"]
}
```
"""

    # Extract and save engineer memory
    success = manager.extract_and_update_memory("engineer", engineer_response)
    print(f"Engineer memory extraction result: {success}")

    # Check where engineer memory was saved
    user_eng_file = user_mem_dir / "engineer_memories.md"
    project_eng_file = project_mem_dir / "engineer_memories.md"

    print(f"\nEngineer memory in user dir exists: {user_eng_file.exists()}")
    print(f"Engineer memory in project dir exists: {project_eng_file.exists()}")

    assert project_eng_file.exists(), (
        "Engineer memory should be saved to project directory"
    )

    print("✓ Test 2 passed: Other agent memory saved to project directory")

    # Test 3: Verify PM memory migration doesn't delete old files
    print("\n--- Test 3: PM Memory Migration Preservation ---")

    # Create old-format PM memory file
    old_pm_file = user_mem_dir / "PM.md"
    old_content = "# Old PM Memory\n- Important PM knowledge that should not be lost"

    if not old_pm_file.exists():
        old_pm_file.write_text(old_content)
        print(f"Created old format PM file: {old_pm_file}")

    # Force reload to trigger migration
    manager2 = AgentMemoryManager(config, project_root)
    manager2.load_agent_memory("PM")

    # Check if backup was created instead of deletion
    backup_file = user_mem_dir / "PM.md.backup"

    print(f"\nOld PM file exists: {old_pm_file.exists()}")
    print(f"Backup file exists: {backup_file.exists()}")
    print(f"New PM file exists: {user_pm_file.exists()}")

    assert user_pm_file.exists(), "New PM memory file should exist"
    assert old_pm_file.exists() or backup_file.exists(), (
        "Old PM file should be backed up, not deleted"
    )

    print("✓ Test 3 passed: PM memory migration preserves old files")

    # Test 4: Verify PM memory persistence across different project contexts
    print("\n--- Test 4: PM Memory Cross-Project Persistence ---")

    # Simulate different project by using different working directory
    temp_project = Path("/tmp/test_project")
    temp_project.mkdir(exist_ok=True)

    manager3 = AgentMemoryManager(config, temp_project)

    # Load PM memory from different project context
    pm_memory_from_other = manager3.load_agent_memory("PM")

    print(
        f"\nPM memory loaded from different project context: {len(pm_memory_from_other)} chars"
    )
    assert (
        "PM always coordinates multi-agent workflows" in pm_memory_from_other
        or "PM Memory" in pm_memory_from_other
    ), "PM memory should be accessible from any project"

    print("✓ Test 4 passed: PM memory persists across projects")

    # Test 5: Verify duplicate prevention still works
    print("\n--- Test 5: Duplicate Prevention ---")

    # Add same memory again
    initial_content = manager.load_agent_memory("PM")
    initial_count = initial_content.count("PM always coordinates multi-agent workflows")

    success = manager.extract_and_update_memory("PM", pm_response)

    final_content = manager.load_agent_memory("PM")
    final_count = final_content.count("PM always coordinates multi-agent workflows")

    print(f"\nInitial occurrences: {initial_count}")
    print(f"Final occurrences: {final_count}")

    assert final_count == initial_count, "Duplicate memories should not be added"

    print("✓ Test 5 passed: Duplicate prevention works")

    print("\n" + "=" * 60)
    print("ALL PM MEMORY PERSISTENCE TESTS PASSED!")
    print("=" * 60)

    return True


def test_memory_hook_integration():
    """Test that memory hook service properly extracts and saves memories."""

    print("\n" + "=" * 60)
    print("TESTING MEMORY HOOK INTEGRATION")
    print("=" * 60)

    from claude_mpm.hooks.base_hook import HookContext
    from claude_mpm.services.memory_hook_service import MemoryHookService

    # Create memory hook service
    hook_service = MemoryHookService()

    # Test PM memory extraction via hook
    print("\n--- Testing PM Memory via Hook ---")

    # Create context with PM response
    context = HookContext(
        event_type="post_tool",
        data={
            "agent_id": "PM",
            "response": """
            Delegation complete.

            ```json
            {
              "status": "success",
              "remember": ["PM coordinates all agent interactions", "PM uses Task tool for delegation"]
            }
            ```
            """,
        },
    )

    # Call the save memories hook
    result = hook_service._save_new_memories_hook(context)

    print(f"Hook result: success={result.success}, modified={result.modified}")

    # Verify memories were saved
    manager = AgentMemoryManager(Config(), Path.cwd())
    pm_memory = manager.load_agent_memory("PM")

    assert (
        "PM coordinates all agent interactions" in pm_memory
        or "PM uses Task tool for delegation" in pm_memory
    ), "Hook should have saved PM memories"

    print("✓ Memory hook integration test passed")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        # Run all tests
        test_pm_memory_persistence()
        test_memory_hook_integration()

        print("\n✅ All PM memory persistence fixes verified successfully!")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
