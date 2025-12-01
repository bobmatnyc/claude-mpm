"""Integration test: Verify BASE-AGENT.md is optional for real-world repositories.

This test validates that agent repositories WITHOUT BASE-AGENT.md files
deploy successfully without errors or warnings.

Real-world test case: bobmatnyc/claude-mpm-agents repository
- Contains 45+ agent markdown files
- No BASE-AGENT.md files anywhere in the repository
- No BASE_{TYPE}.md files
- Should deploy perfectly without any BASE template composition
"""

import json
import tempfile
from pathlib import Path

import pytest

from claude_mpm.services.agents.deployment.agent_template_builder import (
    AgentTemplateBuilder,
)


@pytest.fixture
def template_builder():
    """Create AgentTemplateBuilder instance for testing."""
    return AgentTemplateBuilder()


def create_agent_file(path: Path, content: str):
    """Helper to create agent markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def create_agent_json(path: Path, data: dict):
    """Helper to create agent JSON template."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


class TestNonCompliantRepositoryCompatibility:
    """Test compatibility with repositories that don't use BASE-AGENT.md pattern."""

    def test_simple_agent_without_any_base_templates(self, template_builder):
        """Test deployment of simple agent with no BASE templates anywhere."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            # Create git root marker (no BASE-AGENT.md at any level)
            (repo_root / ".git").mkdir()

            # Create simple agent structure (like bobmatnyc repo)
            agents_dir = repo_root / "agents"
            agents_dir.mkdir()

            # Create agent JSON (similar to real agent templates)
            agent_file = agents_dir / "engineer.md"
            agent_data = {
                "name": "engineer",
                "description": "Software engineering agent for code implementation",
                "agent_type": "engineer",
                "instructions": "# Engineer Agent\n\nImplement features with clean code.",
            }
            create_agent_json(agent_file, agent_data)

            # Build agent markdown - should succeed without BASE templates
            result = template_builder.build_agent_markdown(
                "engineer", agent_file, {}, "test"
            )

            # Verify agent deploys successfully
            assert result is not None
            assert "# Engineer Agent" in result
            assert "Implement features with clean code." in result
            assert "---" in result  # YAML frontmatter separator
            assert "name: engineer" in result

    def test_nested_agent_without_any_base_templates(self, template_builder):
        """Test deployment of nested agent structure with no BASE templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            # Create git root marker
            (repo_root / ".git").mkdir()

            # Create nested structure (like categorized agents)
            # repo/
            #   agents/
            #     engineering/
            #       python/
            #         fastapi-engineer.md

            python_dir = repo_root / "agents" / "engineering" / "python"
            python_dir.mkdir(parents=True)

            # Create agent
            agent_file = python_dir / "fastapi-engineer.md"
            agent_data = {
                "name": "fastapi-engineer",
                "description": "FastAPI specialist for async APIs",
                "agent_type": "engineer",
                "instructions": "# FastAPI Engineer\n\nBuild high-performance async APIs.",
            }
            create_agent_json(agent_file, agent_data)

            # Build agent markdown - should succeed without BASE templates
            result = template_builder.build_agent_markdown(
                "fastapi-engineer", agent_file, {}, "test"
            )

            # Verify agent deploys successfully
            assert result is not None
            assert "# FastAPI Engineer" in result
            assert "Build high-performance async APIs." in result

    def test_multiple_agents_no_shared_base(self, template_builder):
        """Test repository with multiple agents but no shared BASE templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".git").mkdir()

            agents_dir = repo_root / "agents"
            agents_dir.mkdir()

            # Create multiple diverse agents (like bobmatnyc repo)
            agents = [
                {
                    "file": "engineer.md",
                    "name": "engineer",
                    "type": "engineer",
                    "instructions": "# Engineer\n\nWrite code.",
                },
                {
                    "file": "qa.md",
                    "name": "qa",
                    "type": "qa",
                    "instructions": "# QA\n\nTest code.",
                },
                {
                    "file": "ops.md",
                    "name": "ops",
                    "type": "ops",
                    "instructions": "# Ops\n\nDeploy code.",
                },
            ]

            # Deploy each agent without BASE templates
            for agent_info in agents:
                agent_file = agents_dir / agent_info["file"]
                agent_data = {
                    "name": agent_info["name"],
                    "description": f"{agent_info['name']} agent",
                    "agent_type": agent_info["type"],
                    "instructions": agent_info["instructions"],
                }
                create_agent_json(agent_file, agent_data)

                # Build agent markdown
                result = template_builder.build_agent_markdown(
                    agent_info["name"], agent_file, {}, "test"
                )

                # Each should deploy independently
                assert result is not None
                assert agent_info["instructions"] in result

    def test_bobmatnyc_style_flat_structure(self, template_builder):
        """Test flat repository structure like bobmatnyc/claude-mpm-agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".git").mkdir()

            # bobmatnyc uses flat structure: repo/agents/*.md
            agents_dir = repo_root / "agents"
            agents_dir.mkdir()

            # Sample agents from bobmatnyc repo
            test_agents = [
                ("engineer.md", "engineer", "engineer"),
                ("python_engineer.md", "python-engineer", "engineer"),
                ("typescript_engineer.md", "typescript-engineer", "engineer"),
                ("qa.md", "qa", "qa"),
                ("research.md", "research", "research"),
            ]

            for filename, name, agent_type in test_agents:
                agent_file = agents_dir / filename
                agent_data = {
                    "name": name,
                    "description": f"{name} agent for specialized tasks",
                    "agent_type": agent_type,
                    "instructions": f"# {name.title()} Agent\n\nSpecialized instructions here.",
                }
                create_agent_json(agent_file, agent_data)

                # Build agent markdown
                result = template_builder.build_agent_markdown(
                    name, agent_file, {}, "test"
                )

                # Verify successful deployment
                assert result is not None
                assert (
                    f"# {name.title()} Agent" in result
                    or f"# {name.replace('-', ' ').title()} Agent" in result
                )

    def test_no_warnings_for_missing_base_templates(self, template_builder, caplog):
        """Verify no warnings are logged when BASE templates are intentionally absent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".git").mkdir()

            agent_file = repo_root / "agents" / "test-agent.md"
            agent_data = {
                "name": "test-agent",
                "description": "Test agent",
                "agent_type": "general",
                "instructions": "# Test Agent",
            }
            create_agent_json(agent_file, agent_data)

            # Clear any previous logs
            caplog.clear()

            # Build agent markdown
            template_builder.build_agent_markdown("test-agent", agent_file, {}, "test")

            # Verify NO warnings about missing BASE templates
            warning_logs = [
                record
                for record in caplog.records
                if record.levelname == "WARNING" and "BASE-AGENT.md" in record.message
            ]
            assert len(warning_logs) == 0, "Should not warn about missing BASE-AGENT.md"

    def test_discovery_returns_empty_list_for_non_compliant_repo(
        self, template_builder
    ):
        """Verify _discover_base_agent_templates returns [] for non-compliant repos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".git").mkdir()

            # Create deep directory structure with NO BASE-AGENT.md files
            deep_path = (
                repo_root / "agents" / "category" / "subcategory" / "specialized"
            )
            deep_path.mkdir(parents=True)

            agent_file = deep_path / "agent.md"
            agent_file.write_text("# Agent")

            # Discover BASE templates
            discovered = template_builder._discover_base_agent_templates(agent_file)

            # Should return empty list, not None or exception
            assert discovered == []
            assert isinstance(discovered, list)

    def test_graceful_handling_of_mixed_repository(self, template_builder):
        """Test repository where some agents have BASE templates, others don't."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".git").mkdir()

            # Create two subdirectories
            compliant_dir = repo_root / "agents" / "compliant"
            non_compliant_dir = repo_root / "agents" / "non-compliant"
            compliant_dir.mkdir(parents=True)
            non_compliant_dir.mkdir(parents=True)

            # Compliant agent WITH BASE-AGENT.md
            base_file = compliant_dir / "BASE-AGENT.md"
            base_file.write_text("# Compliant Base Template")

            compliant_agent = compliant_dir / "agent-with-base.md"
            create_agent_json(
                compliant_agent,
                {
                    "name": "agent-with-base",
                    "description": "Agent with BASE template",
                    "agent_type": "engineer",
                    "instructions": "# Agent With Base",
                },
            )

            # Non-compliant agent WITHOUT BASE-AGENT.md
            non_compliant_agent = non_compliant_dir / "agent-without-base.md"
            create_agent_json(
                non_compliant_agent,
                {
                    "name": "agent-without-base",
                    "description": "Agent without BASE template",
                    "agent_type": "engineer",
                    "instructions": "# Agent Without Base",
                },
            )

            # Both should deploy successfully
            compliant_result = template_builder.build_agent_markdown(
                "agent-with-base", compliant_agent, {}, "test"
            )
            non_compliant_result = template_builder.build_agent_markdown(
                "agent-without-base", non_compliant_agent, {}, "test"
            )

            # Compliant agent should have BASE content
            assert "# Compliant Base Template" in compliant_result

            # Non-compliant agent should NOT have BASE content (expected)
            assert "# Compliant Base Template" not in non_compliant_result
            assert "# Agent Without Base" in non_compliant_result


class TestEdgeCasesNonCompliantRepos:
    """Test edge cases specific to non-compliant repositories."""

    def test_agent_at_repository_root(self, template_builder):
        """Test agent located at repository root with no subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".git").mkdir()

            # Agent directly in repo root
            agent_file = repo_root / "standalone-agent.md"
            create_agent_json(
                agent_file,
                {
                    "name": "standalone-agent",
                    "description": "Standalone agent",
                    "agent_type": "general",
                    "instructions": "# Standalone",
                },
            )

            # Should deploy without errors
            result = template_builder.build_agent_markdown(
                "standalone-agent", agent_file, {}, "test"
            )

            assert result is not None
            assert "# Standalone" in result

    def test_very_deep_nesting_no_base_templates(self, template_builder):
        """Test deeply nested agent without BASE templates at any level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".git").mkdir()

            # Create very deep nesting (8 levels)
            deep_path = repo_root / "a" / "b" / "c" / "d" / "e" / "f" / "g" / "h"
            deep_path.mkdir(parents=True)

            agent_file = deep_path / "deep-agent.md"
            create_agent_json(
                agent_file,
                {
                    "name": "deep-agent",
                    "description": "Deeply nested agent",
                    "agent_type": "general",
                    "instructions": "# Deep Agent",
                },
            )

            # Should complete without errors or excessive scanning
            result = template_builder.build_agent_markdown(
                "deep-agent", agent_file, {}, "test"
            )

            assert result is not None
            assert "# Deep Agent" in result

    def test_repository_without_git_marker(self, template_builder):
        """Test repository without .git directory (depth limit protection)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            # NOTE: No .git directory created

            # Create nested structure
            agents_dir = repo_root / "agents" / "category"
            agents_dir.mkdir(parents=True)

            agent_file = agents_dir / "agent.md"
            create_agent_json(
                agent_file,
                {
                    "name": "agent",
                    "description": "Agent in non-git repo",
                    "agent_type": "general",
                    "instructions": "# Agent",
                },
            )

            # Should complete safely (depth limit prevents infinite loop)
            result = template_builder.build_agent_markdown(
                "agent", agent_file, {}, "test"
            )

            assert result is not None
            assert "# Agent" in result


