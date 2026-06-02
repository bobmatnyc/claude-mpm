"""Tests for D3: AgentSkillsInjector graceful no-op when registry absent.

D3 disposition: The skills injection system is inoperative because:
1. config/skills_registry.yaml does not exist.
2. agents/templates/*.json do not exist (agents are now .md files with
   hand-authored skills: frontmatter).
3. AgentSkillsInjector is never instantiated in any runtime code path.

Making injection work requires a large redesign (new registry file, porting
enhance_agent_template to handle .md files, wiring into the deployment
pipeline).

The minimal correctness fix implemented here ensures:
- AgentSkillsInjector warns at construction time when the registry is empty.
- enhance_agent_template() warns and returns {} for .md paths (not raises).
- All enhance/inject methods return empty/unmodified results without raising.
- SkillsService.get_skills_for_agent() returns [] when registry is absent.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.skills.agent_skills_injector import AgentSkillsInjector
from claude_mpm.skills.skills_service import SkillsService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_injector_with_empty_registry() -> AgentSkillsInjector:
    """Build an AgentSkillsInjector whose SkillsService has no registry data."""
    mock_service = MagicMock(spec=SkillsService)
    mock_service.registry = {}  # No agent_skills key — simulates missing registry
    return AgentSkillsInjector(mock_service)


def _make_injector_with_populated_registry(
    agent_id: str, skills: list[str]
) -> AgentSkillsInjector:
    """Build an injector whose service returns skills for a specific agent."""
    mock_service = MagicMock(spec=SkillsService)
    mock_service.registry = {
        "agent_skills": {agent_id: {"required": skills[:2], "optional": skills[2:]}}
    }
    mock_service.get_skills_for_agent.return_value = skills
    return AgentSkillsInjector(mock_service)


# ===========================================================================
# D3: Graceful no-op when registry is absent
# ===========================================================================


class TestAgentSkillsInjectorGracefulNoOp:
    """AgentSkillsInjector must not raise when the registry is absent."""

    def test_construction_with_empty_registry_does_not_raise(self):
        """AgentSkillsInjector can be instantiated even with an empty registry."""
        # Must not raise any exception
        injector = _make_injector_with_empty_registry()
        assert injector is not None

    def test_construction_with_empty_registry_logs_warning(self, caplog):
        """AgentSkillsInjector warns at construction when registry is absent."""
        import logging

        with caplog.at_level(logging.WARNING):
            _make_injector_with_empty_registry()

        # At least one warning should mention the missing registry
        warning_texts = [
            r.message for r in caplog.records if r.levelno >= logging.WARNING
        ]
        assert any(
            "agent_skills" in msg or "registry" in msg.lower() for msg in warning_texts
        ), f"Expected registry-missing warning, got: {warning_texts}"

    def test_enhance_agent_with_skills_returns_empty_when_registry_absent(self):
        """enhance_agent_with_skills no-ops gracefully when registry is empty."""
        injector = _make_injector_with_empty_registry()
        injector.skills_service.get_skills_for_agent.return_value = []

        result = injector.enhance_agent_with_skills(
            "engineer", "---\nname: engineer\n---\n\n# Engineer\n"
        )

        assert result["skills"] == []
        assert result["agent_id"] == "engineer"
        # Content is returned unchanged
        assert "# Engineer" in result["content"]

    def test_get_skills_references_for_agent_returns_empty_when_registry_absent(self):
        """get_skills_references_for_agent returns [] when registry is absent."""
        injector = _make_injector_with_empty_registry()
        injector.skills_service.get_skills_for_agent.return_value = []

        result = injector.get_skills_references_for_agent("engineer")

        assert result == []

    def test_inject_skills_documentation_no_skills_returns_unchanged(self):
        """inject_skills_documentation with empty list returns content unchanged."""
        injector = _make_injector_with_empty_registry()
        original = "---\nname: foo\n---\n\n# Foo\n"

        result = injector.inject_skills_documentation(original, [])

        assert result == original


class TestEnhanceAgentTemplateMdGuard:
    """enhance_agent_template must warn and return {} for .md paths."""

    def test_md_path_returns_empty_dict(self, tmp_path):
        """Passing a .md path returns {} without raising."""
        injector = _make_injector_with_empty_registry()
        md_file = tmp_path / "engineer.md"
        md_file.write_text("---\nname: engineer\n---\n\n# Engineer\n")

        result = injector.enhance_agent_template(md_file)

        assert result == {}, f"Expected empty dict for .md path, got {result!r}"

    def test_md_path_logs_warning(self, tmp_path, caplog):
        """Passing a .md path emits a warning log."""
        import logging

        injector = _make_injector_with_empty_registry()
        md_file = tmp_path / "engineer.md"
        md_file.write_text("---\nname: engineer\n---\n\n# Engineer\n")

        with caplog.at_level(logging.WARNING):
            injector.enhance_agent_template(md_file)

        warning_texts = [
            r.message for r in caplog.records if r.levelno >= logging.WARNING
        ]
        assert any(
            ".md" in msg or "Markdown" in msg or "frontmatter" in msg.lower()
            for msg in warning_texts
        ), f"Expected .md path warning, got: {warning_texts}"

    def test_json_path_still_works_when_registry_populated(self, tmp_path):
        """enhance_agent_template still processes JSON when agent has skills."""
        skills = ["test-driven-development", "systematic-debugging"]
        injector = _make_injector_with_populated_registry("engineer", skills)

        template_data = {"agent_id": "engineer", "name": "Engineer"}
        json_file = tmp_path / "engineer.json"
        json_file.write_text(json.dumps(template_data))

        result = injector.enhance_agent_template(json_file)

        assert result["agent_id"] == "engineer"
        assert "skills" in result
        assert result["skills"]["required"] == skills[:2]

    def test_nonexistent_json_raises(self, tmp_path):
        """enhance_agent_template raises ValueError for missing JSON file."""
        injector = _make_injector_with_empty_registry()
        nonexistent = tmp_path / "missing.json"

        with pytest.raises(ValueError, match="Cannot load template"):
            injector.enhance_agent_template(nonexistent)


class TestSkillsServiceGetSkillsForAgent:
    """SkillsService.get_skills_for_agent() returns [] when registry is absent."""

    def test_returns_empty_list_when_no_agent_skills_key(self):
        """Returns [] when registry dict has no 'agent_skills' key."""
        svc = SkillsService.__new__(SkillsService)
        svc.registry = {}  # No agent_skills

        result = svc.get_skills_for_agent("engineer")

        assert result == []

    def test_returns_empty_list_for_unknown_agent(self):
        """Returns [] when agent_id not in registry."""
        svc = SkillsService.__new__(SkillsService)
        svc.registry = {"agent_skills": {"qa": {"required": ["testing"]}}}

        result = svc.get_skills_for_agent("unknown_agent")

        assert result == []

    def test_returns_combined_required_and_optional(self):
        """Returns required + optional skills for a known agent."""
        svc = SkillsService.__new__(SkillsService)
        svc.registry = {
            "agent_skills": {
                "engineer": {
                    "required": ["tdd", "debugging"],
                    "optional": ["code-review"],
                }
            }
        }

        result = svc.get_skills_for_agent("engineer")

        assert result == ["tdd", "debugging", "code-review"]
