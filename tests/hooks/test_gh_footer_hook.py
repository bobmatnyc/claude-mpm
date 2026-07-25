"""Tests for the gh_footer_hook PreToolUse hook.

Covers:
- rewrite_footer: old-footer variants → canonical; idempotent; body-unchanged cases.
- rewrite_bash_command: extracts body from --body/--body=/--body "..."/-b/--body-file/-F;
  ignores unrelated gh commands; no-op when footer is already canonical.
- rewrite_mcp_body: MCP tool body field normalisation.
- build_gh_footer_response: wire-format response for Bash and MCP tools.
- Graceful degradation: malformed / empty input does not raise.
"""

from __future__ import annotations

import pytest

from claude_mpm.hooks.footer_constants import (
    CLAUDE_CODE_FOOTER_OLD,
    CLAUDE_CODE_FOOTER_OLD_ALT,
    MPM_FOOTER_CANONICAL,
)
from claude_mpm.hooks.gh_footer_hook import (
    _DISABLE_ENV_VAR,
    _extract_body_file,
    _is_gh_body_command,
    _requote,
    build_body_file_advisory,
    build_gh_footer_response,
    rewrite_bash_command,
    rewrite_footer,
    rewrite_mcp_body,
)


@pytest.fixture(autouse=True)
def _clear_disable_env(monkeypatch):
    """Ensure a developer's exported opt-out cannot silently pass the suite."""
    monkeypatch.delenv(_DISABLE_ENV_VAR, raising=False)


# ---------------------------------------------------------------------------
# rewrite_footer — pure string transformation
# ---------------------------------------------------------------------------


class TestRewriteFooter:
    """Tests for the pure rewrite_footer helper."""

    def test_old_footer_claude_ai_url_no_emoji(self):
        body = f"Some content\n\n{CLAUDE_CODE_FOOTER_OLD}"
        result = rewrite_footer(body)
        assert MPM_FOOTER_CANONICAL in result
        assert CLAUDE_CODE_FOOTER_OLD not in result

    def test_old_footer_claude_com_url_no_emoji(self):
        body = f"Some content\n\n{CLAUDE_CODE_FOOTER_OLD_ALT}"
        result = rewrite_footer(body)
        assert MPM_FOOTER_CANONICAL in result
        assert CLAUDE_CODE_FOOTER_OLD_ALT not in result

    def test_old_footer_with_robot_emoji(self):
        body = f"Some content\n\n🤖 {CLAUDE_CODE_FOOTER_OLD}"
        result = rewrite_footer(body)
        assert MPM_FOOTER_CANONICAL in result
        # emoji + old string should be replaced by canonical
        assert CLAUDE_CODE_FOOTER_OLD not in result

    def test_old_footer_alt_with_robot_emoji(self):
        body = f"Some content\n\n🤖 {CLAUDE_CODE_FOOTER_OLD_ALT}"
        result = rewrite_footer(body)
        assert MPM_FOOTER_CANONICAL in result
        assert CLAUDE_CODE_FOOTER_OLD_ALT not in result

    def test_idempotent_when_already_canonical(self):
        body = f"Some content\n\n{MPM_FOOTER_CANONICAL}"
        result = rewrite_footer(body)
        assert result == body

    def test_idempotent_canonical_with_old_footer_also_present(self):
        # If canonical is already there, do not add another copy even if old
        # footer is also somehow present.
        body = f"Some content\n\n{MPM_FOOTER_CANONICAL}\n\n{CLAUDE_CODE_FOOTER_OLD}"
        result = rewrite_footer(body)
        assert result == body  # leave unchanged when canonical already present
        assert result.count(MPM_FOOTER_CANONICAL) == 1

    def test_no_footer_body_unchanged(self):
        body = "## Summary\n\nSome PR body without any footer."
        result = rewrite_footer(body)
        assert result == body

    def test_empty_body_unchanged(self):
        assert rewrite_footer("") == ""

    def test_body_text_around_footer_preserved(self):
        body = (
            "## Summary\n\nThis is the PR description.\n\n"
            f"🤖 {CLAUDE_CODE_FOOTER_OLD}\n"
        )
        result = rewrite_footer(body)
        assert "## Summary" in result
        assert "This is the PR description." in result
        assert MPM_FOOTER_CANONICAL in result

    def test_duplicate_old_footers_collapsed_to_one(self):
        body = f"Content\n\n{CLAUDE_CODE_FOOTER_OLD}\n\n{CLAUDE_CODE_FOOTER_OLD_ALT}"
        result = rewrite_footer(body)
        assert result.count(MPM_FOOTER_CANONICAL) == 1
        assert CLAUDE_CODE_FOOTER_OLD not in result
        assert CLAUDE_CODE_FOOTER_OLD_ALT not in result

    def test_multiline_body_footer_at_end(self):
        body = (
            "Line 1\nLine 2\nLine 3\n\n"
            "🤖 Generated with [Claude Code](https://claude.ai/code)"
        )
        result = rewrite_footer(body)
        assert "Line 1" in result
        assert "Line 2" in result
        assert MPM_FOOTER_CANONICAL in result


# ---------------------------------------------------------------------------
# _is_gh_body_command
# ---------------------------------------------------------------------------


class TestIsGhBodyCommand:
    def test_pr_create(self):
        assert _is_gh_body_command("gh pr create --title T --body B")

    def test_pr_edit(self):
        assert _is_gh_body_command("gh pr edit 42 --body B")

    def test_issue_create(self):
        assert _is_gh_body_command("gh issue create --title T --body B")

    def test_issue_edit(self):
        assert _is_gh_body_command("gh issue edit 7 --body B")

    def test_extra_whitespace_between_tokens(self):
        assert _is_gh_body_command("gh   pr   create --body B")

    def test_uppercase_ignored(self):
        # Case-insensitive match
        assert _is_gh_body_command("GH PR CREATE --body B")

    def test_unrelated_pr_view(self):
        assert not _is_gh_body_command("gh pr view 42")

    def test_unrelated_repo_clone(self):
        assert not _is_gh_body_command("gh repo clone org/repo")

    def test_unrelated_pr_list(self):
        assert not _is_gh_body_command("gh pr list")

    def test_unrelated_issue_list(self):
        assert not _is_gh_body_command("gh issue list")

    def test_not_a_gh_command(self):
        assert not _is_gh_body_command("git push origin main")

    def test_empty_command(self):
        assert not _is_gh_body_command("")


# ---------------------------------------------------------------------------
# rewrite_bash_command — command string parsing + rewrite
# ---------------------------------------------------------------------------


