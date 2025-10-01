"""End-to-end test for memory integration hooks.

WHY: Ensure the memory hooks work together properly in a realistic scenario.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from claude_mpm.hooks.base_hook import HookContext, HookType
from claude_mpm.hooks.memory_integration_hook import (
    MemoryPostDelegationHook,
    MemoryPreDelegationHook,
)
from claude_mpm.services.agents.memory import AgentMemoryManager


def test_memory_hooks_integration():
    """Test that memory hooks work together in a full workflow."""
    with tmp_path as tmpdir:
        # Setup config with temp directory
        config = Config(config={"memory": {"enabled": True, "auto_learning": True}})

        # Create memories directory
        memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)

        # Patch get_path_manager() to use temp directory
        with patch(
            "claude_mpm.utils.paths.get_path_manager().get_project_root",
            return_value=Path(tmpdir),
        ):
            # Initialize memory manager
            memory_manager = AgentMemoryManager(config)

            # Create initial memory for engineer agent
            # We'll add some initial learnings to create the memory file
            memory_manager.add_learning(
                "engineer", "architecture", "Uses microservices pattern"
            )
            memory_manager.add_learning(
                "engineer", "architecture", "REST API with JWT auth"
            )
            memory_manager.add_learning(
                "engineer", "mistake", "Don't forget input validation"
            )

            # Create hooks
            pre_hook = MemoryPreDelegationHook(config)
            post_hook = MemoryPostDelegationHook(config)

            # Simulate pre-delegation
            pre_context = HookContext(
                hook_type=HookType.PRE_DELEGATION,
                data={
                    "agent": "Engineer Agent",
                    "context": {"prompt": "Build authentication endpoint"},
                },
                metadata={},
                timestamp=datetime.now(timezone.utc),
            )

            pre_result = pre_hook.execute(pre_context)

            # Verify memory was injected
            assert pre_result.success
            assert pre_result.modified
            assert "agent_memory" in pre_result.data["context"]
            assert "microservices pattern" in pre_result.data["context"]["agent_memory"]

            # Simulate agent execution with learnings
            post_context = HookContext(
                hook_type=HookType.POST_DELEGATION,
                data={
                    "agent": "Engineer Agent",
                    "result": {
                        "content": """
I've created the authentication endpoint with JWT.

# Add To Memory:
Type: pattern
Content: Use bcrypt for password hashing with cost factor 12
#

# Add To Memory:
Type: guideline
Content: Always rate limit authentication endpoints
#

# Add To Memory:
Type: mistake
Content: Initially forgot to validate email format
#

The implementation follows our REST API standards.
"""
                    },
                },
                metadata={},
                timestamp=datetime.now(timezone.utc),
            )

            post_result = post_hook.execute(post_context)

            # Verify learnings were extracted
            assert post_result.success
            assert post_result.metadata["learnings_extracted"] == 3

            # Load updated memory
            updated_memory = memory_manager.load_agent_memory("engineer")

            # Verify new learnings are in memory
            assert (
                "Use bcrypt for password hashing with cost factor 12" in updated_memory
            )
            assert "Always rate limit authentication endpoints" in updated_memory
            assert "Initially forgot to validate email format" in updated_memory

            # Verify they're in the right sections
            assert "## Implementation Guidelines" in updated_memory
            assert "## Common Mistakes to Avoid" in updated_memory

            # Simulate another pre-delegation to verify updated memory
            pre_context2 = HookContext(
                hook_type=HookType.PRE_DELEGATION,
                data={
                    "agent": "Engineer",
                    "context": {"prompt": "Build password reset"},
                },
                metadata={},
                timestamp=datetime.now(timezone.utc),
            )

            pre_result2 = pre_hook.execute(pre_context2)

            # Verify updated memory is injected
            assert pre_result2.success
            assert (
                "bcrypt for password hashing"
                in pre_result2.data["context"]["agent_memory"]
            )
            assert (
                "rate limit authentication endpoints"
                in pre_result2.data["context"]["agent_memory"]
            )


def test_memory_hooks_with_disabled_learning():
    """Test that hooks respect disabled auto-learning."""
    with tmp_path as tmpdir:
        # Setup config with auto-learning disabled
        config = Config(config={"memory": {"enabled": True, "auto_learning": False}})

        memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)

        with patch(
            "claude_mpm.utils.paths.get_path_manager().get_project_root",
            return_value=Path(tmpdir),
        ):
            memory_manager = AgentMemoryManager(config)

            # Create initial memory
            memory_manager.add_learning("qa", "architecture", "Basic structure")

            # Create hooks
            pre_hook = MemoryPreDelegationHook(config)
            post_hook = MemoryPostDelegationHook(config)

            # Pre-delegation should still work
            pre_context = HookContext(
                hook_type=HookType.PRE_DELEGATION,
                data={"agent": "QA", "context": {}},
                metadata={},
                timestamp=datetime.now(timezone.utc),
            )

            pre_result = pre_hook.execute(pre_context)
            assert pre_result.success
            assert pre_result.modified

            # Post-delegation should not extract learnings
            post_context = HookContext(
                hook_type=HookType.POST_DELEGATION,
                data={
                    "agent": "QA",
                    "result": {"content": "Discovered pattern: Important finding"},
                },
                metadata={},
                timestamp=datetime.now(timezone.utc),
            )

            post_result = post_hook.execute(post_context)
            assert post_result.success
            assert not post_result.modified  # No learnings extracted

            # Verify memory unchanged (should still contain basic structure)
            final_memory = memory_manager.load_agent_memory("qa")
            assert "Basic structure" in final_memory
            # Should not contain the pattern that wasn't extracted
            assert "Important finding" not in final_memory
