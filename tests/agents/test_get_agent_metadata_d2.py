"""Regression tests for D2: AgentLoader.get_agent_metadata AttributeError.

get_agent_metadata() previously called self.registry.get_agent() which returns
an AgentMetadata dataclass, then called .get() on it.  AgentMetadata has no
.get() method, so this raised AttributeError.

The fix routes through self.get_agent() (the coercion method on AgentLoader
itself) which converts AgentMetadata to a plain dict before any .get() calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Minimal stub replicating just the relevant shape of AgentMetadata
# ---------------------------------------------------------------------------


@dataclass
class _FakeAgentMetadata:
    """Minimal dataclass with the same public surface as AgentMetadata.

    Critically, it does NOT have a .get() method — just like the real class.
    """

    name: str = "test_agent"
    agent_type: Any = None
    tier: Any = None
    path: str = ""
    format: Any = None
    last_modified: float = 0.0
    description: str = "A test agent"
    version: str = "1.0.0"
    specializations: list = field(default_factory=list)
    memory_files: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    is_memory_aware: bool = False
    collection_id: str | None = None
    source_path: str | None = None
    canonical_id: str | None = None


class TestGetAgentMetadataD2:
    """Verify that get_agent_metadata does not raise AttributeError."""

    def _make_loader_with_mock_registry(self, agent_id: str, return_value: Any):
        """Build an AgentLoader whose registry.get_agent() returns `return_value`."""
        from claude_mpm.agents.agent_loader import AgentLoader

        loader = AgentLoader.__new__(AgentLoader)

        # Stub out the registry with a mock
        mock_registry = MagicMock()
        mock_registry.get_agent.return_value = return_value
        mock_registry.get_agent_tier.return_value = None
        loader.registry = mock_registry

        return loader

    # ------------------------------------------------------------------
    # Core regression: calling get_agent_metadata when registry returns
    # a dataclass must NOT raise AttributeError.
    # ------------------------------------------------------------------

    def test_no_attribute_error_when_registry_returns_dataclass(self):
        """get_agent_metadata must not raise AttributeError on AgentMetadata."""
        agent_id = "test_agent"
        dataclass_instance = _FakeAgentMetadata(name=agent_id, path="/fake/path.md")

        loader = self._make_loader_with_mock_registry(agent_id, dataclass_instance)

        # self.get_agent() is the coercion method we now route through.
        # Mock it to return a proper dict so we can verify no AttributeError.
        coerced_dict = {
            "id": agent_id,
            "name": agent_id,
            "description": "A test agent",
            "version": "1.0.0",
            "tier": "system",
            "model": "sonnet",
            "resource_tier": "standard",
            "tools": [],
            "capabilities": {},
            "metadata": {},
            "instructions": "",
        }

        with patch.object(loader, "get_agent", return_value=coerced_dict):
            # This must NOT raise AttributeError
            result = loader.get_agent_metadata(agent_id)

        assert result is not None, "Expected a dict result, got None"
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result["agent_id"] == agent_id

    def test_returns_none_when_agent_not_found(self):
        """get_agent_metadata returns None when agent does not exist."""
        loader = self._make_loader_with_mock_registry("missing_agent", None)

        with patch.object(loader, "get_agent", return_value=None):
            result = loader.get_agent_metadata("missing_agent")

        assert result is None

    def test_result_contains_expected_keys(self):
        """get_agent_metadata result dict contains the documented keys."""
        agent_id = "my_agent"
        coerced_dict = {
            "id": agent_id,
            "name": "My Agent",
            "description": "Does things",
            "version": "2.0.0",
            "tier": "project",
            "model": "haiku",
            "resource_tier": "standard",
            "tools": ["Read", "Write"],
            "capabilities": {},
            "metadata": {
                "name": "My Agent",
                "description": "Does things",
                "category": "general",
                "version": "2.0.0",
            },
            "instructions": "Do things.",
        }

        loader = self._make_loader_with_mock_registry(agent_id, _FakeAgentMetadata())

        with patch.object(loader, "get_agent", return_value=coerced_dict):
            # registry.get_agent_tier returns None in this stub — handle it
            result = loader.get_agent_metadata(agent_id)

        assert result is not None
        expected_keys = {
            "agent_id",
            "name",
            "description",
            "category",
            "version",
            "model",
            "resource_tier",
            "tier",
            "tools",
            "capabilities",
            "source_file",
            "has_project_memory",
        }
        assert expected_keys.issubset(result.keys()), (
            f"Missing keys: {expected_keys - result.keys()}"
        )

    def test_dataclass_has_no_get_method(self):
        """Sanity check: confirm AgentMetadata stub truly lacks .get()."""
        instance = _FakeAgentMetadata()
        assert not hasattr(instance, "get"), (
            "Test stub unexpectedly has a .get() method — test assumption broken"
        )

    # ------------------------------------------------------------------
    # Verify the real AgentMetadata dataclass also lacks .get()
    # ------------------------------------------------------------------

    def test_real_agent_metadata_has_no_get_method(self):
        """The real AgentMetadata dataclass must not have a .get() method.

        If it does, the bug would not surface.  This ensures our fix remains
        meaningful should someone add .get() to AgentMetadata in the future —
        it would break this sentinel test and prompt a review.
        """
        try:
            from claude_mpm.core.unified_agent_registry import AgentMetadata
        except ImportError:
            pytest.skip("unified_agent_registry not importable in this environment")

        assert not hasattr(AgentMetadata, "get"), (
            "AgentMetadata grew a .get() method.  The D2 regression fix may no "
            "longer be necessary, but verify before removing it."
        )
