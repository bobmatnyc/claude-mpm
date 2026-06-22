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
    _is_gh_body_command,
    build_gh_footer_response,
    rewrite_bash_command,
    rewrite_footer,
    rewrite_mcp_body,
)

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

    def test_body_file_flag(self, tmp_path):
        body_file = tmp_path / "body.md"
        body_file.write_text(f"Content\n\n{CLAUDE_CODE_FOOTER_OLD}")
        cmd = f"gh pr create --body-file {body_file}"
        result = rewrite_bash_command(cmd)
        # Command string is unchanged (same file path)
        assert result == cmd
        # But file content was rewritten
        new_content = body_file.read_text()
        assert MPM_FOOTER_CANONICAL in new_content
        assert CLAUDE_CODE_FOOTER_OLD not in new_content

    def test_body_file_short_flag(self, tmp_path):
        body_file = tmp_path / "body.md"
        body_file.write_text(f"{CLAUDE_CODE_FOOTER_OLD_ALT}")
        cmd = f"gh issue create -F {body_file}"
        result = rewrite_bash_command(cmd)
        assert result == cmd
        assert MPM_FOOTER_CANONICAL in body_file.read_text()

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
