"""Tests for the canonical normalize_agent_id() function."""

import pytest

from claude_mpm.utils.agent_filters import normalize_agent_id


@pytest.mark.parametrize(
    "input_id,expected",
    [
        # Basic transformations
        ("python_engineer", "python-engineer"),
        ("research-agent", "research"),
        ("qa-agent", "qa"),
        ("documentation-agent", "documentation"),
        ("engineer", "engineer"),
        ("research", "research"),
        # Underscore to kebab
        ("golang_engineer", "golang-engineer"),
        ("vercel_ops_agent", "vercel-ops"),
        ("gcp_ops_agent", "gcp-ops"),
        ("local_ops_agent", "local-ops"),
        # Already correct (idempotent)
        ("python-engineer", "python-engineer"),
        ("data-engineer", "data-engineer"),
        # PM -- no special case, lowercases like everything else
        ("PM", "pm"),
        ("QA", "qa"),
        # Empty / whitespace
        ("", ""),
        ("  ", ""),
        # Edge: "-agent" -> strip leading dash -> "agent" (valid name, not stripped)
        ("-agent", "agent"),
        # Edge: "agent" is NOT stripped (it IS the name, not a suffix)
        ("agent", "agent"),
        ("Agent", "agent"),
        # Spaces
        ("QA Agent", "qa"),
        ("Python Engineer", "python-engineer"),
        # Double dashes collapsed
        ("python--engineer", "python-engineer"),
        # Path-style: only leaf extracted
        ("engineer/backend/python-engineer", "python-engineer"),
        ("agents/research-agent.md", "research"),
        # Mixed case
        ("Python_Engineer", "python-engineer"),
        # File extensions stripped
        ("python-engineer.md", "python-engineer"),
        ("research.yaml", "research"),
        ("qa.json", "qa"),
        # Suffix variants
        ("ops-agent", "ops"),
        ("security-agent", "security"),
        ("version-control-agent", "version-control"),
        ("data-engineer-agent", "data-engineer"),
        ("engineer-agent", "engineer"),
        # Legacy underscore + agent suffix
        ("research_agent", "research"),
        ("qa_agent", "qa"),
    ],
)
def test_normalize_agent_id(input_id, expected):
    assert normalize_agent_id(input_id) == expected


def test_normalize_agent_id_idempotent():
    """Normalizing twice produces the same result."""
    ids = ["python-engineer", "research", "qa", "pm", "data-engineer", ""]
    for agent_id in ids:
        assert normalize_agent_id(normalize_agent_id(agent_id)) == normalize_agent_id(
            agent_id
        )


def test_normalize_agent_id_for_comparison_delegates():
    """normalize_agent_id_for_comparison delegates to normalize_agent_id."""
    from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

    test_cases = [
        "research-agent",
        "python_engineer",
        "PM",
        "qa-agent",
        "engineer/backend/python-engineer",
    ]
    for agent_id in test_cases:
        assert normalize_agent_id_for_comparison(agent_id) == normalize_agent_id(
            agent_id
        )