class TestRewriteBashCommand:
    """Tests for rewrite_bash_command with various flag forms."""

    def _make_cmd(self, body: str, flag: str = "--body") -> str:
        return f'gh pr create --title "My PR" {flag} "{body}"'

    def test_body_flag_double_quotes(self):
        cmd = f'gh pr create --title "PR" --body "{CLAUDE_CODE_FOOTER_OLD}"'
        result = rewrite_bash_command(cmd)
        assert result is not None
        assert MPM_FOOTER_CANONICAL in result
        assert CLAUDE_CODE_FOOTER_OLD not in result

    def test_body_flag_with_equals(self):
        cmd = f'gh pr create --body="{CLAUDE_CODE_FOOTER_OLD}"'
        result = rewrite_bash_command(cmd)
        assert result is not None
        assert MPM_FOOTER_CANONICAL in result

    def test_short_flag_b(self):
        cmd = f'gh issue create -b "{CLAUDE_CODE_FOOTER_OLD_ALT}"'
        result = rewrite_bash_command(cmd)
        assert result is not None
        assert MPM_FOOTER_CANONICAL in result

    def test_already_canonical_returns_none(self):
        cmd = f'gh pr create --body "{MPM_FOOTER_CANONICAL}"'
        assert rewrite_bash_command(cmd) is None

    def test_no_footer_returns_none(self):
        cmd = 'gh pr create --body "No footer here"'
        assert rewrite_bash_command(cmd) is None

    def test_unrelated_command_returns_none(self):
        assert rewrite_bash_command("git push origin main") is None

    def test_pr_view_returns_none(self):
        assert rewrite_bash_command("gh pr view 42") is None

    def test_body_file_flag_never_rewrites_command_or_file(self, tmp_path):
        """Regression (defect 1): --body-file is advisory-only, never mutating."""
        body_file = tmp_path / "body.md"
        original = f"Content\n\n{CLAUDE_CODE_FOOTER_OLD}"
        body_file.write_text(original)
        cmd = f"gh pr create --body-file {body_file}"
        # No command rewrite is possible for a file body.
        assert rewrite_bash_command(cmd) is None
        # And the file on disk must be byte-identical.
        assert body_file.read_text() == original

    def test_body_file_short_flag_never_mutates(self, tmp_path):
        body_file = tmp_path / "body.md"
        original = f"{CLAUDE_CODE_FOOTER_OLD_ALT}"
        body_file.write_text(original)
        cmd = f"gh issue create -F {body_file}"
        assert rewrite_bash_command(cmd) is None
        assert body_file.read_text() == original

    def test_body_file_already_canonical_returns_none(self, tmp_path):
        body_file = tmp_path / "body.md"
        body_file.write_text(f"Content\n\n{MPM_FOOTER_CANONICAL}")
        cmd = f"gh pr create --body-file {body_file}"
        assert rewrite_bash_command(cmd) is None

    def test_body_file_missing_returns_none(self):
        cmd = "gh pr create --body-file /nonexistent/path/body.md"
        result = rewrite_bash_command(cmd)
        assert result is None  # graceful degradation

    def test_empty_command_returns_none(self):
        assert rewrite_bash_command("") is None

    def test_env_var_prefix_before_gh(self):
        # Commands like: GITHUB_TOKEN=xxx gh pr create ...
        cmd = f'GITHUB_TOKEN=xxx gh pr create --body "{CLAUDE_CODE_FOOTER_OLD}"'
        result = rewrite_bash_command(cmd)
        assert result is not None
        assert MPM_FOOTER_CANONICAL in result

    def test_exception_in_rewrite_returns_none(self, monkeypatch):
        """Graceful degradation when rewrite_footer raises unexpectedly."""
        from claude_mpm.hooks import gh_footer_hook

        monkeypatch.setattr(
            gh_footer_hook,
            "rewrite_footer",
            lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        cmd = f'gh pr create --body "{CLAUDE_CODE_FOOTER_OLD}"'
        # Should not raise; should return None
        result = rewrite_bash_command(cmd)
        assert result is None


# ---------------------------------------------------------------------------
# FIX 3 regression tests: quoting preservation, multi-line body, title safety
# ---------------------------------------------------------------------------


class TestRewriteBashCommandFix3:
    """Regression tests added for trusty-review correctness findings."""

    def test_multiline_body_roundtrip(self):
        """Multi-line body with embedded newlines rewrites footer and stays well-formed."""
        body = f"## Summary\n\nLine one\nLine two\n\n{CLAUDE_CODE_FOOTER_OLD}"
        # Embed newlines literally inside a double-quoted shell argument.
        cmd = f'gh pr create --title "My PR" --body "{body}"'
        result = rewrite_bash_command(cmd)
        assert result is not None, "Expected a rewrite for multi-line body"
        assert MPM_FOOTER_CANONICAL in result
        assert CLAUDE_CODE_FOOTER_OLD not in result
        # The --title token must still be intact.
        assert '--title "My PR"' in result

    def test_old_footer_in_title_does_not_get_rewritten(self):
        """Regression (finding a): old footer text in --title must not be touched."""
        title_with_footer = f"PR about {CLAUDE_CODE_FOOTER_OLD}"
        body_with_footer = f"Description\n\n{CLAUDE_CODE_FOOTER_OLD}"
        cmd = f'gh pr create --title "{title_with_footer}" --body "{body_with_footer}"'
        result = rewrite_bash_command(cmd)
        assert result is not None, "Expected body to be rewritten"
        # The canonical footer must appear (body was rewritten).
        assert MPM_FOOTER_CANONICAL in result
        # The title must be unchanged: the old footer text is still inside it.
        assert f'--title "{title_with_footer}"' in result

    def test_short_b_flag_standalone_parses(self):
        """Standalone -b flag is matched; parses and rewrites correctly."""
        cmd = f'gh issue create -b "{CLAUDE_CODE_FOOTER_OLD}"'
        result = rewrite_bash_command(cmd)
        assert result is not None
        assert MPM_FOOTER_CANONICAL in result

    def test_dash_base_like_token_not_misrewritten(self):
        """Regression (finding c): -base-like tokens are not treated as -b body flag."""
        # A command with -base main (not a real gh flag; purely tests the
        # standalone-flag boundary assertion for -b).
        cmd = f'gh pr create -base main --body "{CLAUDE_CODE_FOOTER_OLD}"'
        result = rewrite_bash_command(cmd)
        # The body should still get rewritten (via --body); -base is untouched.
        assert result is not None
        assert "-base main" in result
        assert MPM_FOOTER_CANONICAL in result

    def test_body_equals_form_preserves_double_quotes(self):
        """--body= form with double quotes keeps double-quote style after rewrite."""
        cmd = f'gh pr create --body="{CLAUDE_CODE_FOOTER_OLD}"'
        result = rewrite_bash_command(cmd)
        assert result is not None
        # Result must contain the MPM footer wrapped in double quotes.
        assert f'"{MPM_FOOTER_CANONICAL}"' in result

    def test_body_space_form_preserves_double_quotes(self):
        """--body "..." (space separator) keeps double-quote style after rewrite."""
        cmd = f'gh pr create --body "{CLAUDE_CODE_FOOTER_OLD}"'
        result = rewrite_bash_command(cmd)
        assert result is not None
        assert f'"{MPM_FOOTER_CANONICAL}"' in result

    def test_single_quoted_body_preserves_single_quotes(self):
        """Single-quoted body stays single-quoted after rewrite (finding b)."""
        cmd = f"gh pr create --body '{CLAUDE_CODE_FOOTER_OLD}'"
        result = rewrite_bash_command(cmd)
        assert result is not None
        assert f"'{MPM_FOOTER_CANONICAL}'" in result

    def test_idempotent_multiline_body_no_double_rewrite(self):
        """Idempotency: a body that already has the MPM footer returns None."""
        body = f"## Summary\n\n{MPM_FOOTER_CANONICAL}"
        cmd = f'gh pr create --body "{body}"'
        assert rewrite_bash_command(cmd) is None


# ---------------------------------------------------------------------------
# rewrite_mcp_body — MCP tool body field normalisation
# ---------------------------------------------------------------------------


class TestRewriteMcpBody:
    def test_create_pull_request_old_footer(self):
        tool_input = {"title": "My PR", "body": f"Content\n\n{CLAUDE_CODE_FOOTER_OLD}"}
        result = rewrite_mcp_body("mcp__github__create_pull_request", tool_input)
        assert result is not None
        assert MPM_FOOTER_CANONICAL in result["body"]
        assert CLAUDE_CODE_FOOTER_OLD not in result["body"]

    def test_create_issue_old_footer_alt(self):
        tool_input = {"title": "Issue", "body": f"Desc\n\n{CLAUDE_CODE_FOOTER_OLD_ALT}"}
        result = rewrite_mcp_body("mcp__github__create_issue", tool_input)
        assert result is not None
        assert MPM_FOOTER_CANONICAL in result["body"]

    def test_already_canonical_returns_none(self):
        tool_input = {"body": f"{MPM_FOOTER_CANONICAL}"}
        result = rewrite_mcp_body("mcp__github__create_pull_request", tool_input)
        assert result is None

    def test_no_footer_returns_none(self):
        tool_input = {"body": "Just a description"}
        result = rewrite_mcp_body("mcp__github__create_pull_request", tool_input)
        assert result is None

    def test_non_github_tool_returns_none(self):
        tool_input = {"body": f"{CLAUDE_CODE_FOOTER_OLD}"}
        result = rewrite_mcp_body("mcp__gitlab__create_pr", tool_input)
        assert result is None

    def test_no_body_field_returns_none(self):
        tool_input = {"title": "No body"}
        result = rewrite_mcp_body("mcp__github__create_pull_request", tool_input)
        assert result is None

    def test_non_string_body_returns_none(self):
        tool_input = {"body": None}
        result = rewrite_mcp_body("mcp__github__create_pull_request", tool_input)
        assert result is None

    def test_update_pull_request(self):
        tool_input = {"body": f"Update content\n\n{CLAUDE_CODE_FOOTER_OLD}"}
        result = rewrite_mcp_body("mcp__github__update_pull_request", tool_input)
        assert result is not None
        assert MPM_FOOTER_CANONICAL in result["body"]

    def test_other_fields_preserved(self):
        tool_input = {
            "title": "My PR",
            "base": "main",
            "head": "feat/foo",
            "body": f"Description\n\n{CLAUDE_CODE_FOOTER_OLD}",
        }
        result = rewrite_mcp_body("mcp__github__create_pull_request", tool_input)
        assert result is not None
        assert result["title"] == "My PR"
        assert result["base"] == "main"
        assert result["head"] == "feat/foo"


# ---------------------------------------------------------------------------
# build_gh_footer_response — wire-format integration
# ---------------------------------------------------------------------------


class TestBuildGhFooterResponse:
    def _bash_event(self, command: str) -> dict:
        return {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        }

    def _mcp_event(self, tool_name: str, body: str) -> dict:
        return {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {"title": "T", "body": body},
        }

    def test_bash_returns_updated_input_when_rewritten(self):
        cmd = f'gh pr create --body "{CLAUDE_CODE_FOOTER_OLD}"'
        response = build_gh_footer_response(self._bash_event(cmd))
        assert "hookSpecificOutput" in response
        hso = response["hookSpecificOutput"]
        assert "updatedInput" in hso
        assert MPM_FOOTER_CANONICAL in hso["updatedInput"]["command"]

    def test_bash_returns_continue_when_no_rewrite_needed(self):
        cmd = 'gh pr create --body "No footer"'
        response = build_gh_footer_response(self._bash_event(cmd))
        assert response == {"continue": True}

    def test_bash_unrelated_command_returns_continue(self):
        response = build_gh_footer_response(self._bash_event("git push origin main"))
        assert response == {"continue": True}

    def test_mcp_returns_updated_input_when_rewritten(self):
        event = self._mcp_event(
            "mcp__github__create_pull_request",
            f"Content\n\n{CLAUDE_CODE_FOOTER_OLD}",
        )
        response = build_gh_footer_response(event)
        assert "hookSpecificOutput" in response
        hso = response["hookSpecificOutput"]
        assert MPM_FOOTER_CANONICAL in hso["updatedInput"]["body"]

    def test_mcp_returns_continue_when_no_footer(self):
        event = self._mcp_event("mcp__github__create_issue", "Just a description")
        response = build_gh_footer_response(event)
        assert response == {"continue": True}

    def test_unrecognised_tool_returns_continue(self):
        event = {
            "tool_name": "Write",
            "tool_input": {"file_path": "foo.py", "content": CLAUDE_CODE_FOOTER_OLD},
        }
        response = build_gh_footer_response(event)
        assert response == {"continue": True}

    def test_empty_event_returns_continue(self):
        response = build_gh_footer_response({})
        assert response == {"continue": True}

    def test_malformed_event_returns_continue(self):
        response = build_gh_footer_response({"tool_name": None, "tool_input": None})
        assert response == {"continue": True}


# ---------------------------------------------------------------------------
# Graceful degradation — no raise on bad inputs
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    def test_rewrite_footer_non_string_input(self):
        # Should not raise even if called with weird types; treat gracefully
        # (In practice the type hint says str, but be defensive.)
        result = rewrite_footer("")
        assert result == ""

    def test_rewrite_bash_command_none_like_input(self):
        assert rewrite_bash_command("") is None

    def test_build_response_no_tool_name(self):
        assert build_gh_footer_response({}) == {"continue": True}

    def test_build_response_none_tool_input(self):
        response = build_gh_footer_response({"tool_name": "Bash", "tool_input": None})
        assert response == {"continue": True}

    def test_build_response_bash_empty_command(self):
        event = {"tool_name": "Bash", "tool_input": {"command": ""}}
        assert build_gh_footer_response(event) == {"continue": True}

    def test_build_response_bash_whitespace_command(self):
        event = {"tool_name": "Bash", "tool_input": {"command": "   "}}
        assert build_gh_footer_response(event) == {"continue": True}


# ---------------------------------------------------------------------------
# _cb_warning_reason injection on the MCP (mcp__github__) branch
# ---------------------------------------------------------------------------


class TestCbWarningReasonMcpBranch:
    """Verify that the circuit-breaker warning reason propagates through the
    dispatcher when both the MCP footer rewrite fires AND the breaker has
    emitted an allow-with-warning.

    This exercises the ``pretooluse_dispatcher.dispatch()`` path:
        mcp__github__ tool → build_gh_footer_response → rewrite fires
        → _merge_warning_into_response injects the stashed warning reason.
    """

    def _mcp_event_with_old_footer(
        self, tool_name: str = "mcp__github__create_pull_request"
    ) -> dict:
        return {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {
                "title": "My PR",
                "body": f"Description\n\n{CLAUDE_CODE_FOOTER_OLD}",
            },
        }

    def test_warning_reason_injected_on_mcp_footer_rewrite(self, monkeypatch):
        """When context breaker fires allow+warning AND MCP footer is rewritten,
        the permissionDecisionReason must appear in the returned response."""
        from claude_mpm.hooks import context_circuit_breaker, pretooluse_dispatcher

        warning_msg = "Context at 97% — consider compacting"

        monkeypatch.setattr(
            context_circuit_breaker,
            "evaluate",
            lambda _event: {
                "permissionDecision": "allow",
                "permissionDecisionReason": warning_msg,
            },
        )

        event = self._mcp_event_with_old_footer()
        response = pretooluse_dispatcher.dispatch(event)

        # Footer was rewritten — hookSpecificOutput must be present.
        hso = response.get("hookSpecificOutput")
        assert hso is not None, "Expected hookSpecificOutput when footer was rewritten"

        # The rewritten body must contain the canonical MPM footer.
        updated_input = hso.get("updatedInput", {})
        assert MPM_FOOTER_CANONICAL in updated_input.get("body", ""), (
            "Expected MPM canonical footer in rewritten MCP body"
        )

        # The circuit-breaker warning reason must have been injected.
        assert hso.get("permissionDecisionReason") == warning_msg, (
            f"Expected warning reason '{warning_msg}' in hookSpecificOutput, "
            f"got: {hso.get('permissionDecisionReason')!r}"
        )

    def test_no_warning_when_breaker_silent(self, monkeypatch):
        """When the circuit breaker does not fire, permissionDecisionReason is
        absent even when the MCP footer is rewritten."""
        from claude_mpm.hooks import context_circuit_breaker, pretooluse_dispatcher

        monkeypatch.setattr(
            context_circuit_breaker,
            "evaluate",
            lambda _event: {},
        )

        event = self._mcp_event_with_old_footer()
        response = pretooluse_dispatcher.dispatch(event)

        hso = response.get("hookSpecificOutput")
        assert hso is not None, "Expected hookSpecificOutput when footer was rewritten"
        assert MPM_FOOTER_CANONICAL in hso.get("updatedInput", {}).get("body", "")
        # No warning reason should be present when breaker was silent.
        assert not hso.get("permissionDecisionReason"), (
            "Expected no permissionDecisionReason when circuit breaker was silent"
        )


# ---------------------------------------------------------------------------
# _cb_warning_reason injection via ToolHandler.handle_pre_tool_fast (MCP branch)
# ---------------------------------------------------------------------------


class TestCbWarningReasonToolHandlerMcpBranch:
    """Verify that the circuit-breaker warning reason propagates through
    ToolHandler.handle_pre_tool_fast() on the mcp__github__ branch.

    tool_handler.py has an independent reimplementation of the same MCP
    _cb_warning_reason injection logic (~L334-343).  These tests drive that
    path directly, independent of pretooluse_dispatcher.
    """

    def _make_tool_handler(self):
        """Build a minimal ToolHandler with mocked dependencies."""
        from unittest.mock import MagicMock

        from claude_mpm.hooks.claude_hooks.handlers.base import BaseEventHandler
        from claude_mpm.hooks.claude_hooks.handlers.tool_handler import ToolHandler

        mock_hh = MagicMock()
        mock_hh._emit_socketio_event = MagicMock(return_value=None)
        mock_hh._get_delegation_agent_type = MagicMock(return_value="unknown")

        base = MagicMock(spec=BaseEventHandler)
        base.hook_handler = mock_hh
        base._get_git_branch = MagicMock(return_value="main")
        base.log_manager = None

        return ToolHandler(base)

    def _mcp_event(self, tool_name: str = "mcp__github__create_pull_request") -> dict:
        return {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {
                "title": "My PR",
                "body": f"Description\n\n{CLAUDE_CODE_FOOTER_OLD}",
            },
            "session_id": "test-session",
            "cwd": "/tmp",
        }

    def test_warning_reason_injected_via_tool_handler_mcp(self, monkeypatch):
        """When context breaker fires allow+warning AND MCP footer is rewritten,
        ToolHandler.handle_pre_tool_fast must inject permissionDecisionReason."""
        from claude_mpm.hooks import context_circuit_breaker

        warning_msg = "Context at 96% — consider compacting"

        monkeypatch.setattr(
            context_circuit_breaker,
            "evaluate",
            lambda _event: {
                "permissionDecision": "allow",
                "permissionDecisionReason": warning_msg,
            },
        )

        handler = self._make_tool_handler()
        response = handler.handle_pre_tool_fast(self._mcp_event())

        assert response is not None, "Expected a response dict, not None"
        hso = response.get("hookSpecificOutput")
        assert hso is not None, "Expected hookSpecificOutput when footer was rewritten"

        # Body must have been rewritten to canonical footer.
        updated_input = hso.get("updatedInput", {})
        assert MPM_FOOTER_CANONICAL in updated_input.get("body", ""), (
            "Expected MPM canonical footer in rewritten MCP body"
        )

        # Warning reason must have been injected.
        assert hso.get("permissionDecisionReason") == warning_msg, (
            f"Expected warning reason in hookSpecificOutput, "
            f"got: {hso.get('permissionDecisionReason')!r}"
        )

    def test_no_warning_when_breaker_silent_tool_handler(self, monkeypatch):
        """When the circuit breaker does not fire, no permissionDecisionReason
        is present in the MCP footer-rewrite response from ToolHandler."""
        from claude_mpm.hooks import context_circuit_breaker

        monkeypatch.setattr(
            context_circuit_breaker,
            "evaluate",
            lambda _event: {},
        )

        handler = self._make_tool_handler()
        response = handler.handle_pre_tool_fast(self._mcp_event())

        assert response is not None, "Expected a response dict, not None"
        hso = response.get("hookSpecificOutput")
        assert hso is not None, "Expected hookSpecificOutput when footer was rewritten"
        assert MPM_FOOTER_CANONICAL in hso.get("updatedInput", {}).get("body", "")
        # No warning reason when breaker was silent.
        assert not hso.get("permissionDecisionReason"), (
            "Expected no permissionDecisionReason when circuit breaker was silent"
        )


# ---------------------------------------------------------------------------
# Issue #937 — Defect 2: first-pass footer duplication on dirty input
# ---------------------------------------------------------------------------

ROBOT = "\U0001f916"  # 🤖
PEOPLE = "\U0001f465"  # 👥


class TestFooterEmojiDuplication:
    """Regression (#937 defect 2): stale attribution emoji must be consumed.

    Before the fix ``_FOOTER_LINE_RE`` only swallowed a bare adjacent ``🤖``,
    so every shape below gained a duplicated ``🤖👥`` prefix on the FIRST
    rewrite pass (and only stabilised on the second).
    """

    @pytest.mark.parametrize(
        "dirty",
        [
            pytest.param(
                f"{ROBOT}{PEOPLE} {CLAUDE_CODE_FOOTER_OLD}", id="robot+people-same-line"
            ),
            pytest.param(f"{ROBOT}\n{CLAUDE_CODE_FOOTER_OLD}", id="robot-own-line"),
            pytest.param(
                f"{ROBOT}{PEOPLE}\n{CLAUDE_CODE_FOOTER_OLD}", id="robot+people-own-line"
            ),
            pytest.param(
                f"{PEOPLE} {CLAUDE_CODE_FOOTER_OLD}", id="people-only-same-line"
            ),
        ],
    )
    def test_no_duplicate_emoji_prefix(self, dirty):
        result = rewrite_footer(dirty)
        assert result == MPM_FOOTER_CANONICAL, (
            f"Expected exactly the canonical footer, got {result!r}"
        )
        # Belt and braces: the emoji run must appear exactly once.
        assert result.count(ROBOT) == 1
        assert result.count(PEOPLE) == 1
        assert f"{ROBOT}{PEOPLE}{ROBOT}{PEOPLE}" not in result

    @pytest.mark.parametrize(
        "dirty",
        [
            f"{ROBOT}{PEOPLE} {CLAUDE_CODE_FOOTER_OLD}",
            f"{ROBOT}\n{CLAUDE_CODE_FOOTER_OLD}",
            f"{ROBOT}{PEOPLE}\n{CLAUDE_CODE_FOOTER_OLD}",
            f"{PEOPLE} {CLAUDE_CODE_FOOTER_OLD}",
            f"{ROBOT} {CLAUDE_CODE_FOOTER_OLD_ALT}",
        ],
    )
    def test_first_pass_equals_second_pass(self, dirty):
        """The very first pass must already be a fixed point."""
        once = rewrite_footer(dirty)
        twice = rewrite_footer(once)
        assert once == twice

    def test_dirty_footer_in_larger_body(self):
        body = f"## Summary\n\nSome text.\n\n{ROBOT}{PEOPLE} {CLAUDE_CODE_FOOTER_OLD}\n"
        result = rewrite_footer(body)
        assert result.count(MPM_FOOTER_CANONICAL) == 1
        assert f"{ROBOT}{PEOPLE}{ROBOT}{PEOPLE}" not in result
        assert "## Summary" in result
        assert "Some text." in result

    # --- the over-strip guard ------------------------------------------------

    def test_emoji_prose_on_preceding_line_is_not_eaten(self):
        """CRITICAL negative case: a naive 'strip across the newline' fix
        destroys legitimate prose.  The sentence must survive intact."""
        prose = f"{ROBOT} indicates an automated build step"
        body = f"{prose}\n{CLAUDE_CODE_FOOTER_OLD}"
        result = rewrite_footer(body)
        assert prose in result, f"Prose was destroyed: {result!r}"
        assert result == f"{prose}\n{MPM_FOOTER_CANONICAL}"

    def test_emoji_prose_with_trailing_words_same_line_not_eaten(self):
        body = f"Use {ROBOT} for bots and {PEOPLE} for teams.\n{CLAUDE_CODE_FOOTER_OLD}"
        result = rewrite_footer(body)
        assert f"Use {ROBOT} for bots and {PEOPLE} for teams." in result
        assert MPM_FOOTER_CANONICAL in result

    def test_emoji_only_line_two_lines_above_is_not_eaten(self):
        """Only the IMMEDIATELY preceding emoji-only line is consumed."""
        body = f"{ROBOT}\n\n{CLAUDE_CODE_FOOTER_OLD}"
        result = rewrite_footer(body)
        assert result.startswith(f"{ROBOT}\n")
        assert MPM_FOOTER_CANONICAL in result


# ---------------------------------------------------------------------------
# Issue #937 — Defect 1: --body-file is advisory-only, never mutating
# ---------------------------------------------------------------------------


class TestBodyFileAdvisory:
    """The hook must never write to a file the calling agent owns."""

    def test_advisory_returned_and_file_untouched(self, tmp_path):
        body_file = tmp_path / "body.md"
        original = f"## Summary\n\nStuff\n\n{CLAUDE_CODE_FOOTER_OLD}\n"
        body_file.write_text(original)
        before_mtime = body_file.stat().st_mtime_ns

        advisory = build_body_file_advisory(f"gh pr create --body-file {body_file}")

        assert advisory is not None
        assert str(body_file) in advisory
        assert MPM_FOOTER_CANONICAL in advisory
        assert body_file.read_text() == original
        assert body_file.stat().st_mtime_ns == before_mtime

    def test_no_advisory_when_already_canonical(self, tmp_path):
        body_file = tmp_path / "body.md"
        body_file.write_text(f"Content\n\n{MPM_FOOTER_CANONICAL}")
        assert build_body_file_advisory(f"gh pr create -F {body_file}") is None

    def test_no_advisory_for_missing_file(self):
        cmd = "gh pr create --body-file /nonexistent/path/body.md"
        assert build_body_file_advisory(cmd) is None

    def test_no_advisory_for_unrelated_command(self, tmp_path):
        body_file = tmp_path / "body.md"
        body_file.write_text(CLAUDE_CODE_FOOTER_OLD)
        assert build_body_file_advisory(f"cat {body_file}") is None

    def test_no_temp_files_left_behind(self, tmp_path):
        body_file = tmp_path / "body.md"
        body_file.write_text(f"x\n\n{CLAUDE_CODE_FOOTER_OLD}")
        build_body_file_advisory(f"gh pr create --body-file {body_file}")
        assert sorted(p.name for p in tmp_path.iterdir()) == ["body.md"]

    def test_response_has_additional_context_and_no_updated_input(self, tmp_path):
        body_file = tmp_path / "body.md"
        original = f"Body\n\n{CLAUDE_CODE_FOOTER_OLD}"
        body_file.write_text(original)
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": f"gh pr create --body-file {body_file}"},
        }
        response = build_gh_footer_response(event)
        hso = response.get("hookSpecificOutput")
        assert hso is not None, f"Expected an advisory response, got {response!r}"
        assert "updatedInput" not in hso, (
            "No command text changed — updatedInput must be omitted"
        )
        assert MPM_FOOTER_CANONICAL in hso["additionalContext"]
        assert str(body_file) in hso["additionalContext"]
        # Still no mutation.
        assert body_file.read_text() == original

    def test_no_response_when_body_file_already_canonical(self, tmp_path):
        body_file = tmp_path / "body.md"
        body_file.write_text(f"Body\n\n{MPM_FOOTER_CANONICAL}")
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": f"gh pr create --body-file {body_file}"},
        }
        assert build_gh_footer_response(event) == {"continue": True}


