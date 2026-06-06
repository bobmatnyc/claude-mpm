"""Routing-intact and token-budget regression tests for the capabilities section.

Purpose: Verify that after the issue-#678 conservative trim:

1. Every deployed agent's name *and* subagent_type (routing ID) appear inline
   in the assembled ``## Available Agent Capabilities`` section so the PM can
   still route to all of them.

2. The capabilities section stays below its own size budget (issue-#678
   target: ≤9 KB / ~2,250 tokens for a typical 40-agent set).

3. The terse one-liner format is used (no verbose ``### heading`` sub-sections
   per agent, no ``**Memory Routing**`` lines).

4. The delegation routing table (``## Context-Aware Agent Selection``) is
   present in the output.

Strategy: unit-test ``CapabilityGenerator`` directly with a synthetic agent
list so the test is fast and deterministic regardless of which agents happen
to be deployed in the developer's ``~/.claude/agents``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework.formatters.capability_generator import (
    CapabilityGenerator,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Canonical set of core MPM agents — these MUST always route correctly.
CORE_AGENTS: list[dict[str, Any]] = [
    {
        "id": "engineer",
        "display_name": "Engineer",
        "description": "Code implementation and development",
        "model": "sonnet",
    },
    {
        "id": "research",
        "display_name": "Research",
        "description": "Codebase analysis and investigation",
        "model": "sonnet",
        "memory_routing": {
            "description": "Stores analysis findings",
            "categories": ["findings"],
        },
    },
    {
        "id": "qa",
        "display_name": "QA",
        "description": "Testing and quality assurance",
        "model": "sonnet",
        "memory_routing": {"description": "Stores testing patterns"},
    },
    {
        "id": "documentation",
        "display_name": "Documentation Agent",
        "description": "Documentation creation and maintenance",
        "model": "haiku",
    },
    {
        "id": "security",
        "display_name": "Security",
        "description": "Security analysis and protection",
        "model": "sonnet",
    },
    {
        "id": "ops",
        "display_name": "Ops",
        "description": "Deployment and operations",
        "model": "haiku",
        "authority": {"git_commit": True, "file_operations": True},
    },
    {
        "id": "version-control",
        "display_name": "Version Control",
        "description": "Git operations and branch management",
        "model": "haiku",
    },
    {
        "id": "data-engineer",
        "display_name": "Data Engineer",
        "description": "Data management and ETL pipelines",
        "model": "sonnet",
    },
    {
        "id": "python-engineer",
        "display_name": "Python Engineer",
        "description": "Python 3.12+ specialist with type safety",
        "model": "sonnet",
        "memory_routing": {"description": "Stores Python patterns"},
    },
    {
        "id": "typescript-engineer",
        "display_name": "Typescript Engineer",
        "description": "TypeScript 5.6+ specialist",
        "model": "sonnet",
        "memory_routing": {"description": "Stores TypeScript patterns"},
    },
]

# Add a local-tier agent to verify the [LOCAL] suffix path.
LOCAL_AGENTS: dict[str, dict[str, Any]] = {
    "custom-agent": {
        "id": "custom-agent",
        "display_name": "Custom Agent",
        "description": "Project-specific custom agent",
        "is_local": True,
        "tier": "project",
    },
}


@pytest.fixture(scope="module")
def generator() -> CapabilityGenerator:
    return CapabilityGenerator()


@pytest.fixture(scope="module")
def capabilities_section(generator: CapabilityGenerator) -> str:
    return generator.generate_capabilities_section(CORE_AGENTS, LOCAL_AGENTS)


# ---------------------------------------------------------------------------
# Test: All agent names and IDs appear inline
# ---------------------------------------------------------------------------


class TestRoutingIntact:
    """Every agent name and subagent_type must appear in the capabilities block
    so the PM can select the right one without guessing.

    These are the non-negotiable routing guardrails from issue #678.
    """

    @pytest.mark.parametrize(
        "agent_id",
        [a["id"] for a in CORE_AGENTS] + list(LOCAL_AGENTS.keys()),
        ids=[a["id"] for a in CORE_AGENTS] + list(LOCAL_AGENTS.keys()),
    )
    def test_agent_id_present(self, capabilities_section: str, agent_id: str) -> None:
        """Each agent's subagent_type (routing ID) must appear in back-ticks."""
        assert f"`{agent_id}`" in capabilities_section, (
            f"Agent ID {agent_id!r} not found in capabilities section "
            "(PM cannot route to this agent)"
        )

    @pytest.mark.parametrize(
        "display_name",
        [a["display_name"] for a in CORE_AGENTS] + ["Custom Agent"],
        ids=[a["display_name"] for a in CORE_AGENTS] + ["Custom Agent"],
    )
    def test_agent_display_name_present(
        self, capabilities_section: str, display_name: str
    ) -> None:
        """Each agent's human-readable name must appear inline."""
        assert display_name in capabilities_section, (
            f"Display name {display_name!r} not found in capabilities section"
        )

    def test_context_aware_selection_table_present(
        self, capabilities_section: str
    ) -> None:
        """The delegation routing table must be present."""
        assert "## Context-Aware Agent Selection" in capabilities_section, (
            "Context-Aware Agent Selection section missing — PM cannot route tasks"
        )

    def test_pm_routing_principle_present(self, capabilities_section: str) -> None:
        """The 'PM questions → Answer directly' rule must be in the routing table."""
        assert "PM questions" in capabilities_section, (
            "'PM questions' routing hint missing from capabilities section"
        )

    def test_task_tool_instruction_present(self, capabilities_section: str) -> None:
        """The instruction to use the agent ID via Task tool must be present."""
        assert "Task tool" in capabilities_section, (
            "Task tool delegation instruction missing from capabilities section"
        )

    def test_total_agent_count_line_present(self, capabilities_section: str) -> None:
        """A total-agent count line must be present."""
        assert "Total Available Agents" in capabilities_section, (
            "Total Available Agents count line missing"
        )


