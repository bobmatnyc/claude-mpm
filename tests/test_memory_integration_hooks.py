"""Test memory integration hooks.

WHY: Ensure memory hooks properly inject memory before delegation and
extract learnings after delegation.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from claude_mpm.hooks.base_hook import HookContext, HookType
from claude_mpm.hooks.memory_integration_hook import (
    MemoryPostDelegationHook,
    MemoryPreDelegationHook,
)


class TestMemoryPreDelegationHook:
    """Test memory injection before delegation."""

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_injects_memory_into_context(self):
        """Test that agent memory is properly injected into context."""
        # Setup
        mock_manager = Mock()
        mock_manager.load_agent_memory.return_value = """
## Project Architecture
- Uses microservices pattern
- REST API with JWT auth

## Common Mistakes to Avoid
- Don't forget input validation
"""
        self.return_value = mock_manager

        hook = MemoryPreDelegationHook()
        context = HookContext(
            hook_type=HookType.PRE_DELEGATION,
            data={
                "agent": "Engineer Agent",
                "context": {"prompt": "Build a new feature"},
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Execute
        result = hook.execute(context)

        # Verify
        assert result.success
        assert result.modified
        assert "agent_memory" in result.data["context"]
        assert "Project Architecture" in result.data["context"]["agent_memory"]
        assert "microservices pattern" in result.data["context"]["agent_memory"]
        mock_manager.load_agent_memory.assert_called_once_with("engineer")

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_handles_string_context(self):
        """Test that hook handles string context properly."""
        # Setup
        mock_manager = Mock()
        mock_manager.load_agent_memory.return_value = "Test memory"
        self.return_value = mock_manager

        hook = MemoryPreDelegationHook()
        context = HookContext(
            hook_type=HookType.PRE_DELEGATION,
            data={"agent": "QA", "context": "Run the tests"},  # String context
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Execute
        result = hook.execute(context)

        # Verify
        assert result.success
        assert result.modified
        assert isinstance(result.data["context"], dict)
        assert result.data["context"]["prompt"] == "Run the tests"
        assert "agent_memory" in result.data["context"]

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_normalizes_agent_names(self):
        """Test various agent name formats are normalized correctly."""
        # Setup
        mock_manager = Mock()
        mock_manager.load_agent_memory.return_value = "Memory"
        self.return_value = mock_manager

        hook = MemoryPreDelegationHook()

        test_cases = [
            ("Engineer Agent", "engineer"),
            ("engineer_agent", "engineer"),
            ("Engineer", "engineer"),
            ("QA Agent", "qa"),
            ("Research_Agent", "research"),
        ]

        for agent_name, expected_id in test_cases:
            context = HookContext(
                hook_type=HookType.PRE_DELEGATION,
                data={"agent": agent_name, "context": {}},
                metadata={},
                timestamp=datetime.now(timezone.utc),
            )

            hook.execute(context)

            # Verify the correct agent_id was used
            mock_manager.load_agent_memory.assert_called_with(expected_id)
            mock_manager.reset_mock()

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_handles_no_agent(self):
        """Test hook handles missing agent gracefully."""
        hook = MemoryPreDelegationHook()
        context = HookContext(
            hook_type=HookType.PRE_DELEGATION,
            data={"context": {}},  # No agent
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        result = hook.execute(context)

        assert result.success
        assert not result.modified

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_handles_memory_load_failure(self):
        """Test hook handles memory loading errors gracefully."""
        # Setup
        mock_manager = Mock()
        mock_manager.load_agent_memory.side_effect = Exception("File not found")
        self.return_value = mock_manager

        hook = MemoryPreDelegationHook()
        context = HookContext(
            hook_type=HookType.PRE_DELEGATION,
            data={"agent": "Engineer", "context": {}},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Execute
        result = hook.execute(context)

        # Verify - should not fail delegation
        assert result.success
        assert not result.modified
        assert "Memory injection failed" in result.error


class TestMemoryPostDelegationHook:
    """Test learning extraction after delegation."""

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_extracts_patterns(self):
        """Test pattern extraction from results."""
        # Setup
        mock_manager = Mock()
        self.return_value = mock_manager

        config = Config(config={"memory": {"auto_learning": True}})

        hook = MemoryPostDelegationHook(config)
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "agent": "Engineer",
                "result": {
                    "content": """
                    I've implemented the feature successfully.

                    # Add To Memory:
                    Type: pattern
                    Content: Always validate user input at the API boundary
                    #

                    Also learned something important:

                    # Add To Memory:
                    Type: pattern
                    Content: Use dependency injection for better testing
                    #

                    The code follows the existing patterns in the codebase.
                    """
                },
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Execute
        result = hook.execute(context)

        # Verify
        assert result.success
        # Should extract 2 pattern learnings
        assert result.metadata["learnings_extracted"] == 2

        # Check that learnings were stored
        calls = mock_manager.add_learning.call_args_list

        # We expect exactly 2 learnings
        assert len(calls) == 2

        # Check that expected learnings are present
        learnings = [(call[0][1], call[0][2]) for call in calls]
        assert (
            "pattern",
            "Always validate user input at the API boundary",
        ) in learnings
        assert ("pattern", "Use dependency injection for better testing") in learnings

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_extracts_mistakes(self):
        """Test mistake extraction from results."""
        # Setup
        mock_manager = Mock()
        self.return_value = mock_manager

        config = Config(config={"memory": {"auto_learning": True}})

        hook = MemoryPostDelegationHook(config)
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "agent": "QA",
                "result": {
                    "content": """
                    Tests completed with some issues found.

                    # Add To Memory:
                    Type: mistake
                    Content: Forgot to mock the database connection
                    #

                    We should not run integration tests against production database:

                    # Add To Memory:
                    Type: mistake
                    Content: Never run integration tests against production database
                    #

                    Also important:

                    # Add To Memory:
                    Type: mistake
                    Content: Avoid hardcoded test data
                    #
                    """
                },
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Execute
        result = hook.execute(context)

        # Verify
        assert result.success

        # Check learnings
        calls = mock_manager.add_learning.call_args_list
        learnings = [(call[0][1], call[0][2]) for call in calls]

        assert len(calls) == 3
        assert ("mistake", "Forgot to mock the database connection") in learnings
        assert (
            "mistake",
            "Never run integration tests against production database",
        ) in learnings
        assert ("mistake", "Avoid hardcoded test data") in learnings

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_extracts_guidelines(self):
        """Test guideline extraction from results."""
        # Setup
        mock_manager = Mock()
        self.return_value = mock_manager

        config = Config(config={"memory": {"auto_learning": True}})

        hook = MemoryPostDelegationHook(config)
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "agent": "Engineer",
                "result": {
                    "content": """
                    Implementation complete.

                    # Add To Memory:
                    Type: guideline
                    Content: Use async/await for all I/O operations
                    #

                    # Add To Memory:
                    Type: guideline
                    Content: Keep functions under 50 lines
                    #

                    # Add To Memory:
                    Type: guideline
                    Content: Always use type hints in Python code
                    #
                    """
                },
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Execute
        hook.execute(context)

        # Verify guidelines were extracted
        calls = mock_manager.add_learning.call_args_list
        learnings = [(call[0][1], call[0][2]) for call in calls]

        assert len(calls) == 3
        assert ("guideline", "Use async/await for all I/O operations") in learnings
        assert ("guideline", "Keep functions under 50 lines") in learnings
        assert ("guideline", "Always use type hints in Python code") in learnings

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_respects_auto_learning_config(self):
        """Test that hook respects auto_learning configuration."""
        # Setup
        mock_manager = Mock()
        self.return_value = mock_manager

        # Auto-learning disabled
        config = Config(config={"memory": {"auto_learning": False}})

        hook = MemoryPostDelegationHook(config)
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "agent": "Engineer",
                "result": {"content": "Discovered pattern: Important finding"},
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Execute
        result = hook.execute(context)

        # Verify no learnings extracted
        assert result.success
        assert not result.modified
        mock_manager.add_learning.assert_not_called()

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_respects_agent_specific_config(self):
        """Test that hook respects agent-specific auto_learning overrides."""
        # Setup
        mock_manager = Mock()
        self.return_value = mock_manager

        # Global enabled but agent-specific disabled
        config = Config(
            config={
                "memory": {
                    "auto_learning": True,
                    "agent_overrides": {"engineer": {"auto_learning": False}},
                }
            }
        )

        hook = MemoryPostDelegationHook(config)
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "agent": "Engineer",
                "result": {"content": "Best practice: Important guideline"},
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Execute
        result = hook.execute(context)

        # Verify no learnings extracted for this agent
        assert result.success
        assert not result.modified
        mock_manager.add_learning.assert_not_called()

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_length_limit(self):
        """Test that learnings over 100 characters are skipped."""
        # Setup
        mock_manager = Mock()
        self.return_value = mock_manager

        config = Config(config={"memory": {"auto_learning": True}})

        hook = MemoryPostDelegationHook(config)
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "agent": "Engineer",
                "result": {
                    "content": f"""
                    # Add To Memory:
                    Type: pattern
                    Content: Short learning
                    #

                    # Add To Memory:
                    Type: pattern
                    Content: {"x" * 150}
                    #
                    """
                },
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Execute
        hook.execute(context)

        # Verify only short learning was stored
        assert mock_manager.add_learning.call_count == 1
        assert mock_manager.add_learning.call_args[0][2] == "Short learning"

    @patch("claude_mpm.hooks.memory_integration_hook.AgentMemoryManager")
    def test_handles_extraction_errors(self):
        """Test hook handles extraction errors gracefully."""
        # Setup
        mock_manager = Mock()
        mock_manager.add_learning.side_effect = Exception("Storage error")
        self.return_value = mock_manager

        config = Config(config={"memory": {"auto_learning": True}})

        hook = MemoryPostDelegationHook(config)
        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "agent": "Engineer",
                "result": {"content": "Best practice: Test everything"},
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Execute
        result = hook.execute(context)

        # Verify - should not fail
        assert result.success
        assert not result.modified  # No learnings stored due to error