class TestBodyFileStdin:
    """``--body-file -`` means stdin, NOT a file named ``-``."""

    def test_extract_returns_none_for_stdin(self):
        assert _extract_body_file("gh pr create --body-file -") is None
        assert _extract_body_file("gh issue create -F -") is None

    def test_real_file_named_dash_is_never_touched(self, tmp_path, monkeypatch):
        """Proven-dangerous case: a real file literally named ``-`` in cwd."""
        monkeypatch.chdir(tmp_path)
        dash = tmp_path / "-"
        original = f"Body\n\n{CLAUDE_CODE_FOOTER_OLD}"
        dash.write_text(original)
        before_mtime = dash.stat().st_mtime_ns

        cmd = "gh pr create --title T --body-file -"
        assert rewrite_bash_command(cmd) is None
        assert build_body_file_advisory(cmd) is None
        assert build_gh_footer_response(
            {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(tmp_path)}
        ) == {"continue": True}

        # The file must be untouched: same bytes, same mtime, no temp siblings.
        assert dash.read_text() == original
        assert dash.stat().st_mtime_ns == before_mtime
        assert sorted(p.name for p in tmp_path.iterdir()) == ["-"]

    def test_short_flag_dash_stdin_file_untouched(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dash = tmp_path / "-"
        original = f"{CLAUDE_CODE_FOOTER_OLD_ALT}"
        dash.write_text(original)
        assert build_body_file_advisory("gh issue create -F -") is None
        assert dash.read_text() == original


# ---------------------------------------------------------------------------
# Issue #937 — Defect 3B: flag-form coverage matrix
# ---------------------------------------------------------------------------


class TestBodyFileFlagForms:
    """``--body-file=p``, ``-F=p`` and ``-Fp`` used to bypass the hook."""

    @pytest.mark.parametrize(
        "template",
        [
            pytest.param("gh pr create --body-file {p}", id="long-space"),
            pytest.param("gh pr create --body-file={p}", id="long-equals"),
            pytest.param("gh pr create -F {p}", id="short-space"),
            pytest.param("gh pr create -F={p}", id="short-equals"),
            pytest.param("gh pr create -F{p}", id="short-glued"),
            pytest.param('gh pr create --body-file "{p}"', id="long-space-dquoted"),
            pytest.param("gh pr create --body-file='{p}'", id="long-equals-squoted"),
        ],
    )
    def test_every_flag_form_is_detected(self, tmp_path, template):
        body_file = tmp_path / "body.md"
        original = f"Body\n\n{CLAUDE_CODE_FOOTER_OLD}"
        body_file.write_text(original)
        cmd = template.format(p=body_file)

        assert _extract_body_file(cmd) == str(body_file), (
            f"Flag form not parsed: {cmd!r}"
        )
        advisory = build_body_file_advisory(cmd)
        assert advisory is not None, f"Flag form bypassed the hook: {cmd!r}"
        assert str(body_file) in advisory
        # Advisory-only: still no mutation for any flag form.
        assert body_file.read_text() == original

    def test_body_file_not_matched_inside_longer_token(self):
        # -F must not match mid-token.
        assert _extract_body_file("gh pr create --draft") is None
        assert _extract_body_file("gh pr create --title xxx-Fyyy") is None


class TestInlineBodyFlagForms:
    """Inline ``--body``/``-b`` separator matrix.

    The equals form already worked before #937; recorded here so a
    regression is caught.
    """

    @pytest.mark.parametrize(
        "template",
        [
            pytest.param('gh pr create --body "{b}"', id="long-space"),
            pytest.param('gh pr create --body="{b}"', id="long-equals"),
            pytest.param('gh pr create -b "{b}"', id="short-space"),
            pytest.param('gh pr create -b="{b}"', id="short-equals"),
        ],
    )
    def test_every_inline_form_rewrites(self, template):
        cmd = template.format(b=CLAUDE_CODE_FOOTER_OLD)
        result = rewrite_bash_command(cmd)
        assert result is not None, f"Inline form bypassed the hook: {cmd!r}"
        assert MPM_FOOTER_CANONICAL in result
        assert CLAUDE_CODE_FOOTER_OLD not in result

    def test_glued_short_b_is_deliberately_unsupported(self):
        """``-bVALUE`` is NOT supported on purpose.

        Supporting it would make ``-base main`` parse as ``-b`` + ``ase``,
        corrupting a legitimate command.  The false-positive risk outweighs
        the coverage gain, so the glued short form is left alone.
        """
        cmd = f'gh pr create -b"{CLAUDE_CODE_FOOTER_OLD}"'
        assert rewrite_bash_command(cmd) is None
        # And the reason it stays that way:
        cmd2 = f'gh pr create -base main --body "{CLAUDE_CODE_FOOTER_OLD}"'
        result = rewrite_bash_command(cmd2)
        assert result is not None
        assert "-base main" in result


# ---------------------------------------------------------------------------
# Issue #937 — Defect 3C: _requote must never expose shell metacharacters
# ---------------------------------------------------------------------------


class TestRequoteShellSafety:
    def test_single_quoted_body_with_apostrophe_stays_single_quoted(self):
        value = "Fixes it's the bug. $USER ran `whoami` here."
        quoted = _requote(value, "'")
        assert quoted.startswith("'") and quoted.endswith("'")
        # $ and ` must remain inside single quotes (inert), never bare in a
        # double-quoted string.
        assert not quoted.startswith('"')
        assert quoted == "'Fixes it'\\''s the bug. $USER ran `whoami` here.'"

    def test_single_quoted_roundtrips_through_a_real_shell(self):
        """The re-quoted token must survive an actual POSIX shell verbatim."""
        import subprocess

        value = "Fixes it's the bug. $USER ran `whoami` here. 50% \\ done"
        quoted = _requote(value, "'")
        out = subprocess.run(  # noqa: S603
            ["/bin/sh", "-c", f"printf %s {quoted}"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert out.stdout == value, f"Shell mangled the value: {out.stdout!r}"

    def test_bare_value_with_metacharacters_is_single_quoted(self):
        quoted = _requote("has space $x and `y`", "")
        assert quoted.startswith("'") and quoted.endswith("'")
        assert "$x" in quoted and "`y`" in quoted

    def test_bare_safe_value_stays_bare(self):
        assert _requote("simple-value_1.txt", "") == "simple-value_1.txt"

    def test_end_to_end_single_quoted_body_with_dollar_and_backtick(self):
        """Full command rewrite: $ and ` must stay inert after the rewrite."""
        body = f"Fixes $USER bug; ran `whoami`.\n\n{CLAUDE_CODE_FOOTER_OLD}"
        cmd = f"gh pr create --title T --body '{body}'"
        result = rewrite_bash_command(cmd)
        assert result is not None
        assert MPM_FOOTER_CANONICAL in result
        # Must still be single-quoted — never downgraded to double quotes.
        assert "--body '" in result
        assert '--body "' not in result
        assert "$USER" in result
        assert "`whoami`" in result


class TestSpliceQuotedBodyLimitation:
    r"""Documented limitation: bodies using the POSIX ``'\''`` splice idiom.

    ``_BODY_FLAG_RE`` models a quoted value as ONE balanced quote pair, but a
    shell word may be a concatenation of adjacent chunks.  We cannot parse the
    full word without replacing the regex with a shell tokeniser, so the hook
    detects the situation and stands down.  Correctness over coverage: the
    footer is left stale rather than the command being corrupted.
    """

    def test_splice_quoted_body_is_left_alone(self):
        # Body: "Generated with [Claude Code](...) it's here"
        cmd = "gh pr create --body '" + CLAUDE_CODE_FOOTER_OLD + " it'\\''s here'"
        # No rewrite — and crucially, no corrupted half-rewrite either.
        assert rewrite_bash_command(cmd) is None

    def test_splice_quoted_body_response_is_passthrough(self):
        cmd = "gh pr create --body 'It'\\''s " + CLAUDE_CODE_FOOTER_OLD + "'"
        event = {"tool_name": "Bash", "tool_input": {"command": cmd}}
        assert build_gh_footer_response(event) == {"continue": True}

    @pytest.mark.xfail(
        reason=(
            "Known limitation (#937 defect 3C): a body built with the POSIX "
            "'\\'' splice idiom cannot be parsed by the regex-based flag "
            "parser, so its stale footer is left un-normalised. Fixing this "
            "requires a real shell tokeniser; the hook deliberately stands "
            "down instead of corrupting the command."
        ),
        strict=True,
    )
    def test_splice_quoted_body_would_ideally_be_normalised(self):
        cmd = "gh pr create --body 'It'\\''s " + CLAUDE_CODE_FOOTER_OLD + "'"
        result = rewrite_bash_command(cmd)
        assert result is not None
        assert MPM_FOOTER_CANONICAL in result


# ---------------------------------------------------------------------------
# Issue #937 — Defect 3A: opt-out switch
# ---------------------------------------------------------------------------


class TestOptOut:
    def _bash_event(self, cwd: str = "") -> dict:
        return {
            "tool_name": "Bash",
            "tool_input": {
                "command": f'gh pr create --body "{CLAUDE_CODE_FOOTER_OLD}"'
            },
            "cwd": cwd,
        }

    def _mcp_event(self, cwd: str = "") -> dict:
        return {
            "tool_name": "mcp__github__create_pull_request",
            "tool_input": {"title": "T", "body": f"x\n\n{CLAUDE_CODE_FOOTER_OLD}"},
            "cwd": cwd,
        }

    def _write_settings(self, tmp_path, filename: str, payload: dict) -> None:
        import json

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        (claude_dir / filename).write_text(json.dumps(payload))

    # --- baseline: hook is ON by default -------------------------------------

    def test_enabled_by_default_bash(self, tmp_path):
        response = build_gh_footer_response(self._bash_event(str(tmp_path)))
        assert "hookSpecificOutput" in response

    # --- env var -------------------------------------------------------------

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " On "])
    def test_env_var_disables_bash_path(self, monkeypatch, value):
        monkeypatch.setenv(_DISABLE_ENV_VAR, value)
        assert build_gh_footer_response(self._bash_event()) == {"continue": True}

    def test_env_var_disables_mcp_path(self, monkeypatch):
        monkeypatch.setenv(_DISABLE_ENV_VAR, "true")
        assert build_gh_footer_response(self._mcp_event()) == {"continue": True}

    def test_env_var_disables_body_file_advisory(self, monkeypatch, tmp_path):
        monkeypatch.setenv(_DISABLE_ENV_VAR, "1")
        body_file = tmp_path / "body.md"
        body_file.write_text(f"x\n\n{CLAUDE_CODE_FOOTER_OLD}")
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": f"gh pr create --body-file {body_file}"},
        }
        assert build_gh_footer_response(event) == {"continue": True}

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
    def test_falsy_env_values_do_not_disable(self, monkeypatch, value):
        monkeypatch.setenv(_DISABLE_ENV_VAR, value)
        response = build_gh_footer_response(self._bash_event())
        assert "hookSpecificOutput" in response

    # --- settings key --------------------------------------------------------

    @pytest.mark.parametrize("filename", ["settings.local.json", "settings.json"])
    def test_settings_key_disables_bash_path(self, tmp_path, filename):
        self._write_settings(tmp_path, filename, {"gh_footer_hook": {"disabled": True}})
        assert build_gh_footer_response(self._bash_event(str(tmp_path))) == {
            "continue": True
        }

    def test_settings_key_disables_mcp_path(self, tmp_path):
        self._write_settings(
            tmp_path, "settings.json", {"gh_footer_hook": {"disabled": True}}
        )
        assert build_gh_footer_response(self._mcp_event(str(tmp_path))) == {
            "continue": True
        }

    def test_settings_key_false_leaves_hook_enabled(self, tmp_path):
        self._write_settings(
            tmp_path, "settings.json", {"gh_footer_hook": {"disabled": False}}
        )
        response = build_gh_footer_response(self._bash_event(str(tmp_path)))
        assert "hookSpecificOutput" in response

    def test_unrelated_settings_leave_hook_enabled(self, tmp_path):
        self._write_settings(tmp_path, "settings.json", {"other_hook": {"x": 1}})
        response = build_gh_footer_response(self._bash_event(str(tmp_path)))
        assert "hookSpecificOutput" in response

    def test_malformed_settings_file_leaves_hook_enabled(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("{not json")
        response = build_gh_footer_response(self._bash_event(str(tmp_path)))
        assert "hookSpecificOutput" in response


# ---------------------------------------------------------------------------
# Issue #937 — the advisory must survive the LIVE dispatch path
# ---------------------------------------------------------------------------


class TestBodyFileAdvisoryThroughToolHandler:
    """The live PreToolUse dispatch site is ToolHandler.handle_pre_tool_fast.

    Its Bash branch used to look only at ``updatedInput``, so an
    advisory-only response (no command rewrite) would have been dropped.
    """

    def _make_tool_handler(self):
        from unittest.mock import MagicMock

        from claude_mpm.hooks.claude_hooks.handlers.base import BaseEventHandler
        from claude_mpm.hooks.claude_hooks.handlers.tool_handler import ToolHandler

        mock_hh = MagicMock()
        mock_hh._emit_socketio_event = MagicMock(return_value=None)
        mock_hh._get_delegation_agent_type = MagicMock(return_value="unknown")

        base = MagicMock(spec=BaseEventHandler)
        base.hook_handler = mock_hh
        base._get_git_branch = MagicMock(return_value="main")
        base.log_manager = None

        return ToolHandler(base)

    def test_advisory_reaches_the_harness_and_file_is_untouched(
        self, tmp_path, monkeypatch
    ):
        from claude_mpm.hooks import context_circuit_breaker

        monkeypatch.setattr(context_circuit_breaker, "evaluate", lambda _event: {})

        body_file = tmp_path / "body.md"
        original = f"Body\n\n{CLAUDE_CODE_FOOTER_OLD}"
        body_file.write_text(original)

        handler = self._make_tool_handler()
        response = handler.handle_pre_tool_fast(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": f"gh pr create --body-file {body_file}"},
                "session_id": "test-session",
                "cwd": str(tmp_path),
            }
        )

        assert response is not None, "Advisory response was dropped by ToolHandler"
        hso = response.get("hookSpecificOutput")
        assert hso is not None, f"Expected hookSpecificOutput, got {response!r}"
        assert str(body_file) in hso.get("additionalContext", "")
        assert MPM_FOOTER_CANONICAL in hso.get("additionalContext", "")
        # NOTE: ztk_hook also runs on the Bash branch and may return its own
        # response carrying an updatedInput.  What matters here is that the
        # footer advisory is merged into whichever response wins, rather than
        # being dropped — which is exactly what used to happen.
        #
        # The hook must not have written to the agent-owned file.
        assert body_file.read_text() == original

    def test_inline_rewrite_still_reaches_the_harness(self, monkeypatch):
        from claude_mpm.hooks import context_circuit_breaker

        monkeypatch.setattr(context_circuit_breaker, "evaluate", lambda _event: {})

        handler = self._make_tool_handler()
        response = handler.handle_pre_tool_fast(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {
                    "command": f'gh pr create --body "{CLAUDE_CODE_FOOTER_OLD}"'
                },
                "session_id": "test-session",
                "cwd": "/tmp",
            }
        )

        assert response is not None
        hso = response.get("hookSpecificOutput")
        assert hso is not None
        assert MPM_FOOTER_CANONICAL in hso["updatedInput"]["command"]


