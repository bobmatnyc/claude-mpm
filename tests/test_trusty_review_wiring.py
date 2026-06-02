"""Tests for first-class trusty-review wiring in mpm (Feature B).

Why: trusty-review is the review-on-demand MCP server backing ``/mpm-review``.
These tests pin the three wiring surfaces that make it first-class: its
``STATIC_MCP_CONFIGS`` entry, its presence in the per-session capability map
(``get_trusty_capabilities``), and the bundled ``mpm-review.md`` command file
that the command-deployment glob picks up. They also guard the security
invariant that NO secrets are baked into the static MCP env.

What: Asserts the static config entry shape (stdio ``serve --stdio`` + non-secret
``env``), that ``get_trusty_capabilities`` reports trusty-review, and that
``src/claude_mpm/commands/mpm-review.md`` exists with valid frontmatter and the
expected behavioral sections.

Test: ``uv run pytest tests/test_trusty_review_wiring.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.mcp.config_builder import MCPServiceConfigBuilder


class TestStaticMcpConfig:
    def test_trusty_review_present(self):
        """trusty-review is a known static MCP config."""
        configs = MCPServiceConfigBuilder.STATIC_MCP_CONFIGS
        assert "trusty-review" in configs

    def test_trusty_review_entry_shape(self):
        """Entry is the stdio serve --stdio form with the cli auth-mode env."""
        entry = MCPServiceConfigBuilder.STATIC_MCP_CONFIGS["trusty-review"]
        assert entry == {
            "type": "stdio",
            "command": "trusty-review",
            "args": ["serve", "--stdio"],
            "env": {"TRUSTY_REVIEW_AUTH_MODE": "cli"},
        }

    def test_trusty_review_env_holds_no_secrets(self):
        """No AWS keys / GITHUB_TOKEN / search index baked into the static env."""
        env = MCPServiceConfigBuilder.STATIC_MCP_CONFIGS["trusty-review"]["env"]
        forbidden = {
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "GITHUB_TOKEN",
            "TRUSTY_SEARCH_INDEX",
        }
        assert forbidden.isdisjoint(env.keys())


class TestCapabilityDetection:
    def test_trusty_review_reported_in_capabilities(self, monkeypatch):
        """get_trusty_capabilities always reports trusty-review's state."""
        from claude_mpm.services import trusty_status

        monkeypatch.setattr(
            trusty_status, "get_trusty_status", lambda _s: ("absent", "")
        )
        caps = trusty_status.get_trusty_capabilities()
        assert "trusty-review" in caps
        assert caps["trusty-review"] == "absent"


class TestMpmReviewCommand:
    COMMAND_PATH = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "commands"
        / "mpm-review.md"
    )

    def test_command_file_exists(self):
        """The bundled command file the deploy glob picks up must exist."""
        assert self.COMMAND_PATH.is_file()

    def test_command_frontmatter_well_formed(self):
        """Frontmatter is a YAML block with the expected command metadata."""
        import yaml

        text = self.COMMAND_PATH.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        _, frontmatter, _body = text.split("---\n", 2)
        meta = yaml.safe_load(frontmatter)
        assert meta["command"] == "review"
        assert "mpm-review" in meta["aliases"]
        assert isinstance(meta.get("description"), str) and meta["description"]

    def test_command_body_documents_health_probe_and_fallback(self):
        """Body must describe the health probe, the trusty-review tools, the
        fallback agent, and the verdict vocabulary."""
        body = self.COMMAND_PATH.read_text(encoding="utf-8")
        assert "mcp__trusty-review__review_health" in body
        assert "mcp__trusty-review__review_diff" in body
        assert "mcp__trusty-review__review_pr" in body
        assert "openrouter-code-reviewer" in body
        for verdict in ("APPROVE", "REQUEST_CHANGES", "BLOCK", "UNKNOWN"):
            assert verdict in body

    def test_command_body_documents_runtime_requirements(self):
        """Body must call out the Bedrock / trusty-search / GITHUB_TOKEN needs."""
        body = self.COMMAND_PATH.read_text(encoding="utf-8")
        assert "Bedrock" in body
        assert "7878" in body  # trusty-search default port
        assert "GITHUB_TOKEN" in body
        assert "TRUSTY_REVIEW_AUTH_MODE=cli" in body