# ---------------------------------------------------------------------------
# Test: Terse one-liner format (no verbose headings / Memory Routing fields)
# ---------------------------------------------------------------------------


class TestTerseFormat:
    """Verify the output uses the compact one-liner format from issue #678.

    Memory Routing, Authority, Routing-keywords, and other per-agent verbose
    fields must not appear.  Every agent must emit exactly one bullet line.
    """

    def test_no_memory_routing_fields(self, capabilities_section: str) -> None:
        """``**Memory Routing**`` lines must not appear — they cost ~860 tokens."""
        assert "**Memory Routing**" not in capabilities_section, (
            "Memory Routing field found in capabilities section — "
            "verbose trim from issue #678 was reverted"
        )

    def test_no_agent_subheadings(self, capabilities_section: str) -> None:
        """``### Agent Name`` sub-headings must not appear inside the section."""
        # The section header itself is ##, agents must be bullet lines not ###
        # Find the section
        start = capabilities_section.find("## Available Agent Capabilities")
        assert start != -1
        end_next = capabilities_section.find("\n## ", start + 3)
        section_body = (
            capabilities_section[start:end_next]
            if end_next != -1
            else capabilities_section[start:]
        )
        # Within the agent list (before Context-Aware section) there must be
        # no ### headings — those were the old verbose format.
        list_end = section_body.find("## Context-Aware Agent Selection")
        agent_list_body = section_body[:list_end] if list_end != -1 else section_body
        assert "### " not in agent_list_body, (
            "Found '### ' agent sub-headings inside capabilities section — "
            "old verbose format may have been re-introduced"
        )

    def test_bullet_format_per_agent(self, capabilities_section: str) -> None:
        """Core agents must use '- **Name** (`id`) — description' bullet format."""
        # Spot-check engineer and research (always present in CORE_AGENTS)
        assert "- **Engineer** (`engineer`)" in capabilities_section, (
            "Engineer agent not in expected '- **Name** (`id`)' bullet format"
        )
        assert "- **Research** (`research`)" in capabilities_section, (
            "Research agent not in expected '- **Name** (`id`)' bullet format"
        )

    def test_local_agent_has_local_marker(self, capabilities_section: str) -> None:
        """Local-tier agents must have a [LOCAL-...] suffix in the bullet line."""
        # Find the custom-agent line
        line = next(
            (l for l in capabilities_section.splitlines() if "`custom-agent`" in l),
            None,
        )
        assert line is not None, "custom-agent not found in capabilities section"
        assert "[LOCAL-" in line, (
            f"Local-tier agent line missing [LOCAL-...] marker: {line!r}"
        )

    def test_model_hint_in_haiku_line(self, capabilities_section: str) -> None:
        """Non-opus agents should have their model hint inline."""
        # 'ops' agent has model=haiku
        ops_line = next(
            (l for l in capabilities_section.splitlines() if "`ops`" in l),
            None,
        )
        assert ops_line is not None, "ops agent not found in capabilities"
        assert "[haiku]" in ops_line, (
            f"Model hint '[haiku]' missing from ops agent line: {ops_line!r}"
        )