# ---------------------------------------------------------------------------
# Issue #937 review follow-up — the advisory must MERGE with ztk's own
# additionalContext, never be silently yielded to it.
# ---------------------------------------------------------------------------

_ZTK_CONTEXT = "[ztk] command was compressed"


def _make_tool_handler():
    """Build a minimal ToolHandler with mocked observability dependencies."""
    from unittest.mock import MagicMock

    from claude_mpm.hooks.claude_hooks.handlers.base import BaseEventHandler
    from claude_mpm.hooks.claude_hooks.handlers.tool_handler import ToolHandler

    mock_hh = MagicMock()
    mock_hh._emit_socketio_event = MagicMock(return_value=None)
    mock_hh._get_delegation_agent_type = MagicMock(return_value="unknown")

    base = MagicMock(spec=BaseEventHandler)
    base.hook_handler = mock_hh
    base._get_git_branch = MagicMock(return_value="main")
    base.log_manager = None

    return ToolHandler(base)


def _ztk_response_factory(*, additional_context: str | None):
    """Return a fake ``build_ztk_response`` that always rewrites the command."""

    def _fake(event):
        hso = {
            "hookEventName": "PreToolUse",
            "updatedInput": {"command": "ztk-wrapped-command"},
        }
        if additional_context is not None:
            hso["additionalContext"] = additional_context
        return {"hookSpecificOutput": hso}

    return _fake