class TestPerformanceNonCompliantRepos:
    """Test performance characteristics with non-compliant repositories."""

    def test_discovery_performance_no_base_templates(self, template_builder):
        """Verify discovery is fast when no BASE templates exist."""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".git").mkdir()

            # Create moderately deep structure
            deep_path = repo_root / "a" / "b" / "c" / "d" / "e"
            deep_path.mkdir(parents=True)

            agent_file = deep_path / "agent.md"
            agent_file.write_text("# Agent")

            # Measure discovery time
            start = time.time()
            discovered = template_builder._discover_base_agent_templates(agent_file)
            duration = time.time() - start

            # Should be very fast (< 10ms) even with no templates
            assert duration < 0.01  # 10ms
            assert discovered == []

    def test_build_performance_without_composition(self, template_builder):
        """Verify agent building is fast when no composition needed."""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".git").mkdir()

            agent_file = repo_root / "agents" / "agent.md"
            create_agent_json(
                agent_file,
                {
                    "name": "agent",
                    "description": "Test agent",
                    "agent_type": "general",
                    "instructions": "# Agent\n\n"
                    + ("Lorem ipsum\n" * 100),  # Large content
                },
            )

            # Measure build time
            start = time.time()
            result = template_builder.build_agent_markdown(
                "agent", agent_file, {}, "test"
            )
            duration = time.time() - start

            # Should be fast (< 50ms) without composition overhead
            assert duration < 0.05  # 50ms
            assert result is not None
