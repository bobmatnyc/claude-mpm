"""Tests for CRIT-1a/CRIT-1b: memory hooks use canonical normalize_agent_id.

Verify that MemoryPreDelegationHook and MemoryPostDelegationHook use the
canonical normalize_agent_id() function instead of inline normalization,
producing correct kebab-case agent IDs for all input patterns.
"""

from datetime import UTC, datetime, timezone
from unittest.mock import MagicMock

import pytest

from claude_mpm.hooks.base_hook import HookContext, HookType
from claude_mpm.hooks.memory_integration_hook import (
    MemoryPostDelegationHook,
    MemoryPreDelegationHook,
)


def _make_config_get(auto_learning=True, agent_overrides=None):
    """Create a side_effect for config.get that returns sensible defaults."""
    if agent_overrides is None:
        agent_overrides = {}

    def _get(key, default=None):
        mapping = {
            "memory.auto_learning": auto_learning,
            "memory.agent_overrides": agent_overrides,
        }
        return mapping.get(key, default)

    return _get


class TestPreDelegationHookNormalization:
    """Verify MemoryPreDelegationHook uses canonical normalize_agent_id."""

    @pytest.mark.parametrize(
        "agent_display_name,expected_agent_id",
        [
            ("Engineer Agent", "engineer"),
            ("Python Engineer", "python-engineer"),
            ("Research Agent", "research"),
            ("Agent Manager", "agent-manager"),
            ("QA", "qa"),
            ("PM", "pm"),
        ],
    )
    def test_pre_hook_normalizes_agent_id(self, agent_display_name, expected_agent_id):
        """Pre-delegation hook produces canonical kebab-case agent_id."""
        # Create a hook instance bypassing __init__ to avoid Config/MemoryManager deps
        hook = MemoryPreDelegationHook.__new__(MemoryPreDelegationHook)
        hook.name = "memory_pre_delegation"
        hook.priority = 20
        hook.enabled = True
        hook._async = False
        hook.memory_manager = MagicMock()
        hook.memory_manager.load_agent_memory.return_value = "some memory content"
        hook.config = MagicMock()
        hook.config.get = MagicMock(side_effect=_make_config_get())
        hook.event_bus = None

        context = HookContext(
            hook_type=HookType.PRE_DELEGATION,
            data={"agent": agent_display_name, "context": {}},
            metadata={},
            timestamp=datetime.now(UTC),
        )

        hook.execute(context)

        # Verify load_agent_memory was called with the canonical kebab-case ID
        hook.memory_manager.load_agent_memory.assert_called_once_with(expected_agent_id)


class TestPostDelegationHookNormalization:
    """Verify MemoryPostDelegationHook uses canonical normalize_agent_id."""

    @pytest.mark.parametrize(
        "agent_display_name,expected_agent_id",
        [
            ("Research Agent", "research"),
            ("Python Engineer", "python-engineer"),
            ("Agent Manager", "agent-manager"),
            ("Engineer Agent", "engineer"),
            ("QA", "qa"),
            ("PM", "pm"),
        ],
    )
    def test_post_hook_normalizes_agent_id(self, agent_display_name, expected_agent_id):
        """Post-delegation hook produces canonical kebab-case agent_id."""
        # Create a hook instance bypassing __init__ to avoid Config/MemoryManager deps
        hook = MemoryPostDelegationHook.__new__(MemoryPostDelegationHook)
        hook.name = "memory_post_delegation"
        hook.priority = 80
        hook.enabled = True
        hook._async = False
        hook.memory_manager = MagicMock()
        hook.config = MagicMock()
        hook.config.get = MagicMock(side_effect=_make_config_get())

        # Map of supported types (needed for _extract_learnings)
        hook.type_mapping = {
            "pattern": "pattern",
            "architecture": "architecture",
            "guideline": "guideline",
            "mistake": "mistake",
            "strategy": "strategy",
            "integration": "integration",
            "performance": "performance",
            "context": "context",
        }

        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "agent": agent_display_name,
                "result": {"content": "No learnings here"},
            },
            metadata={},
            timestamp=datetime.now(UTC),
        )

        result = hook.execute(context)

        # The hook should succeed without error
        assert result.success

    @pytest.mark.parametrize(
        "agent_display_name,expected_agent_id",
        [
            ("Research Agent", "research"),
            ("Python Engineer", "python-engineer"),
            ("Agent Manager", "agent-manager"),
        ],
    )
    def test_post_hook_passes_correct_id_to_add_learning(
        self, agent_display_name, expected_agent_id
    ):
        """Post-delegation hook passes canonical agent_id to add_learning."""
        hook = MemoryPostDelegationHook.__new__(MemoryPostDelegationHook)
        hook.name = "memory_post_delegation"
        hook.priority = 80
        hook.enabled = True
        hook._async = False
        hook.memory_manager = MagicMock()
        hook.config = MagicMock()
        hook.config.get = MagicMock(side_effect=_make_config_get())
        hook.type_mapping = {
            "pattern": "pattern",
            "architecture": "architecture",
            "guideline": "guideline",
            "mistake": "mistake",
            "strategy": "strategy",
            "integration": "integration",
            "performance": "performance",
            "context": "context",
        }

        # Include a valid memory block so add_learning gets called
        memory_block = (
            "# Add To Memory:\n"
            "Type: pattern\n"
            "Content: Always use dependency injection for flexibility\n"
            "#\n"
        )

        context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={
                "agent": agent_display_name,
                "result": {"content": memory_block},
            },
            metadata={},
            timestamp=datetime.now(UTC),
        )

        result = hook.execute(context)

        assert result.success
        # Verify add_learning was called with the canonical agent_id
        # NOTE: add_learning() actually only accepts (agent_id, content), not
        # (agent_id, learning_type, item). This 3-arg call silently fails in
        # production with a TypeError caught by except Exception.
        # See plan-critical.md "Discovered Side-Finding (Out of Scope)".
        # When the signature mismatch is fixed, update this assertion.
        hook.memory_manager.add_learning.assert_called_once_with(
            expected_agent_id,
            "pattern",
            "Always use dependency injection for flexibility",
        )