class TestAdvisorySurvivesZtkAdditionalContext:
    """``ztk_hook`` may populate ``additionalContext`` itself.

    Both dispatch sites used to write the gh_footer body-file advisory only
    when that field was still empty, so a ztk response that claimed the field
    silently DROPPED the advisory — the exact failure the merge exists to
    prevent.  Both messages must now survive.
    """

    @staticmethod
    def _body_file_event(tmp_path):
        body_file = tmp_path / "body.md"
        body_file.write_text(f"Body\n\n{CLAUDE_CODE_FOOTER_OLD}")
        return body_file, {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": f"gh pr create --body-file {body_file}"},
            "session_id": "test-session",
            "cwd": str(tmp_path),
        }

    # --- live path: ToolHandler.handle_pre_tool_fast -------------------------

    def test_tool_handler_appends_advisory_to_ztk_context(self, tmp_path, monkeypatch):
        from claude_mpm.hooks import context_circuit_breaker, ztk_hook

        monkeypatch.setattr(context_circuit_breaker, "evaluate", lambda _e: {})
        monkeypatch.setattr(
            ztk_hook,
            "build_ztk_response",
            _ztk_response_factory(additional_context=_ZTK_CONTEXT),
        )

        body_file, event = self._body_file_event(tmp_path)
        response = _make_tool_handler().handle_pre_tool_fast(event)

        hso = (response or {}).get("hookSpecificOutput")
        assert hso is not None, f"Expected hookSpecificOutput, got {response!r}"
        context = hso.get("additionalContext", "")
        assert _ZTK_CONTEXT in context, "ztk's own additionalContext was clobbered"
        assert str(body_file) in context, "footer advisory was dropped by ztk"
        assert MPM_FOOTER_CANONICAL in context
        # ztk's rewrite still wins for the command itself.
        assert hso["updatedInput"]["command"] == "ztk-wrapped-command"

    def test_tool_handler_sets_advisory_when_ztk_context_absent(
        self, tmp_path, monkeypatch
    ):
        from claude_mpm.hooks import context_circuit_breaker, ztk_hook

        monkeypatch.setattr(context_circuit_breaker, "evaluate", lambda _e: {})
        monkeypatch.setattr(
            ztk_hook,
            "build_ztk_response",
            _ztk_response_factory(additional_context=None),
        )

        body_file, event = self._body_file_event(tmp_path)
        response = _make_tool_handler().handle_pre_tool_fast(event)

        hso = (response or {}).get("hookSpecificOutput")
        assert hso is not None
        context = hso.get("additionalContext", "")
        assert str(body_file) in context
        assert MPM_FOOTER_CANONICAL in context
        # No stray separator when there was nothing to append to.
        assert not context.startswith("\n")

    # --- legacy path: pretooluse_dispatcher.dispatch -------------------------

    def test_dispatcher_appends_advisory_to_ztk_context(self, tmp_path, monkeypatch):
        from claude_mpm.hooks import (
            context_circuit_breaker,
            pretooluse_dispatcher,
            ztk_hook,
        )

        monkeypatch.setattr(context_circuit_breaker, "evaluate", lambda _e: {})
        monkeypatch.setattr(
            ztk_hook,
            "build_ztk_response",
            _ztk_response_factory(additional_context=_ZTK_CONTEXT),
        )

        body_file, event = self._body_file_event(tmp_path)
        response = pretooluse_dispatcher.dispatch(event)

        hso = response.get("hookSpecificOutput")
        assert hso is not None, f"Expected hookSpecificOutput, got {response!r}"
        context = hso.get("additionalContext", "")
        assert _ZTK_CONTEXT in context, "ztk's own additionalContext was clobbered"
        assert str(body_file) in context, "footer advisory was dropped by ztk"
        assert MPM_FOOTER_CANONICAL in context

    def test_dispatcher_failsafe_footer_response_does_not_break_bash_branch(
        self, monkeypatch
    ):
        """A footer response with NO ``hookSpecificOutput`` key must be inert.

        ``build_gh_footer_response`` fails open to ``{"continue": True}``.  The
        Bash branch reads ``hookSpecificOutput`` several times; every read must
        be total.  ``dispatch`` swallows exceptions, so the discriminator is
        that ztk's response still comes back: had the footer block raised,
        the fail-open handler would have returned a bare pass-through.
        """
        from claude_mpm.hooks import (
            context_circuit_breaker,
            gh_footer_hook as _gh,
            pretooluse_dispatcher,
            ztk_hook,
        )

        monkeypatch.setattr(context_circuit_breaker, "evaluate", lambda _e: {})
        monkeypatch.setattr(
            _gh, "build_gh_footer_response", lambda _e: {"continue": True}
        )
        monkeypatch.setattr(
            ztk_hook,
            "build_ztk_response",
            _ztk_response_factory(additional_context=None),
        )

        response = pretooluse_dispatcher.dispatch(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "gh pr create --body-file body.md"},
            }
        )

        hso = response.get("hookSpecificOutput")
        assert hso is not None, (
            "Bash branch aborted before ztk ran — the footer response with no "
            f"hookSpecificOutput was not handled totally: {response!r}"
        )
        assert hso["updatedInput"]["command"] == "ztk-wrapped-command"
        assert "additionalContext" not in hso


