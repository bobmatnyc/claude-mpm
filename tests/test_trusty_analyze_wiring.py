"""Tests for first-class trusty-analyze wiring in mpm (GitHub #782).

Why: trusty-analyze is the code-analysis sidecar daemon.  These tests pin the
three wiring surfaces that make it first-class: its ``STATIC_MCP_CONFIGS``
entry (key renamed from ``trusty-analyzer`` → ``trusty-analyze``), its
presence in the per-session capability map (``get_trusty_capabilities``), and
the correct stdio invocation (``trusty-analyze mcp``).

What: Asserts the static config entry shape (stdio ``mcp`` subcommand, no
``env`` key required), that ``get_trusty_capabilities`` reports trusty-analyze,
and that the MCP config key is ``trusty-analyze`` (not the old
``trusty-analyzer``).

Test: ``uv run pytest tests/test_trusty_analyze_wiring.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.mcp.config_builder import MCPServiceConfigBuilder


class TestStaticMcpConfig:
    def test_trusty_analyze_present(self):
        """trusty-analyze is a known static MCP config (renamed from trusty-analyzer)."""
        configs = MCPServiceConfigBuilder.STATIC_MCP_CONFIGS
        assert "trusty-analyze" in configs

    def test_trusty_analyzer_old_key_absent(self):
        """Old key ``trusty-analyzer`` must NOT appear in STATIC_MCP_CONFIGS."""
        configs = MCPServiceConfigBuilder.STATIC_MCP_CONFIGS
        assert "trusty-analyzer" not in configs

    def test_trusty_analyze_entry_shape(self):
        """Entry is the stdio ``mcp`` subcommand form (confirmed by trusty-analyze --help)."""
        entry = MCPServiceConfigBuilder.STATIC_MCP_CONFIGS["trusty-analyze"]
        assert entry["type"] == "stdio"
        assert entry["command"] == "trusty-analyze"
        assert entry["args"] == ["mcp"]

    def test_trusty_analyze_no_secret_env(self):
        """No secrets baked into the static entry (env key is absent or empty)."""
        entry = MCPServiceConfigBuilder.STATIC_MCP_CONFIGS["trusty-analyze"]
        env = entry.get("env", {})
        forbidden = {
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "GITHUB_TOKEN",
        }
        assert forbidden.isdisjoint(env.keys())


class TestCapabilityDetection:
    def test_trusty_analyze_reported_in_capabilities(self, monkeypatch):
        """get_trusty_capabilities always reports trusty-analyze's state."""
        from claude_mpm.services import trusty_status

        monkeypatch.setattr(
            trusty_status, "get_trusty_status", lambda _s: ("absent", "")
        )
        caps = trusty_status.get_trusty_capabilities()
        assert "trusty-analyze" in caps
        assert caps["trusty-analyze"] == "absent"

    def test_trusty_analyzer_old_key_not_in_capabilities(self, monkeypatch):
        """Old key ``trusty-analyzer`` must NOT appear in capabilities output."""
        from claude_mpm.services import trusty_status

        monkeypatch.setattr(
            trusty_status, "get_trusty_status", lambda _s: ("absent", "")
        )
        caps = trusty_status.get_trusty_capabilities()
        assert "trusty-analyzer" not in caps
