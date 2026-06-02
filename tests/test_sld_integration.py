"""
tests/test_sld_integration.py — Integration tests for the SLD config wiring.

WHAT: Proves end-to-end that calling build_agent_markdown() on an engineer or
documentation agent with the SLD flag ON produces output containing the SLD
instruction block, and that ops/qa agents do NOT receive it.  Also verifies
that with the flag OFF no agent gets the block.

WHY: The unit tests in test_sld_config.py already cover the helper functions
in isolation.  These integration tests validate the *call path* — from
AgentTemplateBuilder.build_agent_markdown() through
get_sld_instruction_for_agent() — using the real builder with real template
files, not mocks of the function under test.

The _StubConfig helper mirrors the one in test_sld_config.py so tests remain
independent of the real Config singleton.
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003  # used at runtime in helper functions

import pytest

from claude_mpm.config.sld_config import (
    SLD_TARGET_AGENT_TYPES,
    get_sld_instruction_block,
    is_sld_target_agent_type,
)
from claude_mpm.services.agents.deployment.agent_template_builder import (
    AgentTemplateBuilder,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _StubConfig:
    """Minimal Config stub — dot-notation key lookup over a plain dict."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


def _sld_on() -> _StubConfig:
    return _StubConfig({"workflow": {"spec_linked_docs": {"enabled": True}}})


def _sld_off() -> _StubConfig:
    return _StubConfig({"workflow": {"spec_linked_docs": {"enabled": False}}})


def _make_template(tmp_path: Path, agent_type: str, agent_name: str) -> Path:
    """Write a minimal JSON agent template and return its path."""
    data = {
        "name": agent_name,
        "description": f"Test {agent_type} agent",
        "version": "1.0.0",
        "agent_type": agent_type,
        "model": "sonnet",
        "tools": ["Read", "Write"],
    }
    p = tmp_path / f"{agent_name}.json"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


def _make_md_template(tmp_path: Path, agent_type: str, agent_name: str) -> Path:
    """Write a minimal Markdown agent template and return its path."""
    content = f"""\
---
name: {agent_name}
description: Test {agent_type} agent
version: "1.0.0"
agent_type: {agent_type}
model: sonnet
---

# {agent_name.title()} Agent

This is the instruction body.
"""
    p = tmp_path / f"{agent_name}.md"
    p.write_text(content, encoding="utf-8")
    return p


BASE_AGENT_DATA = {
    "content": "# Base Agent\n\nCore functionality.",
    "configuration_fields": {"model": "sonnet", "tools": ["Read", "Write"]},
}

# ---------------------------------------------------------------------------
# Tests: is_sld_target_agent_type (unit, standalone helper)
# ---------------------------------------------------------------------------


class TestIsSldTargetAgentType:
    """Unit tests for the is_sld_target_agent_type() classifier."""

    def test_engineer_is_target(self):
        assert is_sld_target_agent_type("engineer") is True

    def test_documentation_is_target(self):
        assert is_sld_target_agent_type("documentation") is True

    def test_qa_is_not_target(self):
        assert is_sld_target_agent_type("qa") is False

    def test_ops_is_not_target(self):
        assert is_sld_target_agent_type("ops") is False

    def test_research_is_not_target(self):
        assert is_sld_target_agent_type("research") is False

    def test_security_is_not_target(self):
        assert is_sld_target_agent_type("security") is False

    def test_empty_string_is_not_target(self):
        assert is_sld_target_agent_type("") is False

    # Suffix / hyphenated variants (defensive rule)
    def test_python_engineer_suffix_match(self):
        assert is_sld_target_agent_type("python-engineer") is True

    def test_react_engineer_suffix_match(self):
        assert is_sld_target_agent_type("react-engineer") is True

    def test_api_documentation_suffix_match(self):
        assert is_sld_target_agent_type("api-documentation") is True

    def test_partial_match_does_not_trigger(self):
        # "researcher" is NOT "research" and does not end with "-engineer"
        assert is_sld_target_agent_type("researcher") is False

    def test_engineer_category_in_target_types(self):
        """SLD_TARGET_AGENT_TYPES itself contains engineer and documentation."""
        assert "engineer" in SLD_TARGET_AGENT_TYPES
        assert "documentation" in SLD_TARGET_AGENT_TYPES


# ---------------------------------------------------------------------------
# Tests: build_agent_markdown — JSON template
# ---------------------------------------------------------------------------


