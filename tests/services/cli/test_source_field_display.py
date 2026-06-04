"""Tests for `source` field display in the agents list command.

Verifies that:
- AgentInfo carries the `source` field through the listing service data path
- AgentOutputFormatter renders `source` in both text and table output
- When `source` is present the value (bundled/external) appears in output
- When `source` is absent, output handles it gracefully (blank / placeholder)

These tests are unit tests that mock the deployment service so they run without
any on-disk agent files or network access.
"""

from unittest.mock import Mock

import pytest

from claude_mpm.services.cli.agent_listing_service import AgentInfo, AgentListingService
from claude_mpm.services.cli.agent_output_formatter import AgentOutputFormatter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_data(
    name: str = "test-agent",
    source: str | None = None,
    version: str = "1.0.0",
    description: str = "A test agent.",
) -> dict:
    """Return a dict that mimics the shape returned by the deployment service."""
    data: dict = {
        "name": name,
        "agent_type": "engineer",
        "path": f"/path/to/{name}.md",
        "description": description,
        "version": version,
    }
    if source is not None:
        data["source"] = source
    return data


def _make_deployment_service(agents: list[dict]) -> Mock:
    """Return a mock deployment service that vends the given agent list."""
    service = Mock()
    service.list_available_agents.return_value = agents
    service.verify_deployment.return_value = {
        "agents_found": agents,
        "warnings": [],
    }
    return service


# ---------------------------------------------------------------------------
# AgentInfo dataclass
# ---------------------------------------------------------------------------


class TestAgentInfoSourceField:
    """The AgentInfo dataclass must carry and expose the source field."""

    def test_source_bundled_stored(self) -> None:
        agent = AgentInfo(
            name="my-agent",
            type="engineer",
            tier="system",
            path="/path/my-agent.md",
            source="bundled",
        )
        assert agent.source == "bundled"

    def test_source_external_stored(self) -> None:
        agent = AgentInfo(
            name="my-agent",
            type="engineer",
            tier="system",
            path="/path/my-agent.md",
            source="external",
        )
        assert agent.source == "external"

    def test_source_none_is_default(self) -> None:
        agent = AgentInfo(
            name="my-agent",
            type="engineer",
            tier="system",
            path="/path/my-agent.md",
        )
        assert agent.source is None


# ---------------------------------------------------------------------------
# AgentListingService — source flows through data layer
# ---------------------------------------------------------------------------


class TestListingServiceSourcePropagation:
    """list_system_agents() must pass the source value from deployment data into AgentInfo."""

    def test_bundled_source_propagates(self) -> None:
        mock_svc = _make_deployment_service(
            [_make_agent_data("bundled-agent", source="bundled")]
        )
        listing = AgentListingService(deployment_service=mock_svc)
        listing.clear_cache()

        agents = listing.list_system_agents(verbose=True)

        assert len(agents) == 1
        assert agents[0].source == "bundled"

    def test_external_source_propagates(self) -> None:
        mock_svc = _make_deployment_service(
            [_make_agent_data("external-agent", source="external")]
        )
        listing = AgentListingService(deployment_service=mock_svc)
        listing.clear_cache()

        agents = listing.list_system_agents(verbose=True)

        assert len(agents) == 1
        assert agents[0].source == "external"

    def test_absent_source_propagates_as_none(self) -> None:
        """An agent dict without a 'source' key must produce AgentInfo.source == None."""
        mock_svc = _make_deployment_service(
            [_make_agent_data("legacy-agent", source=None)]
        )
        listing = AgentListingService(deployment_service=mock_svc)
        listing.clear_cache()

        agents = listing.list_system_agents(verbose=True)

        assert len(agents) == 1
        assert agents[0].source is None

    def test_mixed_sources_preserved(self) -> None:
        """Multiple agents each keep their own source value."""
        mock_svc = _make_deployment_service(
            [
                _make_agent_data("bundled-agent", source="bundled"),
                _make_agent_data("external-agent", source="external"),
                _make_agent_data("legacy-agent", source=None),
            ]
        )
        listing = AgentListingService(deployment_service=mock_svc)
        listing.clear_cache()

        agents = listing.list_system_agents(verbose=True)
        by_name = {a.name: a for a in agents}

        assert by_name["bundled-agent"].source == "bundled"
        assert by_name["external-agent"].source == "external"
        assert by_name["legacy-agent"].source is None


# ---------------------------------------------------------------------------
# AgentOutputFormatter — source appears in rendered output
# ---------------------------------------------------------------------------


