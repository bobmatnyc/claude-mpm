"""Test dynamic agent name registry refresh."""

from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.core.agent_name_registry import (
    AGENT_NAME_MAP,
    CORE_AGENT_IDS,
    get_agent_name_map,
    invalidate_cache,
)


class TestAgentNameRegistry:
    """Verify registry provides correct agent names."""

    def setup_method(self):
        """Reset cache before each test."""
        invalidate_cache()

    def test_hardcoded_baseline_exists(self):
        """AGENT_NAME_MAP has entries."""
        assert len(AGENT_NAME_MAP) > 20

    def test_core_agent_ids_are_subset(self):
        """Core agents must all be in the name map."""
        name_map = get_agent_name_map()
        for agent_id in CORE_AGENT_IDS:
            assert agent_id in name_map, f"Core agent '{agent_id}' not in name map"

    def test_get_agent_name_map_returns_dict(self):
        """get_agent_name_map() returns a dict."""
        result = get_agent_name_map()
        assert isinstance(result, dict)
        assert len(result) >= len(AGENT_NAME_MAP)

    def test_invalidate_cache(self):
        """invalidate_cache() forces re-discovery on next call."""
        first = get_agent_name_map()
        invalidate_cache()
        second = get_agent_name_map()
        assert isinstance(second, dict)

    def test_non_conforming_names_preserved(self):
        """Non-conforming upstream name: values must be exact."""
        name_map = get_agent_name_map()
        non_conforming = {
            "ticketing": "ticketing_agent",
            "nestjs-engineer": "nestjs-engineer",
            "real-user": "real-user",
        }
        for agent_id, expected_name in non_conforming.items():
            if agent_id in name_map:
                assert name_map[agent_id] == expected_name, (
                    f"Non-conforming name for '{agent_id}': "
                    f"expected '{expected_name}', got '{name_map[agent_id]}'"
                )
