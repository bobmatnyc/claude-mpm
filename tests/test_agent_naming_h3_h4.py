"""Tests for Phase H3 and H4: Agent naming normalization replacements.

H3: _normalize_agent_name() in multi_source_deployment_service.py
    now delegates to the canonical normalize_agent_id().
H4: Inline normalization in agent_state_manager.py now uses
    normalize_agent_id() instead of ad-hoc .replace() chains.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.services.agents.deployment.multi_source_deployment_service import (
    _normalize_agent_name,
)
from claude_mpm.utils.agent_filters import normalize_agent_id

# ---------------------------------------------------------------------------
# H3 Tests: _normalize_agent_name delegates to canonical normalize_agent_id
# ---------------------------------------------------------------------------


class TestNormalizeAgentNameH3:
    """Tests that _normalize_agent_name() delegates to normalize_agent_id()."""

    def test_normalize_agent_name_strips_agent_suffix(self) -> None:
        """H3: Input 'research-agent' should produce 'research'."""
        assert _normalize_agent_name("research-agent") == "research"

    def test_normalize_agent_name_handles_mixed_case_underscore(self) -> None:
        """H3: Input 'Python_Engineer-Agent' should produce 'python-engineer'."""
        assert _normalize_agent_name("Python_Engineer-Agent") == "python-engineer"

    def test_normalize_agent_name_delegates_to_canonical(self) -> None:
        """H3: _normalize_agent_name(x) == normalize_agent_id(x) for all inputs."""
        representative_inputs = [
            "research-agent",
            "Python_Engineer-Agent",
            "dart_engineer",
            "Dart Engineer",
            "DART-ENGINEER",
            "qa-agent",
            "PM",
            "data-engineer.md",
            "qa/BASE-AGENT",
            "",
            "  ",
            "simple",
            "multi--dash",
            "-agent",
        ]
        for name in representative_inputs:
            assert _normalize_agent_name(name) == normalize_agent_id(name), (
                f"Mismatch for input {name!r}: "
                f"_normalize_agent_name={_normalize_agent_name(name)!r}, "
                f"normalize_agent_id={normalize_agent_id(name)!r}"
            )

    def test_normalize_agent_name_lowercases(self) -> None:
        """H3: Mixed-case input is lowercased."""
        assert _normalize_agent_name("DART-ENGINEER") == "dart-engineer"

    def test_normalize_agent_name_replaces_spaces(self) -> None:
        """H3: Spaces become hyphens."""
        assert _normalize_agent_name("Dart Engineer") == "dart-engineer"

    def test_normalize_agent_name_replaces_underscores(self) -> None:
        """H3: Underscores become hyphens."""
        assert _normalize_agent_name("dart_engineer") == "dart-engineer"


# ---------------------------------------------------------------------------
# H4 Tests: agent_state_manager inline normalization replaced
# ---------------------------------------------------------------------------


class TestAgentStateManagerNormalizationH4:
    """Tests that agent_state_manager uses normalize_agent_id() correctly."""

    def test_agent_state_normalizes_mixed_case(self) -> None:
        """H4: 'Python_Engineer-Agent' -> 'python-engineer' via normalize_agent_id."""
        # This verifies the canonical normalizer handles the exact case that
        # the old inline code got wrong (no lowercasing before suffix strip).
        result = normalize_agent_id("Python_Engineer-Agent")
        assert result == "python-engineer"

    def test_agent_state_normalizes_underscore(self) -> None:
        """H4: 'dart_engineer' -> 'dart-engineer' via normalize_agent_id."""
        result = normalize_agent_id("dart_engineer")
        assert result == "dart-engineer"

    def test_agent_state_old_inline_was_wrong_for_mixed_case(self) -> None:
        """H4: Demonstrate the old inline code produced wrong results.

        Old code: agent_id.replace("-agent", "").replace("_", "-")
        For 'Python_Engineer-Agent':
          Step 1: .replace("-agent", "") -> 'Python_Engineer-Agent'
            (doesn't match '-agent' literally because of '-A' uppercase)
          Actually '-Agent' != '-agent' so no replacement happens!
          Step 2: .replace("_", "-") -> 'Python-Engineer-Agent'
          Result: 'Python-Engineer-Agent' (WRONG: still has mixed case + agent suffix)

        New code: normalize_agent_id("Python_Engineer-Agent") -> 'python-engineer'
        """
        # Old behavior (broken)
        old_result = "Python_Engineer-Agent".replace("-agent", "").replace("_", "-")
        # The old code doesn't lowercase first, so '-Agent' != '-agent'
        assert old_result == "Python-Engineer-Agent"  # Broken: mixed case + suffix

        # New behavior (correct)
        new_result = normalize_agent_id("Python_Engineer-Agent")
        assert new_result == "python-engineer"  # Correct: lowercase, no suffix

    def test_agent_state_manager_discovers_with_normalized_ids(self) -> None:
        """H4: Integration test that SimpleAgentManager uses normalize_agent_id.

        Create a minimal JSON template with an agent_id containing '-agent'
        suffix and underscores, then verify that discover_agents returns
        the correctly normalized name.
        """
        from claude_mpm.cli.commands.agent_state_manager import SimpleAgentManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".claude-mpm"
            config_dir.mkdir(parents=True)

            manager = SimpleAgentManager(config_dir)

            # Create a fake templates directory with a JSON template
            templates_dir = Path(tmpdir) / "templates"
            templates_dir.mkdir(parents=True)
            manager.templates_dir = templates_dir

            # Create a template with an agent_id that has -agent suffix
            template_data = {
                "agent_id": "python_engineer-agent",
                "metadata": {
                    "name": "Python Engineer Agent",
                    "description": "Test agent for normalization",
                },
                "capabilities": {
                    "tools": ["Read", "Write"],
                },
            }
            template_file = templates_dir / "python_engineer-agent.json"
            template_file.write_text(json.dumps(template_data))

            # Mock _is_agent_deployed to avoid filesystem checks
            with patch.object(manager, "_is_agent_deployed", return_value=False):
                # Discover local agents only (skip remote)
                agents = manager._discover_local_template_agents()

            # The agent name should be normalized via normalize_agent_id
            assert len(agents) == 1
            assert agents[0].name == "python-engineer"