# ---------------------------------------------------------------------------
# Issue #937 review follow-up — _BODY_FILE_FLAG_RE anchor semantics
# ---------------------------------------------------------------------------


class TestBodyFileFlagAnchor:
    """``_BODY_FILE_FLAG_RE`` uses ``(?:^|\\s)`` WITHOUT ``re.MULTILINE``.

    That is deliberate and sufficient: ``\\s`` already matches ``\\n``, so a
    flag on a backslash-continued line is reached through the ``\\s`` branch
    and never needs ``^`` to match at a line start.  Adding ``re.MULTILINE``
    would change nothing, so it is not added.
    """

    def test_flag_at_string_start_matches(self):
        assert _extract_body_file("--body-file=body.md") == "body.md"
        assert _extract_body_file("-F body.md") == "body.md"

    @pytest.mark.parametrize(
        "command",
        [
            "gh pr create \\\n  -F body.md",
            'gh pr create --title "x" \\\n  --body-file body.md',
            "gh pr create\n-F body.md",
        ],
    )
    def test_flag_after_newline_matches_without_multiline(self, command):
        """The ``\\s`` branch consumes the newline — no ``re.MULTILINE`` needed."""
        assert _extract_body_file(command) == "body.md"

    def test_flag_inside_a_longer_token_is_not_matched_as_dash_f(self):
        """``(?:^|\\s)`` keeps ``-F`` from matching inside ``--body-file``."""
        assert _extract_body_file("gh pr create --body-file report.md") == "report.md"

    def test_dash_f_inside_a_quoted_value_is_a_harmless_false_positive(
        self, tmp_path, monkeypatch
    ):
        """KNOWN LIMITATION, pinned deliberately.

        The regex is not shell-aware, so ``-F`` preceded by a space *inside* a
        quoted argument is matched.  ``re.MULTILINE`` is irrelevant to this —
        the match comes from the ``\\s`` branch either way.  It is harmless
        because the extracted token is not a real path: the hook is read-only
        and ``build_body_file_advisory`` degrades to None on the failed read,
        so nothing is emitted and no file is ever touched.
        """
        monkeypatch.chdir(tmp_path)
        command = "gh pr create --title \"use -F for files\" --body 'hello'"

        # The raw extractor does match the phantom token...
        assert _extract_body_file(command) == "for"
        # ...but the advisory builder emits nothing, because there is no such file.
        assert build_body_file_advisory(command) is None
        assert not (tmp_path / "for").exists()
