"""Test that agent name mappings stay in sync with deployed agents.

This test reads all .md files from the agent cache and verifies
that CANONICAL_NAMES and the agent_name_registry both match
the actual name: frontmatter field values.

It also includes structural regression tests to prevent:
- C1 drift: Task(agent=...) values in templates not matching AGENT_NAME_MAP
- C2 drift: CANONICAL_NAMES values diverging from AGENT_NAME_MAP values
"""

import re
from pathlib import Path

import pytest
import yaml

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer
from claude_mpm.core.agent_name_registry import AGENT_NAME_MAP


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


# ---------------------------------------------------------------------------
# Structural regression tests (prevent C1 and C2 drift)
# ---------------------------------------------------------------------------

TEMPLATES_DIR = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "claude_mpm"
    / "agents"
    / "templates"
)

# Values from AGENT_NAME_MAP that are the authoritative set of valid agent names
VALID_AGENT_NAMES = set(AGENT_NAME_MAP.values())


class TestTemplateAgentReferences:
    """Scan template .md files for Task(agent="...") and validate names.

    Prevents C1 drift: template examples using wrong agent name format.
    Every Task(agent="X") value must exist as a VALUE in AGENT_NAME_MAP.
    """

    @staticmethod
    def _extract_task_agent_values(md_path: Path) -> list[tuple[int, str]]:
        """Extract (line_number, agent_name) from Task(agent="...") patterns."""
        pattern = re.compile(r'Task\(agent="([^"]+)"')
        results = []
        for i, line in enumerate(md_path.read_text().splitlines(), start=1):
            for m in pattern.finditer(line):
                results.append((i, m.group(1)))
        return results

    def test_all_template_task_agents_are_valid(self):
        """Every Task(agent="X") in templates must use a valid AGENT_NAME_MAP value."""
        if not TEMPLATES_DIR.is_dir():
            pytest.skip(f"Templates directory not found: {TEMPLATES_DIR}")

        invalid: list[str] = []
        for md_file in sorted(TEMPLATES_DIR.glob("*.md")):
            for line_no, agent_name in self._extract_task_agent_values(md_file):
                if agent_name not in VALID_AGENT_NAMES:
                    invalid.append(
                        f"  {md_file.name}:{line_no} — "
                        f'Task(agent="{agent_name}") not in AGENT_NAME_MAP values'
                    )

        assert not invalid, (
            f"Found {len(invalid)} Task(agent=...) references with invalid agent names:\n"
            + "\n".join(invalid)
            + "\n\nValid agent names (AGENT_NAME_MAP values):\n  "
            + "\n  ".join(sorted(VALID_AGENT_NAMES))
        )


class TestCanonicalNamesAlignment:
    """Verify CANONICAL_NAMES values match AGENT_NAME_MAP values.

    Prevents C2 drift: CANONICAL_NAMES display names diverging from
    what AGENT_NAME_MAP says (which mirrors upstream name: frontmatter).

    For every key in CANONICAL_NAMES that has a corresponding entry in
    AGENT_NAME_MAP (underscore→hyphen conversion), the display name
    values must match.
    """

    def test_canonical_names_match_agent_name_map(self):
        """CANONICAL_NAMES values must match AGENT_NAME_MAP for overlapping keys."""
        mismatches: list[str] = []

        for canon_key, canon_value in AgentNameNormalizer.CANONICAL_NAMES.items():
            # Convert underscore key to hyphen for AGENT_NAME_MAP lookup
            registry_key = canon_key.replace("_", "-")
            if registry_key in AGENT_NAME_MAP:
                registry_value = AGENT_NAME_MAP[registry_key]
                if canon_value != registry_value:
                    mismatches.append(
                        f"  {canon_key}: "
                        f"CANONICAL_NAMES='{canon_value}' vs "
                        f"AGENT_NAME_MAP['{registry_key}']='{registry_value}'"
                    )

        assert not mismatches, (
            f"CANONICAL_NAMES / AGENT_NAME_MAP drift detected "
            f"({len(mismatches)} mismatches):\n"
            + "\n".join(mismatches)
            + "\n\nFix: Update CANONICAL_NAMES values to match AGENT_NAME_MAP "
            "(which mirrors upstream name: frontmatter)."
        )
