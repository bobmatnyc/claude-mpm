"""Tests for FrameworkLoader._generate_tool_status_section (issue #606).

Why: The per-session "Available Tool Services" block is the runtime override
that stops the PM from calling trusty-* tools that are absent/down this
session. These tests pin its contract: the table renders with the correct
NEGATION lines per unavailable service, a DEGRADED-MODE note appears when all
services are unavailable, and the block injects nothing (empty string) on any
probe error so framework assembly never breaks.

What: Exercises ``_generate_tool_status_section`` against mocked
``get_trusty_capabilities`` return values, plus a backward-compat check that
``ContentFormatter.format_full_framework`` ignores a ``None``
``tool_status_section``.

Test: ``uv run pytest tests/test_framework_loader_tool_status.py``.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services import trusty_status


def _render(monkeypatch, capabilities) -> str:
    """Invoke the section generator with a stubbed capabilities probe.

    ``capabilities`` may be a dict (returned verbatim) or an Exception instance
    (raised) to exercise the fail-safe path. The method only touches
    ``self.logger``, so we bind it to a minimal stub to avoid heavy init.
    """

    def _fake_caps():
        if isinstance(capabilities, Exception):
            raise capabilities
        return capabilities

    monkeypatch.setattr(trusty_status, "get_trusty_capabilities", _fake_caps)
    stub = SimpleNamespace(logger=logging.getLogger("test_tool_status"))
    return FrameworkLoader._generate_tool_status_section(stub)


HEADER = "## Available Tool Services (auto-detected at session start)"


class TestToolStatusSection:
    def test_all_on_renders_table_no_negations_no_degraded(self, monkeypatch):
        """Every service ON → header + table, no skip list, no degraded note."""
        block = _render(
            monkeypatch,
            {
                "trusty-memory": "on",
                "trusty-search": "on",
                "trusty-analyze": "on",
                "trusty-review": "on",
            },
        )
        assert HEADER in block
        assert "| Service | Status | Impact |" in block
        # All four rows render with the ON status label.
        assert block.count("| ON |") == 4
        assert "| trusty-memory | ON |" in block
        assert "| trusty-review | ON |" in block
        # No service is unavailable → no skip list and no negations.
        assert "Skip the following this session" not in block
        assert "is NOT" not in block
        assert "DEGRADED MODE" not in block

    def test_memory_absent_has_explicit_negation(self, monkeypatch):
        """An absent service gets an explicit NOT-available negation line."""
        block = _render(
            monkeypatch,
            {
                "trusty-memory": "absent",
                "trusty-search": "on",
                "trusty-analyze": "on",
                "trusty-review": "on",
            },
        )
        assert "| trusty-memory | ABSENT |" in block
        assert "trusty-memory is NOT" in block
        assert "SKIP all `mcp__trusty-memory__*` calls" in block
        assert "Skip the following this session" in block
        # Not all unavailable → no degraded-mode banner.
        assert "DEGRADED MODE" not in block

    def test_not_running_labeled_not_running(self, monkeypatch):
        """``configured`` and ``not_running`` both render as NOT RUNNING."""
        block = _render(
            monkeypatch,
            {
                "trusty-memory": "configured",
                "trusty-search": "not_running",
                "trusty-analyze": "on",
                "trusty-review": "on",
            },
        )
        assert "| trusty-memory | NOT RUNNING |" in block
        assert "| trusty-search | NOT RUNNING |" in block

    def test_all_absent_emits_degraded_mode(self, monkeypatch):
        """All services unavailable → DEGRADED MODE note present."""
        block = _render(
            monkeypatch,
            {
                "trusty-memory": "absent",
                "trusty-search": "absent",
                "trusty-analyze": "absent",
                "trusty-review": "absent",
            },
        )
        assert HEADER in block
        assert "DEGRADED MODE" in block
        assert "delegate directly to" in block
        # Each service still gets its negation line.
        assert "trusty-memory is NOT" in block
        assert "trusty-search is NOT" in block

    def test_probe_error_injects_nothing(self, monkeypatch):
        """A raising probe yields an empty string (nothing injected)."""
        block = _render(monkeypatch, RuntimeError("probe exploded"))
        assert block == ""

    def test_empty_capabilities_injects_nothing(self, monkeypatch):
        """An empty capabilities map yields an empty string."""
        block = _render(monkeypatch, {})
        assert block == ""


class TestContentFormatterBackwardCompat:
    def test_none_tool_status_section_is_noop(self):
        """format_full_framework must stay backward-compatible: passing
        tool_status_section=None injects nothing and does not raise."""
        from claude_mpm.core.framework.formatters.content_formatter import (
            ContentFormatter,
        )

        formatter = ContentFormatter()
        framework_content = {"framework_instructions": "# Base instructions\n"}
        with_none = formatter.format_full_framework(
            framework_content,
            "CAPS",
            "CTX",
            False,
            None,
            None,
        )
        without_arg = formatter.format_full_framework(
            framework_content,
            "CAPS",
            "CTX",
            False,
            None,
        )
        assert with_none == without_arg
        assert "Available Tool Services" not in with_none

    def test_tool_status_section_appended_when_provided(self):
        """When a block is supplied it appears in the assembled output."""
        from claude_mpm.core.framework.formatters.content_formatter import (
            ContentFormatter,
        )

        formatter = ContentFormatter()
        block = "\n\n## Available Tool Services (auto-detected at session start)\n"
        out = formatter.format_full_framework(
            {"framework_instructions": "# Base instructions\n"},
            "CAPS",
            "CTX",
            False,
            None,
            block,
        )
        assert "Available Tool Services" in out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