class TestFormatterTextOutput:
    """Text-format output must include the source value when present."""

    @pytest.fixture
    def formatter(self) -> AgentOutputFormatter:
        return AgentOutputFormatter()

    def test_bundled_appears_in_text(self, formatter: AgentOutputFormatter) -> None:
        agents = [
            {
                "name": "bundled-agent",
                "file": "bundled-agent.md",
                "version": "1.0.0",
                "description": "A bundled agent.",
                "source": "bundled",
            }
        ]
        output = formatter.format_agent_list(agents, output_format="text")

        assert "bundled" in output, f"Expected 'bundled' in output:\n{output}"

    def test_external_appears_in_text(self, formatter: AgentOutputFormatter) -> None:
        agents = [
            {
                "name": "external-agent",
                "file": "external-agent.md",
                "version": "1.0.0",
                "description": "An external agent.",
                "source": "external",
            }
        ]
        output = formatter.format_agent_list(agents, output_format="text")

        assert "external" in output, f"Expected 'external' in output:\n{output}"

    def test_absent_source_does_not_crash(
        self, formatter: AgentOutputFormatter
    ) -> None:
        """An agent dict without `source` must not raise an exception."""
        agents = [
            {
                "name": "legacy-agent",
                "file": "legacy-agent.md",
                "version": "1.0.0",
                "description": "A legacy agent.",
                # no 'source' key
            }
        ]
        # Must not raise; source line is simply omitted
        output = formatter.format_agent_list(agents, output_format="text")
        assert "legacy-agent" in output

    def test_source_none_does_not_crash(self, formatter: AgentOutputFormatter) -> None:
        """An agent dict with source=None must not raise an exception."""
        agents = [
            {
                "name": "none-source-agent",
                "file": "none-source-agent.md",
                "version": "1.0.0",
                "description": "An agent with null source.",
                "source": None,
            }
        ]
        output = formatter.format_agent_list(agents, output_format="text")
        assert "none-source-agent" in output


class TestFormatterTableOutput:
    """Table-format output must include a Source column with the correct value."""

    @pytest.fixture
    def formatter(self) -> AgentOutputFormatter:
        return AgentOutputFormatter()

    def test_source_column_header_present(
        self, formatter: AgentOutputFormatter
    ) -> None:
        agents = [
            {
                "name": "test-agent",
                "file": "test-agent.md",
                "version": "1.0.0",
                "description": "A test agent.",
                "source": "bundled",
            }
        ]
        output = formatter.format_agent_list(agents, output_format="table")

        assert "Source" in output, f"Expected 'Source' column header:\n{output}"

    def test_bundled_value_in_table(self, formatter: AgentOutputFormatter) -> None:
        agents = [
            {
                "name": "bundled-agent",
                "file": "bundled-agent.md",
                "version": "1.0.0",
                "description": "A bundled agent.",
                "source": "bundled",
            }
        ]
        output = formatter.format_agent_list(agents, output_format="table")

        assert "bundled" in output, f"Expected 'bundled' value in table:\n{output}"

    def test_external_value_in_table(self, formatter: AgentOutputFormatter) -> None:
        agents = [
            {
                "name": "external-agent",
                "file": "external-agent.md",
                "version": "1.0.0",
                "description": "An external agent.",
                "source": "external",
            }
        ]
        output = formatter.format_agent_list(agents, output_format="table")

        assert "external" in output, f"Expected 'external' value in table:\n{output}"

    def test_absent_source_shows_placeholder_in_table(
        self, formatter: AgentOutputFormatter
    ) -> None:
        """Missing source should display a placeholder (e.g. '-') rather than crash."""
        agents = [
            {
                "name": "legacy-agent",
                "file": "legacy-agent.md",
                "version": "1.0.0",
                "description": "An agent without source.",
                # no 'source' key
            }
        ]
        output = formatter.format_agent_list(agents, output_format="table")

        # Must not raise; a placeholder ('-') should appear in the Source column
        assert "Source" in output
        assert "-" in output, f"Expected '-' placeholder for absent source:\n{output}"

    def test_none_source_shows_placeholder_in_table(
        self, formatter: AgentOutputFormatter
    ) -> None:
        """source=None should display a placeholder rather than 'None'."""
        agents = [
            {
                "name": "none-agent",
                "file": "none-agent.md",
                "version": "1.0.0",
                "description": "Agent with null source.",
                "source": None,
            }
        ]
        output = formatter.format_agent_list(agents, output_format="table")

        # The formatter uses `agent.get("source") or "-"`, so None → "-"
        assert "Source" in output
        assert "-" in output

    def test_verbose_table_includes_source(
        self, formatter: AgentOutputFormatter
    ) -> None:
        """Verbose table mode must also show the Source column."""
        agents = [
            {
                "name": "agent-x",
                "file": "agent-x.md",
                "version": "2.0.0",
                "description": "Verbose test agent.",
                "source": "external",
                "tier": "system",
                "path": "/path/agent-x.md",
            }
        ]
        output = formatter.format_agent_list(
            agents, output_format="table", verbose=True
        )

        assert "Source" in output
        assert "external" in output