# ---------------------------------------------------------------------------
# Test: Token budget regression
# ---------------------------------------------------------------------------

# Per-agent ceiling: 256 bytes per agent x 40 agents + 512 bytes overhead = ~10.7 KB.
# With the terse format the actual is ~10-11 bytes/char x (130 chars/agent).
# Set a per-section ceiling that's generous enough not to false-positive on
# unusual agent descriptions.
MAX_CAP_SECTION_BYTES = 12_000  # ~3 000 tokens — warns if verbose format returns

# Bytes per agent ceiling for the terse format
MAX_BYTES_PER_AGENT = 300  # one-liner should be well under this


class TestTokenBudget:
    """Regression guard: capabilities section must stay under its token budget.

    These limits are intentionally generous to avoid false positives from
    unusually long agent descriptions, while still catching re-introduction of
    the verbose ``### heading + multi-field`` format that this trim removed.
    """

    def test_capabilities_section_under_byte_ceiling(
        self, capabilities_section: str
    ) -> None:
        """Total capabilities section must stay below MAX_CAP_SECTION_BYTES."""
        section_bytes = len(capabilities_section.encode("utf-8"))
        assert section_bytes <= MAX_CAP_SECTION_BYTES, (
            f"Capabilities section too large: {section_bytes} bytes "
            f"(limit: {MAX_CAP_SECTION_BYTES}). "
            "The verbose heading format may have been re-introduced."
        )

    def test_average_bytes_per_agent_under_ceiling(
        self, generator: CapabilityGenerator, capabilities_section: str
    ) -> None:
        """Average bytes per agent must stay well below MAX_BYTES_PER_AGENT."""
        n_agents = len(CORE_AGENTS) + len(LOCAL_AGENTS)
        # Subtract the trailing Context-Aware section (~300 bytes)
        context_start = capabilities_section.find("## Context-Aware Agent Selection")
        agent_list_bytes = (
            len(capabilities_section[:context_start].encode("utf-8"))
            if context_start != -1
            else len(capabilities_section.encode("utf-8"))
        )
        avg = agent_list_bytes / n_agents
        assert avg <= MAX_BYTES_PER_AGENT, (
            f"Average bytes per agent too high: {avg:.0f} bytes "
            f"(limit: {MAX_BYTES_PER_AGENT}). "
            "Check that Memory Routing / Authority fields are not being emitted."
        )


# ---------------------------------------------------------------------------
# Test: Fallback capabilities still mention core agents
# ---------------------------------------------------------------------------


class TestFallbackCapabilities:
    """The fallback section (no agents deployed) must still mention core agents."""

    def test_fallback_contains_engineer(self, generator: CapabilityGenerator) -> None:
        fallback = generator.get_fallback_capabilities()
        assert "engineer" in fallback, (
            "'engineer' not in fallback capabilities — fallback is missing core agents"
        )

    def test_fallback_contains_header(self, generator: CapabilityGenerator) -> None:
        fallback = generator.get_fallback_capabilities()
        assert "## Available Agent Capabilities" in fallback

    def test_empty_agents_returns_fallback(
        self, generator: CapabilityGenerator
    ) -> None:
        result = generator.generate_capabilities_section([], {})
        assert "## Available Agent Capabilities" in result
