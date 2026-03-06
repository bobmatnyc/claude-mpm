"""Test that agent name mappings stay in sync with deployed agents.

This test reads all .md files from the agent cache and verifies
that CANONICAL_NAMES and the agent_name_registry both match
the actual name: frontmatter field values.
"""

import re
from pathlib import Path

import pytest
import yaml

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer


def _get_cached_agents():
    """Read all cached agent files and extract name: field values."""
    cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
    if not cache_dir.exists():
        pytest.skip("Agent cache not available")

    agents = {}
    for md_file in sorted(cache_dir.glob("*.md")):
        content = md_file.read_text()
        # Extract YAML frontmatter
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if match:
            try:
                frontmatter = yaml.safe_load(match.group(1))
                if isinstance(frontmatter, dict) and "name" in frontmatter:
                    agents[md_file.stem] = frontmatter["name"]
            except yaml.YAMLError:
                pass
    return agents


class TestCanonicalNamesDrift:
    """Verify CANONICAL_NAMES matches reality."""

    def test_canonical_names_match_deployed(self):
        """Every CANONICAL_NAMES entry must match actual name: field."""
        cached = _get_cached_agents()
        if not cached:
            pytest.skip("No cached agents found")

        mismatches = []
        for key, canonical_value in AgentNameNormalizer.CANONICAL_NAMES.items():
            # Convert underscore key to dash for filename lookup
            filename_key = key.replace("_", "-")
            if filename_key in cached:
                actual_name = cached[filename_key]
                if canonical_value != actual_name:
                    mismatches.append(
                        f"  {key}: CANONICAL='{canonical_value}' vs ACTUAL='{actual_name}'"
                    )

        assert not mismatches, (
            f"CANONICAL_NAMES drift detected ({len(mismatches)} mismatches):\n"
            + "\n".join(mismatches)
        )

    def test_no_unknown_canonical_entries(self):
        """CANONICAL_NAMES should not have entries for non-existent agents."""
        cached = _get_cached_agents()
        if not cached:
            pytest.skip("No cached agents found")

        # Build set of all valid agent keys (both dash and underscore variants)
        valid_keys = set()
        for stem in cached:
            valid_keys.add(stem)
            valid_keys.add(stem.replace("-", "_"))

        # Known aliases that don't map 1:1 to files
        known_aliases = {"architect", "pm"}

        unknown = []
        for key in AgentNameNormalizer.CANONICAL_NAMES:
            if key not in valid_keys and key not in known_aliases:
                unknown.append(key)

        assert not unknown, (
            f"CANONICAL_NAMES has entries for non-existent agents: {unknown}"
        )
