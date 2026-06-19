"""Test dynamic agent name registry refresh."""

from unittest.mock import patch

from claude_mpm.core.agent_name_registry import (
    AGENT_NAME_MAP,
    CORE_AGENT_IDS,
    get_agent_name_map,
    invalidate_cache,
)

# Stable discovery result used to hermetically test name assertions.
# Mirrors the canonical real-user.md frontmatter (name: Real User) so
# that the test is not sensitive to what is or is not deployed on disk
# during the test run.
_STABLE_DISCOVERED: dict[str, str] = {
    "real-user": "Real User",
}


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
        """Non-conforming upstream name: values must be exact.

        Asserts the value returned by ``get_agent_name_map()``, which applies
        runtime discovery from ``.claude/agents/``. Discovery overrides the
        hardcoded ``AGENT_NAME_MAP`` baseline with each agent's actual
        frontmatter ``name:`` field, so the expected values below are the
        runtime-resolved names, not the registry baseline.

        NOTE: 'ticketing' and 'nestjs-engineer' are excluded because their
        frontmatter ``name:`` field is the raw lowercase id (e.g.
        ``nestjs-engineer``), which diverges from the registry display name
        (``NestJS Engineer``) and is therefore not a stable assertion target.

        Isolation: ``_discover_agents_from_paths`` is patched with a stable
        dict so this test does not depend on the real ``.claude/agents/``
        directory or ``~/.claude-mpm/cache/agents/``.  Without this patch,
        a sibling test that writes a ``real-user.md`` with
        ``name: real-user`` into any directory on the search path would
        pollute the module-level cache and cause this assertion to fail
        under ``pytest -n auto``.
        """
        non_conforming = {
            "real-user": "Real User",
        }
        try:
            with patch(
                "claude_mpm.core.agent_name_registry._discover_agents_from_paths",
                return_value=_STABLE_DISCOVERED,
            ):
                invalidate_cache()
                name_map = get_agent_name_map()
        finally:
            # Reset module-level cache so patched data never leaks to
            # subsequent tests, regardless of pass/fail outcome.
            invalidate_cache()

        for agent_id, expected_name in non_conforming.items():
            assert agent_id in name_map, f"Agent '{agent_id}' missing from name map"
            assert name_map[agent_id] == expected_name, (
                f"Non-conforming name for '{agent_id}': "
                f"expected '{expected_name}', got '{name_map[agent_id]}'"
            )