class TestBuildAgentMarkdownSLDInjection:
    """Integration: build_agent_markdown injects SLD block correctly."""

    # --- Flag ON, engineer agent ---

    def test_engineer_json_receives_sld_block_when_flag_on(self, tmp_path):
        """Engineer agent output contains the SLD instruction block when flag is on."""
        template_file = _make_template(tmp_path, "engineer", "test-engineer")
        builder = AgentTemplateBuilder(config=_sld_on())

        result = builder.build_agent_markdown(
            agent_name="test-engineer",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        sld_block = get_sld_instruction_block()
        assert sld_block.strip() in result, (
            "SLD instruction block should appear in engineer output when flag is on"
        )

    def test_documentation_json_receives_sld_block_when_flag_on(self, tmp_path):
        """Documentation agent output contains the SLD block when flag is on."""
        template_file = _make_template(tmp_path, "documentation", "test-docs")
        builder = AgentTemplateBuilder(config=_sld_on())

        result = builder.build_agent_markdown(
            agent_name="test-docs",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        assert "Spec-Linked Documentation" in result, (
            "SLD instruction text should appear in documentation agent output"
        )

    # --- Flag ON, non-target agent types ---

    def test_ops_does_not_receive_sld_block_when_flag_on(self, tmp_path):
        """Ops agent output does NOT contain the SLD block even when flag is on."""
        template_file = _make_template(tmp_path, "ops", "test-ops")
        builder = AgentTemplateBuilder(config=_sld_on())

        result = builder.build_agent_markdown(
            agent_name="test-ops",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        sld_block = get_sld_instruction_block()
        assert sld_block.strip() not in result, (
            "SLD instruction block must NOT appear in ops agent output"
        )

    def test_qa_does_not_receive_sld_block_when_flag_on(self, tmp_path):
        """QA agent output does NOT contain the SLD block."""
        template_file = _make_template(tmp_path, "qa", "test-qa")
        builder = AgentTemplateBuilder(config=_sld_on())

        result = builder.build_agent_markdown(
            agent_name="test-qa",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        assert "Spec-Linked Documentation" not in result

    def test_research_does_not_receive_sld_block_when_flag_on(self, tmp_path):
        """Research agent output does NOT contain the SLD block."""
        template_file = _make_template(tmp_path, "research", "test-research")
        builder = AgentTemplateBuilder(config=_sld_on())

        result = builder.build_agent_markdown(
            agent_name="test-research",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        assert "Spec-Linked Documentation" not in result

    # --- Flag OFF, all agent types ---

    def test_engineer_does_not_receive_sld_block_when_flag_off(self, tmp_path):
        """Engineer agent output does NOT contain SLD block when flag is off."""
        template_file = _make_template(tmp_path, "engineer", "test-engineer")
        builder = AgentTemplateBuilder(config=_sld_off())

        result = builder.build_agent_markdown(
            agent_name="test-engineer",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        assert "Spec-Linked Documentation" not in result, (
            "SLD instruction block must NOT appear when flag is off"
        )

    def test_documentation_does_not_receive_sld_block_when_flag_off(self, tmp_path):
        """Documentation agent output does NOT contain SLD block when flag is off."""
        template_file = _make_template(tmp_path, "documentation", "test-docs")
        builder = AgentTemplateBuilder(config=_sld_off())

        result = builder.build_agent_markdown(
            agent_name="test-docs",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        assert "Spec-Linked Documentation" not in result

    # --- No config (config=None) — backward compatible ---

    def test_engineer_does_not_receive_sld_block_when_no_config(self, tmp_path):
        """Builder with config=None is backward-compatible — no SLD injection."""
        template_file = _make_template(tmp_path, "engineer", "test-engineer")
        builder = AgentTemplateBuilder(config=None)

        result = builder.build_agent_markdown(
            agent_name="test-engineer",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        # With no config, is_sld_enabled() falls back to False
        assert "Spec-Linked Documentation" not in result, (
            "No SLD block with config=None (backward compat)"
        )


# ---------------------------------------------------------------------------
# Tests: build_agent_markdown — Markdown template (same assertions)
# ---------------------------------------------------------------------------


class TestBuildAgentMarkdownSLDInjectionMarkdown:
    """Same assertions for Markdown (.md) template files."""

    def test_engineer_md_receives_sld_block_when_flag_on(self, tmp_path):
        template_file = _make_md_template(tmp_path, "engineer", "test-engineer")
        builder = AgentTemplateBuilder(config=_sld_on())

        result = builder.build_agent_markdown(
            agent_name="test-engineer",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        assert "Spec-Linked Documentation" in result

    def test_ops_md_does_not_receive_sld_block_when_flag_on(self, tmp_path):
        template_file = _make_md_template(tmp_path, "ops", "test-ops")
        builder = AgentTemplateBuilder(config=_sld_on())

        result = builder.build_agent_markdown(
            agent_name="test-ops",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        assert "Spec-Linked Documentation" not in result

    def test_engineer_md_no_sld_when_flag_off(self, tmp_path):
        template_file = _make_md_template(tmp_path, "engineer", "test-engineer")
        builder = AgentTemplateBuilder(config=_sld_off())

        result = builder.build_agent_markdown(
            agent_name="test-engineer",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        assert "Spec-Linked Documentation" not in result


# ---------------------------------------------------------------------------
# Tests: output format — SLD block appears after main content
# ---------------------------------------------------------------------------


class TestSldBlockPosition:
    """Verify the SLD block is appended after the main content, not prepended."""

    def test_sld_block_appended_after_frontmatter_and_content(self, tmp_path):
        """SLD block must come after the YAML frontmatter separator and main body."""
        template_file = _make_template(tmp_path, "engineer", "test-engineer")
        builder = AgentTemplateBuilder(config=_sld_on())

        result = builder.build_agent_markdown(
            agent_name="test-engineer",
            template_path=template_file,
            base_agent_data=BASE_AGENT_DATA,
        )

        sld_phrase = "Spec-Linked Documentation"
        sld_pos = result.find(sld_phrase)
        yaml_end_pos = result.find("---\n\n")  # end of YAML frontmatter

        assert sld_pos != -1, "SLD phrase must be present"
        assert yaml_end_pos != -1, "Frontmatter closing --- must be present"
        assert sld_pos > yaml_end_pos, "SLD block must come after frontmatter"
